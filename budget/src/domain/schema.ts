import { z } from "zod";

import { BUDGET_AREA_IDS } from "./areas.js";

/** Fixed risk reserve over eligible future house costs; the household chose not to tune it. */
export const CONTINGENCY_BPS = 1_000 as const;
export const MAX_MONEY_CENTS = 100_000_000_000 as const;
/** Basis points in one whole (100 %). */
export const BPS_DENOMINATOR = 10_000 as const;

/** Reserved beneficiary ID for items without a known payee. */
export const TBD_BENEFICIARY_ID = "tbd";

export const FIXED_MILESTONES = {
  "la-rosu": "2027-09",
  "la-gri": "2027-12",
  "la-cheie": "2028-09",
  "la-mutat": "2029-06",
} as const;

/** Separate post-move budget; every other milestone belongs to the initial budget. */
export const EXTRA_MILESTONE_ID = "extra";

const MILESTONE_IDS: ReadonlyArray<keyof typeof FIXED_MILESTONES | typeof EXTRA_MILESTONE_ID> = [
  ...(Object.keys(FIXED_MILESTONES) as Array<keyof typeof FIXED_MILESTONES>),
  EXTRA_MILESTONE_ID,
];

/** Record collections of a budget document, in canonical file order. */
export const RECORD_COLLECTION_KEYS = [
  "milestones",
  "groups",
  "items",
  "sources",
  "beneficiaries",
  "instalments",
  "payments",
] as const;

const idSchema = z
  .string()
  .min(1)
  .max(100)
  .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Folosește un ID stabil în kebab-case.");

const labelSchema = z.string().trim().min(1).max(240);
const noteSchema = z.string().trim().max(500);
const sortOrderSchema = z.number().int().nonnegative();
const euroCentsSchema = z.number().int().nonnegative().max(MAX_MONEY_CENTS);

function isHttpUrl(value: string): boolean {
  try {
    const protocol = new URL(value).protocol;
    return protocol === "http:" || protocol === "https:";
  } catch {
    return false;
  }
}

export function isCalendarDate(value: string): boolean {
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

/** Month-level planning value. */
export const isoMonthSchema = z
  .string()
  .refine(isCalendarMonth, "Luna trebuie să fie o valoare calendaristică ISO YYYY-MM.");

export const paymentModeSchema = z.enum(["one-off", "partial-progress"]);

export const budgetAreaIdSchema = z.enum(BUDGET_AREA_IDS);

export const estimateAmountsSchema = z.object({ baseCents: euroCentsSchema }).strict();

const totalEstimateSchema = z
  .object({
    kind: z.literal("total"),
    amounts: estimateAmountsSchema,
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
    rates: estimateAmountsSchema,
    fixed: z.boolean(),
    pricedOn: isoDateSchema,
  })
  .strict()
  .superRefine((estimate, context) => {
    const amountCents = quantityRateCents(estimate);
    if (!Number.isSafeInteger(amountCents) || amountCents > MAX_MONEY_CENTS) {
      context.addIssue({
        code: "custom",
        path: ["rates", "baseCents"],
        message: `Cantitatea înmulțită cu tariful trebuie să producă maximum ${MAX_MONEY_CENTS} cenți întregi siguri.`,
      });
    }
  });

/** Unvalidated quantity × rate product in cents. */
export function quantityRateCents(estimate: {
  quantity: number;
  rates: { baseCents: number };
}): number {
  return Math.round(estimate.quantity * estimate.rates.baseCents);
}

export const estimateSchema = z.discriminatedUnion("kind", [
  totalEstimateSchema,
  quantityRateEstimateSchema,
]);

export const milestoneSchema = z
  .object({
    id: z.enum(MILESTONE_IDS),
    label: labelSchema,
    startDate: isoMonthSchema.optional(),
    date: isoMonthSchema,
  })
  .strict();

export const groupSchema = z
  .object({
    id: idSchema,
    label: labelSchema,
    parentId: idSchema.nullable(),
    milestoneId: milestoneSchema.shape.id,
    sortOrder: sortOrderSchema,
    archived: z.boolean(),
  })
  .strict();

export const briefReferenceSchema = z
  .object({
    recordId: z.string().trim().min(1).max(160),
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
    beneficiaryId: idSchema.optional(),
    milestoneId: milestoneSchema.shape.id,
    sortOrder: sortOrderSchema,
    costScope: z.enum(["core", "movable"]),
    costType: z.enum(["land", "work", "professional-fee", "system", "movable-good", "other"]),
    paymentMode: paymentModeSchema,
    contingencyEligible: z.boolean(),
    included: z.boolean(),
    archived: z.boolean(),
    ownership: z.enum(["planned", "owned"]),
    completion: completionSchema,
    estimate: estimateSchema,
    brand: labelSchema.optional(),
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

export const beneficiarySchema = z
  .object({
    id: idSchema,
    name: labelSchema,
    phone: z.string().trim().min(1).max(40).optional(),
    email: z.email().optional(),
    website: z
      .url()
      .refine(isHttpUrl, "Site-ul trebuie să folosească un URL http sau https.")
      .optional(),
  })
  .strict()
  .superRefine((beneficiary, context) => {
    if (beneficiary.id === TBD_BENEFICIARY_ID) {
      context.addIssue({
        code: "custom",
        path: ["id"],
        message: "ID-ul «tbd» este rezervat elementelor fără beneficiar.",
      });
    }
  });

export const sourceSchema = z
  .object({
    id: idSchema,
    title: labelSchema,
    url: z.url().refine(isHttpUrl, "Sursa trebuie să folosească un URL http sau https."),
    accessedOn: isoDateSchema,
    scope: noteSchema.min(1),
    tax: z
      .object({
        status: z.enum(["included", "excluded", "not-applicable", "unknown"]),
        rateBps: z.number().int().min(0).max(BPS_DENOMINATOR).optional(),
      })
      .strict(),
    confidence: z.enum(["low", "medium", "high"]),
    provenance: z
      .object({
        currency: z.string().trim().length(3).toUpperCase(),
        quotedAmountMinor: z.number().int().nonnegative().optional(),
        note: noteSchema.optional(),
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
    note: noteSchema.optional(),
  })
  .strict();

export const projectSchema = z
  .object({
    id: idSchema,
    name: labelSchema,
    location: labelSchema,
    currency: z.literal("EUR"),
    builtAreaSqm: z.number().positive().finite().max(1_000_000),
  })
  .strict();

export const budgetDocumentSchema = z
  .object({
    schemaVersion: z.literal(1),
    project: projectSchema,
    milestones: z.array(milestoneSchema).length(MILESTONE_IDS.length),
    groups: z.array(groupSchema),
    items: z.array(itemSchema),
    sources: z.array(sourceSchema),
    beneficiaries: z.array(beneficiarySchema),
    instalments: z.array(instalmentSchema),
    payments: z.array(paymentSchema),
  })
  .strict()
  .superRefine(validateDocumentReferences);

export type EstimateAmounts = z.infer<typeof estimateAmountsSchema>;
export type Estimate = z.infer<typeof estimateSchema>;
export type Milestone = z.infer<typeof milestoneSchema>;
export type BudgetGroup = z.infer<typeof groupSchema>;
export type BriefReference = z.infer<typeof briefReferenceSchema>;
export type BudgetItem = z.infer<typeof itemSchema>;
export type BudgetSource = z.infer<typeof sourceSchema>;
export type Beneficiary = z.infer<typeof beneficiarySchema>;
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

  const milestones = new Map(document.milestones.map((milestone) => [milestone.id, milestone]));
  document.milestones.forEach((milestone, index) => {
    if (milestone.startDate && milestone.startDate > milestone.date) {
      context.addIssue({
        code: "custom",
        path: ["milestones", index, "startDate"],
        message: "Începutul etapei trebuie să fie înaintea sfârșitului sau în aceeași lună.",
      });
    }
  });
  for (const [id, date] of Object.entries(FIXED_MILESTONES)) {
    const milestone = milestones.get(id as Milestone["id"]);
    if (!milestone || milestone.date !== date) {
      context.addIssue({
        code: "custom",
        path: ["milestones"],
        message: `Jalonul ${id} trebuie să aibă luna fixă ${date}.`,
      });
    }
  }

  const allIds = new Map<string, string>();
  for (const collectionName of RECORD_COLLECTION_KEYS) {
    const records: ReadonlyArray<{ id: string }> = document[collectionName];
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
  const beneficiaries = new Set(document.beneficiaries.map((beneficiary) => beneficiary.id));
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
    if (item.beneficiaryId !== undefined && !beneficiaries.has(item.beneficiaryId)) {
      context.addIssue({
        code: "custom",
        path: ["items", index, "beneficiaryId"],
        message: `Beneficiarul ${item.beneficiaryId} nu există.`,
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
