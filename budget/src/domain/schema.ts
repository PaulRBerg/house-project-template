import { z } from "zod";

import { BUDGET_AREA_IDS } from "./areas.js";

export const DEFAULT_ANNUAL_GROWTH_BPS = 500 as const;
export const DEFAULT_CONTINGENCY_BPS = 1_000 as const;
export const MAX_ANNUAL_GROWTH_BPS = 2_500 as const;
export const MAX_CONTINGENCY_BPS = 5_000 as const;
export const MAX_MONEY_CENTS = 100_000_000_000 as const;
export const MAX_GROWTH_DAYS = 36_525 as const;

export const MILESTONE_IDS = ["la-rosu", "la-gri", "la-cheie", "la-mutat"] as const;

const idSchema = z
  .string()
  .min(1)
  .max(100)
  .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Folosește un ID stabil în kebab-case.");

const labelSchema = z.string().trim().min(1).max(240);
const euroCentsSchema = z.number().int().nonnegative().max(MAX_MONEY_CENTS);

function isHttpUrl(value: string): boolean {
  try {
    const protocol = new URL(value).protocol;
    return protocol === "http:" || protocol === "https:";
  } catch {
    return false;
  }
}

function isCalendarDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
  );
}

export const isoDateSchema = z
  .string()
  .refine(isCalendarDate, "Data trebuie să fie o zi calendaristică ISO YYYY-MM-DD.");

function isCalendarMonth(value: string): boolean {
  const match = /^(\d{4})-(\d{2})$/.exec(value);
  if (!match) return false;
  const month = Number(match[2]);
  return month >= 1 && month <= 12;
}

/** Month-level planning value; valid legacy day values are reduced to their month when parsed. */
export const isoMonthSchema = z.preprocess(
  (value) => (typeof value === "string" && isCalendarDate(value) ? value.slice(0, 7) : value),
  z.string().refine(isCalendarMonth, "Luna trebuie să fie o valoare calendaristică ISO YYYY-MM."),
);

export const scenarioSchema = z.enum(["base", "high"]);
export type Scenario = z.infer<typeof scenarioSchema>;

export const paymentModeSchema = z.enum(["one-off", "partial-progress"]);

export const budgetAreaIdSchema = z.enum(BUDGET_AREA_IDS);

const currentScenarioAmountsSchema = z
  .object({
    baseCents: euroCentsSchema,
    highCents: euroCentsSchema,
  })
  .strict()
  .superRefine((amounts, context) => {
    if (amounts.baseCents > amounts.highCents) {
      context.addIssue({
        code: "custom",
        message: "Scenariile trebuie ordonate Optimist ≤ Prudent.",
      });
    }
  });

// Older v1 backups retain a retired low tier; base is now Optimist and high remains Prudent.
export const scenarioAmountsSchema = z.preprocess((value) => {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return value;
  const amounts = { ...value } as Record<string, unknown>;
  delete amounts.lowCents;
  return amounts;
}, currentScenarioAmountsSchema);

const totalEstimateSchema = z
  .object({
    kind: z.literal("total"),
    amounts: scenarioAmountsSchema,
    fixed: z.boolean(),
    pricedOn: isoDateSchema,
  })
  .strict();

const quantityRateEstimateSchema = z
  .object({
    kind: z.literal("quantity-rate"),
    quantity: z.number().positive().finite().max(1_000_000_000),
    quantityBasis: z.literal("built-area").optional(),
    unit: z.string().trim().min(1).max(40),
    rates: scenarioAmountsSchema,
    fixed: z.boolean(),
    pricedOn: isoDateSchema,
  })
  .strict()
  .superRefine((estimate, context) => {
    for (const [scenario, rateCents] of Object.entries(estimate.rates)) {
      const amountCents = Math.round(estimate.quantity * rateCents);
      if (!Number.isSafeInteger(amountCents) || amountCents > MAX_MONEY_CENTS) {
        context.addIssue({
          code: "custom",
          path: ["rates", scenario],
          message: `Cantitatea înmulțită cu tariful trebuie să producă maximum ${MAX_MONEY_CENTS} cenți întregi siguri.`,
        });
      }
    }
  });

export const estimateSchema = z.discriminatedUnion("kind", [
  totalEstimateSchema,
  quantityRateEstimateSchema,
]);

export const milestoneSchema = z
  .object({
    id: z.enum(MILESTONE_IDS),
    label: labelSchema,
    date: isoMonthSchema,
  })
  .strict();

export const groupSchema = z
  .object({
    id: idSchema,
    label: labelSchema,
    parentId: idSchema.nullable(),
    milestoneId: milestoneSchema.shape.id,
    sortOrder: z.number().int().nonnegative(),
    archived: z.boolean(),
  })
  .strict();

export const briefReferenceSchema = z
  .object({
    recordId: z.string().trim().min(1).max(160),
    status: z.enum(["required", "preferred", "phased", "deferred"]),
  })
  .strict();

export const completionSchema = z
  .object({
    complete: z.boolean(),
    completedOn: isoDateSchema.optional(),
  })
  .strict()
  .superRefine((completion, context) => {
    if (!completion.complete && completion.completedOn !== undefined) {
      context.addIssue({
        code: "custom",
        path: ["completedOn"],
        message: "Un element incomplet nu poate avea dată de finalizare.",
      });
    }
  });

export const itemSchema = z
  .object({
    id: idSchema,
    label: labelSchema,
    groupId: idSchema,
    areaId: budgetAreaIdSchema.optional(),
    milestoneId: milestoneSchema.shape.id,
    sortOrder: z.number().int().nonnegative(),
    costScope: z.enum(["core", "movable"]),
    costType: z.enum(["land", "work", "professional-fee", "system", "movable-good", "other"]),
    paymentMode: paymentModeSchema.default("partial-progress"),
    contingencyEligible: z.boolean(),
    included: z.boolean(),
    archived: z.boolean(),
    ownership: z.enum(["planned", "owned"]),
    completion: completionSchema,
    estimate: estimateSchema,
    supplier: z.string().trim().min(1).max(240).optional(),
    briefReferences: z.array(briefReferenceSchema).max(40),
    sourceIds: z.array(idSchema).max(40),
    notes: z.string().trim().max(2_000).optional(),
  })
  .strict()
  .superRefine((item, context) => {
    if (item.ownership === "owned" && !item.completion.complete) {
      context.addIssue({
        code: "custom",
        path: ["completion", "complete"],
        message: "O achiziție deja deținută trebuie marcată completă.",
      });
    }
    if (item.costType === "land" && item.costScope !== "core") {
      context.addIssue({
        code: "custom",
        path: ["costScope"],
        message: "Terenul face parte din bugetul de bază.",
      });
    }
    const shouldHaveContingency = item.costScope === "core" && item.costType !== "land";
    if (item.contingencyEligible !== shouldHaveContingency) {
      context.addIssue({
        code: "custom",
        path: ["contingencyEligible"],
        message:
          item.costScope === "movable" || item.costType === "land"
            ? "Terenul și bunurile mobile nu primesc contingență."
            : "Costurile de bază, cu excepția terenului, primesc contingență.",
      });
    }
    if (item.costType === "movable-good" && item.costScope !== "movable") {
      context.addIssue({
        code: "custom",
        path: ["costScope"],
        message: "Un bun mobil trebuie să aibă costScope «movable».",
      });
    }
  });

export const sourceSchema = z
  .object({
    id: idSchema,
    title: labelSchema,
    url: z.url().refine(isHttpUrl, "Sursa trebuie să folosească un URL http sau https."),
    accessedOn: isoDateSchema,
    scope: z.string().trim().min(1).max(500),
    tax: z
      .object({
        status: z.enum(["included", "excluded", "not-applicable", "unknown"]),
        rateBps: z.number().int().min(0).max(10_000).optional(),
      })
      .strict(),
    confidence: z.enum(["low", "medium", "high"]),
    provenance: z
      .object({
        currency: z.string().trim().length(3).toUpperCase(),
        quotedAmountMinor: z.number().int().nonnegative().optional(),
        note: z.string().trim().max(500).optional(),
      })
      .strict()
      .optional(),
  })
  .strict();

export const instalmentSchema = z
  .object({
    id: idSchema,
    itemId: idSchema,
    label: labelSchema,
    dueOn: isoMonthSchema.optional(),
    projectedCents: euroCentsSchema,
  })
  .strict();

export const paymentSchema = z
  .object({
    id: idSchema,
    itemId: idSchema,
    instalmentId: idSchema,
    paidOn: isoDateSchema,
    amountCents: euroCentsSchema.positive(),
    note: z.string().trim().max(500).optional(),
  })
  .strict();

const currentProjectSchema = z
  .object({
    id: idSchema,
    name: labelSchema,
    location: z.string().trim().min(1).max(240),
    currency: z.literal("EUR"),
    builtAreaSqm: z.number().positive().finite().max(1_000_000),
    annualGrowthBps: z.number().int().min(0).max(MAX_ANNUAL_GROWTH_BPS),
    contingencyBps: z.number().int().min(0).max(MAX_CONTINGENCY_BPS),
  })
  .strict();

// Older v1 backups may still contain retired targets; discard them when opening.
export const projectSchema = z.preprocess((value) => {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return value;
  const project = { ...value } as Record<string, unknown>;
  delete project.coreBudgetTargetCents;
  delete project.coreBudgetCapCents;
  return project;
}, currentProjectSchema);

export const budgetDocumentSchema = z
  .object({
    schemaVersion: z.literal(1),
    project: projectSchema,
    milestones: z.array(milestoneSchema).length(4),
    groups: z.array(groupSchema),
    items: z.array(itemSchema),
    sources: z.array(sourceSchema),
    instalments: z.array(instalmentSchema),
    payments: z.array(paymentSchema),
  })
  .strict()
  .superRefine(validateDocumentReferences);

export type ScenarioAmounts = z.infer<typeof scenarioAmountsSchema>;
export type Estimate = z.infer<typeof estimateSchema>;
export type Milestone = z.infer<typeof milestoneSchema>;
export type BudgetGroup = z.infer<typeof groupSchema>;
export type BriefReference = z.infer<typeof briefReferenceSchema>;
export type BudgetItem = z.infer<typeof itemSchema>;
export type BudgetSource = z.infer<typeof sourceSchema>;
export type Instalment = z.infer<typeof instalmentSchema>;
export type Payment = z.infer<typeof paymentSchema>;
export type BudgetProject = z.infer<typeof projectSchema>;
export type BudgetDocument = z.infer<typeof budgetDocumentSchema>;

function validateDocumentReferences(
  document: z.infer<typeof budgetDocumentSchema>,
  context: z.RefinementCtx,
): void {
  document.items.forEach((item, index) => {
    const estimate = item.estimate;
    if (
      estimate.kind === "quantity-rate" &&
      estimate.quantityBasis === "built-area" &&
      estimate.quantity !== document.project.builtAreaSqm
    ) {
      context.addIssue({
        code: "custom",
        path: ["items", index, "estimate", "quantity"],
        message: `Cantitatea bazată pe aria construită trebuie să coincidă cu suprafața proiectului: ${document.project.builtAreaSqm} m².`,
      });
    }
  });

  const milestoneIds = document.milestones.map((milestone) => milestone.id);
  for (const id of MILESTONE_IDS) {
    if (milestoneIds.filter((milestoneId) => milestoneId === id).length !== 1) {
      context.addIssue({
        code: "custom",
        path: ["milestones"],
        message: `Jalonul ${id} trebuie să apară exact o dată.`,
      });
    }
  }

  const allIds = new Map<string, string>();
  const collections: ReadonlyArray<readonly [string, ReadonlyArray<{ id: string }>]> = [
    ["milestones", document.milestones],
    ["groups", document.groups],
    ["items", document.items],
    ["sources", document.sources],
    ["instalments", document.instalments],
    ["payments", document.payments],
  ];
  for (const [collectionName, records] of collections) {
    records.forEach((record, index) => {
      const previousCollection = allIds.get(record.id);
      if (previousCollection) {
        context.addIssue({
          code: "custom",
          path: [collectionName, index, "id"],
          message: `ID-ul ${record.id} este deja folosit în ${previousCollection}.`,
        });
      } else {
        allIds.set(record.id, collectionName);
      }
    });
  }

  const groups = new Map(document.groups.map((group) => [group.id, group]));
  document.groups.forEach((group, index) => {
    if (group.parentId === null) return;
    const parent = groups.get(group.parentId);
    if (!parent) {
      context.addIssue({
        code: "custom",
        path: ["groups", index, "parentId"],
        message: `Grupul părinte ${group.parentId} nu există.`,
      });
    } else if (parent.milestoneId !== group.milestoneId) {
      context.addIssue({
        code: "custom",
        path: ["groups", index, "milestoneId"],
        message: "Un subgrup trebuie să aparțină aceluiași jalon ca părintele său.",
      });
    }
  });

  const visited = new Set<string>();
  const active = new Set<string>();
  const visit = (groupId: string): void => {
    if (active.has(groupId)) {
      const index = document.groups.findIndex((group) => group.id === groupId);
      context.addIssue({
        code: "custom",
        path: ["groups", index, "parentId"],
        message: `Ierarhia grupurilor conține un ciclu la ${groupId}.`,
      });
      return;
    }
    if (visited.has(groupId)) return;
    active.add(groupId);
    const parentId = groups.get(groupId)?.parentId;
    if (parentId && groups.has(parentId)) visit(parentId);
    active.delete(groupId);
    visited.add(groupId);
  };
  document.groups.forEach((group) => visit(group.id));

  const sources = new Set(document.sources.map((source) => source.id));
  const items = new Map(document.items.map((item) => [item.id, item]));
  document.items.forEach((item, index) => {
    const group = groups.get(item.groupId);
    if (!group) {
      context.addIssue({
        code: "custom",
        path: ["items", index, "groupId"],
        message: `Grupul ${item.groupId} nu există.`,
      });
    } else if (group.milestoneId !== item.milestoneId) {
      context.addIssue({
        code: "custom",
        path: ["items", index, "milestoneId"],
        message: "Elementul trebuie să aparțină aceluiași jalon ca grupul său.",
      });
    }
    const duplicateSources = item.sourceIds.filter(
      (sourceId, sourceIndex) => item.sourceIds.indexOf(sourceId) !== sourceIndex,
    );
    if (duplicateSources.length > 0) {
      context.addIssue({
        code: "custom",
        path: ["items", index, "sourceIds"],
        message: `Sursa ${duplicateSources[0]} este referită de mai multe ori.`,
      });
    }
    item.sourceIds.forEach((sourceId, sourceIndex) => {
      if (!sources.has(sourceId)) {
        context.addIssue({
          code: "custom",
          path: ["items", index, "sourceIds", sourceIndex],
          message: `Sursa ${sourceId} nu există.`,
        });
      }
    });
  });

  const instalments = new Map(
    document.instalments.map((instalment) => [instalment.id, instalment]),
  );
  document.instalments.forEach((instalment, index) => {
    if (!items.has(instalment.itemId)) {
      context.addIssue({
        code: "custom",
        path: ["instalments", index, "itemId"],
        message: `Elementul ${instalment.itemId} nu există.`,
      });
    }
  });

  document.payments.forEach((payment, index) => {
    const item = items.get(payment.itemId);
    const instalment = instalments.get(payment.instalmentId);
    if (!item) {
      context.addIssue({
        code: "custom",
        path: ["payments", index, "itemId"],
        message: `Elementul ${payment.itemId} nu există.`,
      });
    }
    if (!instalment) {
      context.addIssue({
        code: "custom",
        path: ["payments", index, "instalmentId"],
        message: `Tranșa ${payment.instalmentId} nu există.`,
      });
    } else if (instalment.itemId !== payment.itemId) {
      context.addIssue({
        code: "custom",
        path: ["payments", index, "instalmentId"],
        message: "Plata și tranșa trebuie să aparțină aceluiași element.",
      });
    }
  });
}

export function parseBudgetDocument(input: unknown): BudgetDocument {
  return budgetDocumentSchema.parse(input);
}

export function formatValidationIssues(error: z.ZodError): string[] {
  return error.issues.map((issue) => {
    const path = issue.path.length > 0 ? issue.path.join(".") : "document";
    return `${path}: ${issue.message}`;
  });
}
