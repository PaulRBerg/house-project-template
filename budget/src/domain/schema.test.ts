import { describe, expect, it } from "vitest";

import {
  budgetAreaIdSchema,
  budgetDocumentSchema,
  isoMonthSchema,
  parseBudgetDocument,
  paymentModeSchema,
  scenarioAmountsSchema,
  scenarioSchema,
} from "./schema.js";
import {
  makeDocument,
  makeGroup,
  makeInstalment,
  makeItem,
  makePayment,
  makeSource,
} from "./test-fixtures.js";

describe("budgetDocumentSchema", () => {
  it("accepts a fully linked document", () => {
    expect(parseBudgetDocument(makeDocument())).toEqual(makeDocument());
  });

  it("normalizes valid legacy planning days to months", () => {
    const document = makeDocument();
    const legacy = {
      ...document,
      milestones: document.milestones.map((milestone) => ({
        ...milestone,
        date: `${milestone.date}-01`,
      })),
      instalments: document.instalments.map((instalment) => ({
        ...instalment,
        dueOn: instalment.dueOn ? `${instalment.dueOn}-20` : undefined,
      })),
    };

    expect(parseBudgetDocument(legacy)).toEqual(document);
    expect(isoMonthSchema.safeParse("2027-02-30").success).toBe(false);
    expect(isoMonthSchema.safeParse("2027-13").success).toBe(false);
  });

  it("accepts only catalogue area IDs while keeping schema-v1 area metadata optional", () => {
    const legacyDocument = makeDocument();
    expect(parseBudgetDocument(legacyDocument)).toEqual(legacyDocument);
    expect(budgetAreaIdSchema.safeParse("living-room").success).toBe(true);
    expect(
      budgetDocumentSchema.safeParse({
        ...legacyDocument,
        items: legacyDocument.items.map((item) => ({ ...item, areaId: "camera-inventata" })),
      }).success,
    ).toBe(false);
    expect(
      parseBudgetDocument({
        ...legacyDocument,
        items: legacyDocument.items.map((item) => ({ ...item, areaId: "living-room" })),
      }).items[0]?.areaId,
    ).toBe("living-room");
  });

  it("accepts only Optimist and Prudent, ordered by cost", () => {
    expect(scenarioSchema.options).toEqual(["base", "high"]);
    expect(scenarioSchema.safeParse("low").success).toBe(false);
    expect(scenarioAmountsSchema.safeParse({ baseCents: 120, highCents: 100 }).success).toBe(false);
    expect(scenarioAmountsSchema.safeParse({ baseCents: 120, highCents: 120 }).success).toBe(true);
    expect(scenarioAmountsSchema.safeParse({ lowCents: 100, highCents: 150 }).success).toBe(false);
    expect(
      scenarioAmountsSchema.safeParse({ baseCents: 120, highCents: 150, unexpected: 100 }).success,
    ).toBe(false);
  });

  it("accepts only the two payment presentation modes", () => {
    const document = makeDocument();
    expect(paymentModeSchema.options).toEqual(["one-off", "partial-progress"]);
    expect(
      budgetDocumentSchema.safeParse({
        ...document,
        items: document.items.map((item) => ({ ...item, paymentMode: "instalments" })),
      }).success,
    ).toBe(false);
  });

  it("defaults legacy schema-v1 items to partial progress without mutating the input", () => {
    const document = makeDocument();
    const legacy = {
      ...document,
      items: document.items.map(({ paymentMode: _paymentMode, ...item }) => item),
    };

    expect(parseBudgetDocument(legacy)).toEqual(document);
    expect(legacy.items[0]).not.toHaveProperty("paymentMode");
  });

  it("opens both legacy estimate kinds without changing retained amounts or accounting data", () => {
    const document = makeDocument({
      items: [
        makeItem(),
        makeItem({
          id: "cantitate",
          estimate: {
            kind: "quantity-rate",
            quantity: 48,
            quantityBasis: "built-area",
            unit: "m²",
            rates: { baseCents: 120, highCents: 150 },
            fixed: false,
            pricedOn: "2026-09-18",
          },
        }),
      ],
      payments: [makePayment()],
    });
    const legacy = {
      ...document,
      items: document.items.map((item) => ({
        ...item,
        estimate:
          item.estimate.kind === "total"
            ? { ...item.estimate, amounts: { ...item.estimate.amounts, lowCents: 90 } }
            : { ...item.estimate, rates: { ...item.estimate.rates, lowCents: 90 } },
      })),
    };
    expect(parseBudgetDocument(legacy)).toEqual(document);
    expect(legacy.items[0]?.estimate).toMatchObject({ amounts: { lowCents: 90 } });
    expect(parseBudgetDocument(parseBudgetDocument(legacy))).toEqual(document);
  });

  it("opens older v1 backups without restoring retired budget limits", () => {
    const document = makeDocument();
    const legacy = {
      ...document,
      project: {
        ...document.project,
        coreBudgetTargetCents: 1_000_000,
        coreBudgetCapCents: 2_000_000,
      },
    };
    expect(parseBudgetDocument(legacy)).toEqual(document);
    expect(
      budgetDocumentSchema.safeParse({
        ...legacy,
        project: { ...legacy.project, unexpected: true },
      }).success,
    ).toBe(false);
  });

  it("accepts revised fractional areas while rejecting mismatched quantity-based estimates", () => {
    const input = makeDocument();
    input.project.builtAreaSqm = 48.5;
    const item = input.items[0];
    if (!item) throw new Error("Fixture needs a budget item");
    item.estimate = {
      kind: "quantity-rate",
      quantity: 48.5,
      quantityBasis: "built-area",
      unit: "m²",
      rates: { baseCents: 100, highCents: 150 },
      fixed: false,
      pricedOn: "2026-09-20",
    };
    expect(parseBudgetDocument(input).project.builtAreaSqm).toBe(48.5);
    item.estimate.quantity = 49;
    const result = budgetDocumentSchema.safeParse(input);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toEqual(["items", 0, "estimate", "quantity"]);
    }
    expect(
      budgetDocumentSchema.safeParse({ ...input, project: { ...input.project, builtAreaSqm: 0 } })
        .success,
    ).toBe(false);
  });

  it("accepts project milestone dates while requiring every known ID once", () => {
    const input = makeDocument();
    const revised = budgetDocumentSchema.safeParse({
      ...input,
      milestones: input.milestones.map((milestone) =>
        milestone.id === "la-cheie" ? { ...milestone, date: "2031-02" } : milestone,
      ),
    });
    expect(revised.success).toBe(true);

    const duplicate = budgetDocumentSchema.safeParse({
      ...input,
      milestones: input.milestones.map((milestone) =>
        milestone.id === "la-mutat" ? { ...milestone, id: "la-cheie" } : milestone,
      ),
    });
    expect(duplicate.success).toBe(false);
  });

  it("rejects orphaned, cyclic, and cross-stage hierarchy references", () => {
    const groups = [
      makeGroup({ id: "parinte", parentId: "copil" }),
      makeGroup({ id: "copil", parentId: "parinte", milestoneId: "la-gri" }),
    ];
    const result = budgetDocumentSchema.safeParse(
      makeDocument({
        groups,
        items: [makeItem({ groupId: "lipsa" })],
        instalments: [makeInstalment({ itemId: "lipsa" })],
      }),
    );
    expect(result.success).toBe(false);
    if (!result.success) {
      const messages = result.error.issues.map((issue) => issue.message).join(" ");
      expect(messages).toContain("ciclu");
      expect(messages).toContain("aceluiași jalon");
      expect(messages).toContain("nu există");
    }
  });

  it("rejects mismatched payments and unknown sources", () => {
    const secondItem = makeItem({ id: "acoperis", sortOrder: 1, sourceIds: ["sursa-lipsa"] });
    const result = budgetDocumentSchema.safeParse(
      makeDocument({
        items: [makeItem(), secondItem],
        payments: [makePayment({ itemId: "acoperis" })],
      }),
    );
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((issue) => issue.message).join(" ")).toContain(
        "aceluiași element",
      );
    }
  });

  it("enforces the land and movable contingency policy", () => {
    const land = makeItem({
      id: "teren",
      costType: "land",
      contingencyEligible: true,
    });
    const movable = makeItem({
      id: "mobila",
      costScope: "movable",
      costType: "movable-good",
      contingencyEligible: true,
    });
    expect(budgetDocumentSchema.safeParse(makeDocument({ items: [land, movable] })).success).toBe(
      false,
    );
  });

  it("accepts bounded editable assumptions, supplier, and the built-area quantity basis", () => {
    const input = makeDocument({
      project: {
        ...makeDocument().project,
        annualGrowthBps: 750,
        contingencyBps: 1_500,
      },
      items: [
        makeItem({
          supplier: "Example supplier",
          estimate: {
            kind: "quantity-rate",
            quantity: 48,
            quantityBasis: "built-area",
            unit: "m²",
            rates: { baseCents: 120, highCents: 150 },
            fixed: false,
            pricedOn: "2026-09-18",
          },
        }),
      ],
    });
    expect(parseBudgetDocument(input).project).toMatchObject({
      annualGrowthBps: 750,
      contingencyBps: 1_500,
    });
    expect(parseBudgetDocument(input).items[0]?.supplier).toBe("Example supplier");
  });

  it("rejects unsafe quantity products and a wrong built-area quantity", () => {
    const unsafe = makeItem({
      estimate: {
        kind: "quantity-rate",
        quantity: 1_000_000_000,
        unit: "unitate",
        rates: {
          baseCents: 100_000_000_000,
          highCents: 100_000_000_000,
        },
        fixed: false,
        pricedOn: "2026-09-18",
      },
    });
    const wrongArea = makeItem({
      estimate: {
        kind: "quantity-rate",
        quantity: 49,
        quantityBasis: "built-area",
        unit: "m²",
        rates: { baseCents: 120, highCents: 150 },
        fixed: false,
        pricedOn: "2026-09-18",
      },
    });
    expect(budgetDocumentSchema.safeParse(makeDocument({ items: [unsafe] })).success).toBe(false);
    expect(budgetDocumentSchema.safeParse(makeDocument({ items: [wrongArea] })).success).toBe(
      false,
    );
  });

  it("rejects out-of-range assumptions and non-http source URLs", () => {
    const document = makeDocument();
    expect(
      budgetDocumentSchema.safeParse({
        ...document,
        project: { ...document.project, annualGrowthBps: 2_501, contingencyBps: 5_001 },
      }).success,
    ).toBe(false);
    expect(
      budgetDocumentSchema.safeParse({
        ...document,
        sources: [makeSource({ url: "file:///tmp/oferta" })],
      }).success,
    ).toBe(false);
  });
});
