import {
  budgetDocumentSchema,
  type BudgetDocument,
  type BudgetItem,
  type Instalment,
} from "./schema.js";
import { allocateProportionally, estimateCents } from "./selectors.js";

/** One validated edit to a single cost item; every operation returns a new, schema-checked document. */
export class CostEditError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CostEditError";
  }
}

export interface AddCostInput {
  id: string;
  groupId: string;
  label: string;
  baseCents: number;
  pricedOn: string;
  dueMonths: readonly string[];
  fields?: Partial<BudgetItem>;
}

/** Parses a euro amount with at most two decimals into integer cents. */
export function parseEuroCents(value: string): number {
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(value.trim());
  if (!match)
    throw new CostEditError(`Invalid euro amount "${value}"; use digits with up to two decimals.`);
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
}

function findItem(document: BudgetDocument, id: string): BudgetItem {
  const item = document.items.find((candidate) => candidate.id === id);
  if (!item) throw new CostEditError(`Unknown cost item "${id}".`);
  return item;
}

function assertNoPayments(document: BudgetDocument, itemId: string, action: string): void {
  if (document.payments.some((payment) => payment.itemId === itemId)) {
    throw new CostEditError(
      `Cannot ${action} "${itemId}": it has recorded payments. Edit it by hand.`,
    );
  }
}

function leafGroup(document: BudgetDocument, groupId: string): BudgetDocument["groups"][number] {
  const group = document.groups.find((candidate) => candidate.id === groupId);
  if (!group) throw new CostEditError(`Unknown category "${groupId}".`);
  if (document.groups.some((candidate) => candidate.parentId === groupId)) {
    throw new CostEditError(
      `Category "${groupId}" has subcategories; items belong only in leaf categories.`,
    );
  }
  return group;
}

function nextSortOrder(document: BudgetDocument, groupId: string): number {
  const orders = document.items
    .filter((item) => item.groupId === groupId)
    .map((item) => item.sortOrder);
  return orders.length === 0 ? 1 : Math.max(...orders) + 1;
}

/** Places an item at the end of a leaf category and derives the fields the schema couples to it. */
function placeItem(document: BudgetDocument, item: BudgetItem, groupId: string): BudgetItem {
  const group = leafGroup(document, groupId);
  return {
    ...item,
    groupId,
    milestoneId: group.milestoneId,
    sortOrder: nextSortOrder(document, groupId),
    contingencyEligible: item.costScope === "core" && item.costType !== "land",
  };
}

function itemInstalments(document: BudgetDocument, itemId: string): Instalment[] {
  return document.instalments.filter((instalment) => instalment.itemId === itemId);
}

/** Reallocates an item's instalments to a new total, exact to the cent, keeping their dates. */
function reallocate(instalments: readonly Instalment[], targetCents: number): Instalment[] {
  if (instalments.length === 0) return [];
  const weights = instalments.map((instalment) => instalment.projectedCents);
  const shares = weights.every((weight) => weight === 0)
    ? allocateProportionally(
        targetCents,
        weights.map(() => 1),
      )
    : allocateProportionally(targetCents, weights);
  return instalments.map((instalment, index) => ({
    ...instalment,
    projectedCents: shares[index] ?? 0,
  }));
}

/** Swaps in reallocated instalments in place, keeping the file order of every record. */
function replaceInstalments(document: BudgetDocument, next: readonly Instalment[]): Instalment[] {
  const byId = new Map(next.map((instalment) => [instalment.id, instalment]));
  return document.instalments.map((instalment) => byId.get(instalment.id) ?? instalment);
}

function validated(document: BudgetDocument): BudgetDocument {
  const result = budgetDocumentSchema.safeParse(document);
  if (!result.success) {
    const issues = result.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`);
    throw new CostEditError(`The edit breaks the budget schema:\n${issues.join("\n")}`);
  }
  return result.data;
}

export function addCost(document: BudgetDocument, input: AddCostInput): BudgetDocument {
  if (document.items.some((item) => item.id === input.id)) {
    throw new CostEditError(`Cost item "${input.id}" already exists.`);
  }
  const base: BudgetItem = {
    id: input.id,
    label: input.label,
    groupId: input.groupId,
    milestoneId: "la-rosu",
    sortOrder: 0,
    costScope: "core",
    costType: "work",
    paymentMode: "one-off",
    contingencyEligible: true,
    included: true,
    archived: false,
    ownership: "planned",
    completion: { complete: false },
    estimate: {
      kind: "total",
      amounts: { baseCents: input.baseCents },
      fixed: false,
      pricedOn: input.pricedOn,
    },
    briefReferences: [],
    sourceIds: [],
    ...input.fields,
  };
  const item = placeItem(document, { ...base, id: input.id, label: input.label }, input.groupId);
  const shares =
    input.dueMonths.length === 0
      ? []
      : allocateProportionally(
          estimateCents(item.estimate),
          input.dueMonths.map(() => 1),
        );
  const instalments = input.dueMonths.map((dueOn, index) => ({
    id: `ins-${item.id}-${index + 1}`,
    itemId: item.id,
    label: "Plată estimată",
    dueOn,
    projectedCents: shares[index] ?? 0,
  }));
  return validated({
    ...document,
    items: [...document.items, item],
    instalments: [...document.instalments, ...instalments],
  });
}

export function deleteCost(document: BudgetDocument, id: string): BudgetDocument {
  findItem(document, id);
  assertNoPayments(document, id, "delete");
  return validated({
    ...document,
    items: document.items.filter((item) => item.id !== id),
    instalments: document.instalments.filter((instalment) => instalment.itemId !== id),
  });
}

export function moveCost(document: BudgetDocument, id: string, groupId: string): BudgetDocument {
  const item = findItem(document, id);
  if (item.groupId === groupId) throw new CostEditError(`"${id}" is already in "${groupId}".`);
  const others = { ...document, items: document.items.filter((candidate) => candidate.id !== id) };
  const moved = placeItem(others, item, groupId);
  return validated({
    ...document,
    items: document.items.map((candidate) => (candidate.id === id ? moved : candidate)),
  });
}

export function renameCost(document: BudgetDocument, id: string, label: string): BudgetDocument {
  findItem(document, id);
  return validated({
    ...document,
    items: document.items.map((item) => (item.id === id ? { ...item, label: label.trim() } : item)),
  });
}

/** Sets a total estimate, or the unit rate of a quantity × rate estimate, and reallocates instalments. */
export function setCostPrice(
  document: BudgetDocument,
  id: string,
  cents: number,
  pricedOn: string,
): BudgetDocument {
  const item = findItem(document, id);
  const estimate: BudgetItem["estimate"] =
    item.estimate.kind === "total"
      ? { ...item.estimate, amounts: { baseCents: cents }, pricedOn }
      : { ...item.estimate, rates: { baseCents: cents }, pricedOn };
  const updated = { ...item, estimate };
  const instalments = reallocate(itemInstalments(document, id), estimateCents(estimate));
  return validated({
    ...document,
    items: document.items.map((candidate) => (candidate.id === id ? updated : candidate)),
    instalments: replaceInstalments(document, instalments),
  });
}

export interface SplitCostInput {
  id: string;
  newId: string;
  newLabel: string;
  cents: number;
  fields?: Partial<BudgetItem>;
}

/** Moves part of a total estimate into a new item that inherits the source fields and instalment dates. */
export function splitCost(document: BudgetDocument, input: SplitCostInput): BudgetDocument {
  const source = findItem(document, input.id);
  assertNoPayments(document, input.id, "split");
  if (source.estimate.kind !== "total") {
    throw new CostEditError(`Only total estimates can be split; "${input.id}" is quantity × rate.`);
  }
  if (document.items.some((item) => item.id === input.newId)) {
    throw new CostEditError(`Cost item "${input.newId}" already exists.`);
  }
  const sourceCents = source.estimate.amounts.baseCents;
  if (input.cents <= 0 || input.cents >= sourceCents) {
    throw new CostEditError(`The split amount must be above 0 and below ${sourceCents} cents.`);
  }
  const remainingCents = sourceCents - input.cents;
  const reduced: BudgetItem = {
    ...source,
    estimate: { ...source.estimate, amounts: { baseCents: remainingCents } },
  };
  const draft: BudgetItem = {
    ...source,
    ...input.fields,
    id: input.newId,
    label: input.newLabel,
    estimate: { ...source.estimate, amounts: { baseCents: input.cents } },
  };
  const placed = placeItem(document, draft, draft.groupId);
  const sourceInstalments = itemInstalments(document, input.id);
  const newInstalments = reallocate(sourceInstalments, input.cents).map((instalment, index) => ({
    ...instalment,
    id: `ins-${input.newId}-${index + 1}`,
    itemId: input.newId,
  }));
  return validated({
    ...document,
    items: [...document.items.map((item) => (item.id === input.id ? reduced : item)), placed],
    instalments: [
      ...replaceInstalments(document, reallocate(sourceInstalments, remainingCents)),
      ...newInstalments,
    ],
  });
}
