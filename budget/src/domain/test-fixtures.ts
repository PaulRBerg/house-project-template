import {
  DEFAULT_ANNUAL_GROWTH_BPS,
  DEFAULT_CONTINGENCY_BPS,
  type BudgetDocument,
  type BudgetGroup,
  type BudgetItem,
  type BudgetSource,
  type Instalment,
  type Payment,
} from "./schema.js";

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
      amounts: { baseCents: 10_000, highCents: 12_000 },
      fixed: true,
      pricedOn: "2030-01-01",
    },
    briefReferences: [],
    sourceIds: [],
    ...overrides,
  };
}

export function makeSource(overrides: Partial<BudgetSource> = {}): BudgetSource {
  return {
    id: "example-source",
    title: "Example source",
    url: "https://example.com/estimate",
    accessedOn: "2030-01-01",
    scope: "Fictional test evidence",
    tax: { status: "included", rateBps: 2_100 },
    confidence: "medium",
    ...overrides,
  };
}

export function makeInstalment(overrides: Partial<Instalment> = {}): Instalment {
  return {
    id: "transa-structura",
    itemId: "structura",
    label: "Tranșă structură",
    dueOn: "2030-03",
    projectedCents: 10_000,
    ...overrides,
  };
}

export function makePayment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: "plata-structura",
    itemId: "structura",
    instalmentId: "transa-structura",
    paidOn: "2030-02-01",
    amountCents: 2_000,
    ...overrides,
  };
}

export function makeDocument(overrides: Partial<BudgetDocument> = {}): BudgetDocument {
  return {
    schemaVersion: 1,
    project: {
      id: "demo-house",
      name: "Demo House",
      location: "Not specified",
      currency: "EUR",
      builtAreaSqm: 48,
      annualGrowthBps: DEFAULT_ANNUAL_GROWTH_BPS,
      contingencyBps: DEFAULT_CONTINGENCY_BPS,
    },
    milestones: [
      { id: "la-rosu", label: "La roșu", date: "2030-03" },
      { id: "la-gri", label: "La gri", date: "2030-06" },
      { id: "la-cheie", label: "La cheie", date: "2030-09" },
      { id: "la-mutat", label: "La mutat", date: "2030-10" },
    ],
    groups: [makeGroup()],
    items: [makeItem()],
    sources: [],
    instalments: [makeInstalment()],
    payments: [],
    ...overrides,
  };
}
