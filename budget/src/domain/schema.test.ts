import { describe, expect, it } from "vitest";

import {
  makeBeneficiary,
  makeDocument,
  makeGroup,
  makeInstalment,
  makeItem,
  makePayment,
  makeSource,
} from "../test/builders.js";
import {
  budgetAreaIdSchema,
  budgetDocumentSchema,
  isoMonthSchema,
  parseBudgetDocument,
  estimateAmountsSchema,
  paymentModeSchema,
} from "./schema.js";

describe("budgetDocumentSchema", () => {
  it("requires all five milestones and rejects a reversed interval", () => {
    const document = makeDocument();
    expect(parseBudgetDocument(document)).toEqual(document);
    expect(
      budgetDocumentSchema.safeParse({
        ...document,
        milestones: document.milestones.filter((milestone) => milestone.id !== "extra"),
      }).success,
    ).toBe(false);
    expect(
      budgetDocumentSchema.safeParse({
        ...document,
        milestones: document.milestones.map((milestone) =>
          milestone.id === "extra" ? { ...milestone, startDate: "2032-06" } : milestone,
        ),
      }).success,
    ).toBe(false);
  });
  it("accepts a fully linked document", () => {
    expect(parseBudgetDocument(makeDocument())).toEqual(makeDocument());
  });

  it("accepts only the stable record ID in a brief reference", () => {
    const document = makeDocument();
    const withStatus = {
      ...document,
      items: document.items.map((item) => ({
        ...item,
        briefReferences: [{ recordId: "household-brief", status: "required" }],
      })),
    };
    expect(budgetDocumentSchema.safeParse(withStatus).success).toBe(false);
  });

  it("accepts only calendar months as planning values", () => {
    const document = makeDocument();
    expect(isoMonthSchema.safeParse("2027-02").success).toBe(true);
    expect(isoMonthSchema.safeParse("2027-02-01").success).toBe(false);
    expect(isoMonthSchema.safeParse("2027-13").success).toBe(false);
    expect(
      budgetDocumentSchema.safeParse({
        ...document,
        instalments: document.instalments.map((instalment) => ({
          ...instalment,
          dueOn: `${instalment.dueOn ?? "2027-01"}-20`,
        })),
      }).success,
    ).toBe(false);
  });

  it("accepts only catalogue area IDs while keeping schema-v1 area metadata optional", () => {
    const legacyDocument = makeDocument();
    expect(parseBudgetDocument(legacyDocument)).toEqual(legacyDocument);
    expect(budgetAreaIdSchema.safeParse("G-LIV").success).toBe(true);
    expect(
      budgetDocumentSchema.safeParse({
        ...legacyDocument,
        items: legacyDocument.items.map((item) => ({ ...item, areaId: "camera-inventata" })),
      }).success,
    ).toBe(false);
    expect(
      parseBudgetDocument({
        ...legacyDocument,
        items: legacyDocument.items.map((item) => ({ ...item, areaId: "G-LIV" })),
      }).items[0]?.areaId,
    ).toBe("G-LIV");
  });

  it("accepts exactly one estimate amount", () => {
    expect(estimateAmountsSchema.safeParse({ baseCents: 120 }).success).toBe(true);
    expect(estimateAmountsSchema.safeParse({ lowCents: 100 }).success).toBe(false);
    expect(estimateAmountsSchema.safeParse({ baseCents: 120, highCents: 150 }).success).toBe(false);
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

  it("requires a payment mode on every item", () => {
    const document = makeDocument();
    expect(
      budgetDocumentSchema.safeParse({
        ...document,
        items: document.items.map(({ paymentMode: _paymentMode, ...item }) => item),
      }).success,
    ).toBe(false);
  });

  it("rejects retired project budget limits and assumptions", () => {
    const document = makeDocument();
    for (const retired of [
      "coreBudgetTargetCents",
      "coreBudgetCapCents",
      "annualGrowthBps",
      "contingencyBps",
    ]) {
      expect(
        budgetDocumentSchema.safeParse({
          ...document,
          project: { ...document.project, [retired]: 1_000 },
        }).success,
      ).toBe(false);
    }
  });

  it("accepts revised fractional areas while rejecting mismatched quantity-based estimates", () => {
    const input = makeDocument();
    input.project.builtAreaSqm = 251.4;
    const item = input.items[0];
    if (!item) throw new Error("Fixture needs a budget item");
    item.estimate = {
      kind: "quantity-rate",
      quantity: 251.4,
      quantityBasis: "built-area",
      unit: "m²",
      rates: { baseCents: 11000 },
      fixed: false,
      pricedOn: "2026-09-20",
    };
    expect(parseBudgetDocument(input).project.builtAreaSqm).toBe(251.4);
    item.estimate.quantity = 260;
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

  it("rejects altered invariants and milestone dates", () => {
    const input = makeDocument();
    const result = budgetDocumentSchema.safeParse({
      ...input,
      milestones: input.milestones.map((milestone) =>
        milestone.id === "la-cheie" ? { ...milestone, date: "2028-10" } : milestone,
      ),
    });
    expect(result.success).toBe(false);
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

  it("accepts brand and the built-area quantity basis", () => {
    const input = makeDocument({
      items: [
        makeItem({
          brand: "Miele",
          estimate: {
            kind: "quantity-rate",
            quantity: 260,
            quantityBasis: "built-area",
            unit: "m²",
            rates: { baseCents: 120 },
            fixed: false,
            pricedOn: "2026-09-18",
          },
        }),
      ],
    });
    expect(parseBudgetDocument(input).items[0]?.brand).toBe("Miele");
  });

  it("rejects the retired `supplier` key", () => {
    const document = makeDocument();
    const input = { ...document, items: [{ ...makeItem(), supplier: "Constructor Exemplu SRL" }] };
    expect(budgetDocumentSchema.safeParse(input).success).toBe(false);
  });

  it("requires the beneficiaries collection", () => {
    const document = makeDocument();
    const missing = { ...document } as Record<string, unknown>;
    delete missing.beneficiaries;
    expect(budgetDocumentSchema.safeParse(missing).success).toBe(false);
  });

  it("accepts beneficiaries and an item's beneficiaryId reference", () => {
    const beneficiary = makeBeneficiary({
      id: "constructor-exemplu",
      name: "Constructor Exemplu",
      phone: "0700 000 000",
      email: "contact@example.com",
      website: "https://example.com/",
    });
    const document = makeDocument({
      beneficiaries: [beneficiary],
      items: [makeItem({ beneficiaryId: "constructor-exemplu" })],
    });
    const parsed = parseBudgetDocument(document);
    expect(parsed.beneficiaries).toEqual([beneficiary]);
    expect(parsed.items[0]?.beneficiaryId).toBe("constructor-exemplu");
  });

  it("rejects an item referencing an unknown beneficiaryId", () => {
    const document = makeDocument({
      items: [makeItem({ beneficiaryId: "no-such-beneficiary" })],
    });
    const result = budgetDocumentSchema.safeParse(document);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((issue) => issue.message).join(" ")).toContain("nu există");
    }
  });

  it("rejects a beneficiary ID colliding with another collection's ID", () => {
    const document = makeDocument({
      beneficiaries: [makeBeneficiary({ id: "constructie" })],
    });
    expect(budgetDocumentSchema.safeParse(document).success).toBe(false);
  });

  it("rejects the reserved beneficiary id «tbd»", () => {
    const document = makeDocument({
      beneficiaries: [makeBeneficiary({ id: "tbd" })],
    });
    expect(budgetDocumentSchema.safeParse(document).success).toBe(false);
  });

  it("rejects an invalid beneficiary email", () => {
    const document = makeDocument({
      beneficiaries: [makeBeneficiary({ email: "not-an-email" })],
    });
    expect(budgetDocumentSchema.safeParse(document).success).toBe(false);
  });

  it("rejects a non-http beneficiary website", () => {
    const document = makeDocument({
      beneficiaries: [makeBeneficiary({ website: "ftp://example.com" })],
    });
    expect(budgetDocumentSchema.safeParse(document).success).toBe(false);
  });

  it("rejects unsafe quantity products and a wrong built-area quantity", () => {
    const unsafe = makeItem({
      estimate: {
        kind: "quantity-rate",
        quantity: 1_000_000_000,
        unit: "unitate",
        rates: { baseCents: 100_000_000_000 },
        fixed: false,
        pricedOn: "2026-09-18",
      },
    });
    const wrongArea = makeItem({
      estimate: {
        kind: "quantity-rate",
        quantity: 261,
        quantityBasis: "built-area",
        unit: "m²",
        rates: { baseCents: 120 },
        fixed: false,
        pricedOn: "2026-09-18",
      },
    });
    expect(budgetDocumentSchema.safeParse(makeDocument({ items: [unsafe] })).success).toBe(false);
    expect(budgetDocumentSchema.safeParse(makeDocument({ items: [wrongArea] })).success).toBe(
      false,
    );
  });

  it("rejects non-http source URLs", () => {
    const document = makeDocument();
    expect(
      budgetDocumentSchema.safeParse({
        ...document,
        sources: [makeSource({ url: "file:///tmp/oferta" })],
      }).success,
    ).toBe(false);
  });
});
