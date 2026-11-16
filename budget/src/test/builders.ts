import {
  EXTRA_MILESTONE_ID,
  FIXED_MILESTONES,
  type Beneficiary,
  type BudgetDocument,
  type BudgetGroup,
  type BudgetItem,
  type BudgetSource,
  type Instalment,
  type Payment,
} from "../domain/schema.js";

export function makeGroup(overrides: Partial<BudgetGroup> = {}): BudgetGroup {
  return {
    id: "constructie",
    label: "La roșu",
    parentId: null,
    milestoneId: "la-rosu",
    sortOrder: 0,
    archived: false,
    ...overrides,
  };
}

export function makeItem(overrides: Partial<BudgetItem> = {}): BudgetItem {
  return {
    id: "structura",
    label: "Structură",
    groupId: "constructie",
    milestoneId: "la-rosu",
    sortOrder: 0,
    costScope: "core",
    costType: "work",
    paymentMode: "partial-progress",
    contingencyEligible: true,
    included: true,
    archived: false,
    ownership: "planned",
    completion: { complete: false },
    estimate: {
      kind: "total",
      amounts: { baseCents: 10_000 },
      fixed: true,
      pricedOn: "2026-09-18",
    },
    briefReferences: [{ recordId: "budget-001" }],
    sourceIds: [],
    ...overrides,
  };
}

export function makeSource(overrides: Partial<BudgetSource> = {}): BudgetSource {
  return {
    id: "sursa-structura",
    title: "Ofertă structură",
    url: "https://example.com/oferta",
    accessedOn: "2026-09-18",
    scope: "Materiale și manoperă, fără finisaje",
    tax: { status: "included", rateBps: 2_100 },
    confidence: "medium",
    ...overrides,
  };
}

export function makeBeneficiary(overrides: Partial<Beneficiary> = {}): Beneficiary {
  return {
    id: "constructor-exemplu",
    name: "Constructor Exemplu",
    phone: "0700 000 000",
    website: "https://example.com/",
    ...overrides,
  };
}

export function makeInstalment(overrides: Partial<Instalment> = {}): Instalment {
  return {
    id: "transa-structura",
    itemId: "structura",
    label: "Tranșă structură",
    dueOn: "2027-09",
    projectedCents: 10_000,
    ...overrides,
  };
}

export function makePayment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: "plata-structura",
    itemId: "structura",
    instalmentId: "transa-structura",
    paidOn: "2026-11-20",
    amountCents: 2_000,
    ...overrides,
  };
}

export function makeDocument(overrides: Partial<BudgetDocument> = {}): BudgetDocument {
  return {
    schemaVersion: 1,
    project: {
      id: "casa-exemplu",
      name: "Casa Exemplu",
      location: "Comuna Exemplu, județul Exemplu, România",
      currency: "EUR",
      builtAreaSqm: 260,
    },
    milestones: [
      ...(
        [
          ["la-rosu", "La roșu"],
          ["la-gri", "La gri"],
          ["la-cheie", "La cheie"],
          ["la-mutat", "La mutat"],
        ] as const
      ).map(([id, label]) => ({ id, label, date: FIXED_MILESTONES[id] })),
      { id: EXTRA_MILESTONE_ID, label: "Extra", startDate: "2029-06", date: "2031-06" },
    ],
    groups: [makeGroup()],
    items: [makeItem()],
    sources: [],
    beneficiaries: [],
    instalments: [makeInstalment()],
    payments: [],
    ...overrides,
  };
}
