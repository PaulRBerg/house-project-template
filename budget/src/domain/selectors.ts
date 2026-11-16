import { BUDGET_AREAS, itemAreaId, type BudgetAreaId } from "./areas.js";
import { groupBy, sumCents, UI_LOCALE } from "./collections.js";
import { compareUndatedLast, dateSpan, monthKey } from "./dates.js";
import {
  BPS_DENOMINATOR,
  CONTINGENCY_BPS,
  EXTRA_MILESTONE_ID,
  MAX_MONEY_CENTS,
  quantityRateCents,
  type BudgetDocument,
  type BudgetGroup,
  type BudgetItem,
  type Estimate,
  type Instalment,
  type Milestone,
  type Payment,
} from "./schema.js";

const ROMANIAN_COLLATOR = new Intl.Collator(UI_LOCALE);

export interface BudgetViewOptions {
  /** Extra is a separate budget; callers must explicitly request it. */
  scope?: "initial" | "extra" | "all";
  /** Calendar date in the user's locale, as YYYY-MM-DD. */
  asOf: string;
}

export interface DerivedInstalment {
  id: string;
  itemId: string;
  label: string;
  dueOn?: string;
  /** Stored plan before subtracting actual payments. */
  projectedCents: number;
  actualPaidCents: number;
  remainingCents: number;
  overdue: boolean;
  active: boolean;
}

export interface EstimateDiscrepancy {
  /** Positive means unallocated estimate; negative means plan/actual above estimate. */
  amountCents: number;
  kind: "balanced" | "unallocated" | "over-scheduled";
}

export interface DerivedItem {
  item: BudgetItem;
  active: boolean;
  effectivelyArchived: boolean;
  scheduleStartOn?: string;
  scheduleFinalOn?: string;
  estimateCents: number;
  actualPaidCents: number;
  /** Table value includes active owned purchases at their historical price, counted once. */
  totalCents: number;
  /** Recorded payments plus historical owned value absent from the payment ledger. */
  settledCents: number;
  scheduledRemainingCents: number;
  unallocatedFutureCents: number;
  contingencyCents: number;
  forecastBeforeContingencyCents: number;
  forecastCents: number;
  /** Forecast still to be paid: active future obligations plus their contingency. */
  remainingForecastCents: number;
  overdueCents: number;
  discrepancy: EstimateDiscrepancy;
  instalments: DerivedInstalment[];
}

export interface BudgetSummary {
  actualPaidCents: number;
  totalCashForecastCents: number;
  remainingCashForecastCents: number;
}

export interface BudgetHierarchyItem {
  kind: "item";
  id: string;
  label: string;
  sortOrder: number;
  derived: DerivedItem;
}

export interface BudgetHierarchyGroup {
  kind: "group";
  id: string;
  /** Original catalogue group when this is a namespaced area-view subset. */
  sourceGroupId?: string;
  label: string;
  milestoneId: Milestone["id"];
  sortOrder: number;
  archived: boolean;
  scheduleStartOn?: string;
  scheduleFinalOn?: string;
  /** Current estimates for outstanding items plus settled values, including owned purchases. */
  estimateCents: number;
  totalCents: number;
  settledCents: number;
  children: Array<BudgetHierarchyGroup | BudgetHierarchyItem>;
}

export type CashFlowAllocationKind = "actual" | "scheduled" | "unallocated" | "contingency";

export interface CashFlowAllocation {
  id: string;
  itemId: string;
  instalmentId?: string;
  relatedAllocationId?: string;
  kind: CashFlowAllocationKind;
  date?: string;
  amountCents: number;
}

export interface CashFlowBucket {
  periodKey: string;
  actualCents: number;
  scheduledCents: number;
  unallocatedCents: number;
  /** Base obligation: scheduled plus unallocated amounts, excluding the reserve. */
  plannedCents: number;
  contingencyCents: number;
  totalCents: number;
  allocations: CashFlowAllocation[];
}

export interface MonthlyCashFlow {
  months: CashFlowBucket[];
  undated: CashFlowBucket;
}

export interface BudgetTimelineEntry {
  milestone: Milestone;
  forecastCents: number;
  itemCount: number;
  completeItemCount: number;
}

export interface UpcomingPayment {
  allocationId: string;
  itemId: string;
  itemLabel: string;
  instalmentId?: string;
  label: string;
  dueOn?: string;
  amountCents: number;
  contingencyCents: number;
  overdue: boolean;
  unallocated: boolean;
}

export interface BudgetView {
  summary: BudgetSummary;
  items: DerivedItem[];
  hierarchy: BudgetHierarchyGroup[];
  timeline: BudgetTimelineEntry[];
  upcomingPayments: UpcomingPayment[];
  allocations: CashFlowAllocation[];
}

interface ItemLedger {
  item: BudgetItem;
  effectivelyArchived: boolean;
  active: boolean;
  estimateCents: number;
  actualPaidCents: number;
  instalments: DerivedInstalment[];
  scheduledRemainingCents: number;
  unallocatedFutureCents: number;
  overdueCents: number;
  discrepancy: EstimateDiscrepancy;
}

export function estimateCents(estimate: Estimate): number {
  if (estimate.kind === "total") {
    const amountCents = estimate.amounts.baseCents;
    assertSafeCentAmount(amountCents, "Estimarea totală");
    return amountCents;
  }
  const amountCents = quantityRateCents(estimate);
  assertSafeCentAmount(amountCents, "Estimarea cantitate × tarif");
  return amountCents;
}

function assertSafeCentAmount(amountCents: number, label: string): void {
  if (!Number.isSafeInteger(amountCents) || amountCents < 0 || amountCents > MAX_MONEY_CENTS) {
    throw new RangeError(
      `${label} trebuie să fie între 0 și ${MAX_MONEY_CENTS} cenți întregi siguri.`,
    );
  }
}

function roundedRatio(value: number, multiplier: number, divisor: number): number {
  if (
    !Number.isSafeInteger(value) ||
    !Number.isSafeInteger(multiplier) ||
    !Number.isSafeInteger(divisor) ||
    value < 0 ||
    multiplier < 0 ||
    divisor <= 0
  ) {
    throw new RangeError("Raportul monetar necesită întregi siguri și un divizor pozitiv.");
  }
  const numerator = BigInt(value) * BigInt(multiplier);
  const denominator = BigInt(divisor);
  const result = Number((numerator + denominator / 2n) / denominator);
  if (!Number.isSafeInteger(result)) {
    throw new RangeError("Rezultatul monetar proporțional depășește limita de întreg sigur.");
  }
  return result;
}

export function allocateProportionally(targetCents: number, weights: readonly number[]): number[] {
  const weightTotal = sumCents(weights);
  if (targetCents === 0) return weights.map(() => 0);
  if (weightTotal === 0) {
    throw new RangeError("O sumă pozitivă nu poate fi repartizată peste ponderi zero.");
  }
  const shares = weights.map((weight, order) => {
    const numerator = BigInt(weight) * BigInt(targetCents);
    const denominator = BigInt(weightTotal);
    return {
      order,
      cents: Number(numerator / denominator),
      remainder: numerator % denominator,
    };
  });
  let centsLeft = targetCents - sumCents(shares.map((share) => share.cents));
  const ranked = [...shares].sort((left, right) =>
    left.remainder === right.remainder
      ? left.order - right.order
      : left.remainder > right.remainder
        ? -1
        : 1,
  );
  for (const share of ranked) {
    if (centsLeft === 0) break;
    share.cents += 1;
    centsLeft -= 1;
  }
  return shares.sort((left, right) => left.order - right.order).map((share) => share.cents);
}

function getArchivedGroupIds(groups: BudgetGroup[]): Set<string> {
  const byId = new Map(groups.map((group) => [group.id, group]));
  const archived = new Set<string>();
  const isArchived = (group: BudgetGroup): boolean => {
    if (archived.has(group.id)) return true;
    if (group.archived) {
      archived.add(group.id);
      return true;
    }
    const parent = group.parentId ? byId.get(group.parentId) : undefined;
    if (parent && isArchived(parent)) {
      archived.add(group.id);
      return true;
    }
    return false;
  };
  groups.forEach(isArchived);
  return archived;
}

interface LedgerContext {
  archivedGroupIds: Set<string>;
  instalmentsByItem: Map<string, Instalment[]>;
  paymentsByItem: Map<string, Payment[]>;
  paidByInstalment: Map<string, number>;
  asOfMonth: string;
}

function deriveInstalment(
  item: BudgetItem,
  instalment: Instalment,
  paidCents: number,
  active: boolean,
  asOfMonth: string,
): DerivedInstalment {
  // Owned purchases are settled: their instalments keep payment history but plan nothing.
  const remainingCents =
    item.ownership === "owned" ? 0 : Math.max(instalment.projectedCents - paidCents, 0);
  return {
    id: instalment.id,
    itemId: item.id,
    label: instalment.label,
    ...(instalment.dueOn === undefined ? {} : { dueOn: instalment.dueOn }),
    projectedCents: instalment.projectedCents,
    actualPaidCents: paidCents,
    remainingCents,
    overdue:
      active &&
      instalment.dueOn !== undefined &&
      instalment.dueOn < asOfMonth &&
      remainingCents > 0,
    active,
  };
}

function deriveItemLedger(item: BudgetItem, context: LedgerContext): ItemLedger {
  const payments = context.paymentsByItem.get(item.id) ?? [];
  const actualPaidCents = sumCents(payments.map((payment) => payment.amountCents));
  const effectivelyArchived = item.archived || context.archivedGroupIds.has(item.groupId);
  const active = item.included && !effectivelyArchived;
  const itemEstimateCents = estimateCents(item.estimate);
  const instalments = (context.instalmentsByItem.get(item.id) ?? []).map((instalment) =>
    deriveInstalment(
      item,
      instalment,
      context.paidByInstalment.get(instalment.id) ?? 0,
      active,
      context.asOfMonth,
    ),
  );
  if (item.ownership === "owned") {
    return {
      item,
      effectivelyArchived,
      active,
      estimateCents: itemEstimateCents,
      actualPaidCents,
      instalments,
      scheduledRemainingCents: 0,
      unallocatedFutureCents: 0,
      overdueCents: 0,
      discrepancy: { amountCents: 0, kind: "balanced" },
    };
  }

  const scheduledRemainingCents = sumCents(instalments.map((entry) => entry.remainingCents));
  const discrepancyAmount = itemEstimateCents - actualPaidCents - scheduledRemainingCents;
  const discrepancy: EstimateDiscrepancy = {
    amountCents: discrepancyAmount,
    kind:
      discrepancyAmount === 0
        ? "balanced"
        : discrepancyAmount > 0
          ? "unallocated"
          : "over-scheduled",
  };
  const unallocatedFutureCents = active ? Math.max(discrepancyAmount, 0) : 0;
  const overdueCents = active
    ? sumCents(instalments.filter((entry) => entry.overdue).map((entry) => entry.remainingCents))
    : 0;

  return {
    item,
    effectivelyArchived,
    active,
    estimateCents: itemEstimateCents,
    actualPaidCents,
    instalments,
    scheduledRemainingCents,
    unallocatedFutureCents,
    overdueCents,
    discrepancy,
  };
}

function makeBaseAllocations(
  document: BudgetDocument,
  ledgers: ItemLedger[],
): CashFlowAllocation[] {
  const allocations: CashFlowAllocation[] = document.payments.map((payment) => ({
    id: `actual-${payment.id}`,
    itemId: payment.itemId,
    instalmentId: payment.instalmentId,
    kind: "actual",
    date: payment.paidOn,
    amountCents: payment.amountCents,
  }));

  for (const ledger of ledgers) {
    if (!ledger.active) continue;
    for (const instalment of ledger.instalments) {
      if (instalment.remainingCents === 0) continue;
      allocations.push({
        id: `scheduled-${instalment.id}`,
        itemId: ledger.item.id,
        instalmentId: instalment.id,
        kind: "scheduled",
        ...(instalment.dueOn === undefined ? {} : { date: instalment.dueOn }),
        amountCents: instalment.remainingCents,
      });
    }
    if (ledger.unallocatedFutureCents > 0) {
      allocations.push({
        id: `unallocated-${ledger.item.id}`,
        itemId: ledger.item.id,
        kind: "unallocated",
        amountCents: ledger.unallocatedFutureCents,
      });
    }
  }
  return allocations;
}

function allocateContingency(
  ledgers: ItemLedger[],
  allocations: CashFlowAllocation[],
): CashFlowAllocation[] {
  const eligibleItems = new Set(
    ledgers
      .filter((ledger) => ledger.active && ledger.item.contingencyEligible)
      .map((ledger) => ledger.item.id),
  );
  const eligible = allocations.filter(
    (allocation) =>
      eligibleItems.has(allocation.itemId) &&
      (allocation.kind === "scheduled" || allocation.kind === "unallocated") &&
      allocation.amountCents > 0,
  );
  const eligibleTotal = sumCents(eligible.map((allocation) => allocation.amountCents));
  const target = roundedRatio(eligibleTotal, CONTINGENCY_BPS, BPS_DENOMINATOR);
  if (target === 0 || eligibleTotal === 0) return [];

  const shares = allocateProportionally(
    target,
    eligible.map((allocation) => allocation.amountCents),
  );
  return eligible
    .map((allocation, index) => ({ allocation, cents: shares[index] ?? 0 }))
    .filter(({ cents }) => cents > 0)
    .map(({ allocation, cents }) => ({
      id: `contingency-${allocation.id}`,
      itemId: allocation.itemId,
      ...(allocation.instalmentId === undefined ? {} : { instalmentId: allocation.instalmentId }),
      relatedAllocationId: allocation.id,
      kind: "contingency" as const,
      ...(allocation.date === undefined ? {} : { date: allocation.date }),
      amountCents: cents,
    }));
}

function buildDerivedItems(
  ledgers: ItemLedger[],
  allocations: CashFlowAllocation[],
): DerivedItem[] {
  const contingencyByItem = groupBy(
    allocations.filter((allocation) => allocation.kind === "contingency"),
    (allocation) => allocation.itemId,
  );
  return ledgers.map((ledger) => {
    const { start: scheduleStartOn, end: scheduleFinalOn } = dateSpan(
      ledger.instalments.map((instalment) => instalment.dueOn),
    );
    const contingencyCents = sumCents(
      (contingencyByItem.get(ledger.item.id) ?? []).map((allocation) => allocation.amountCents),
    );
    const activeFutureCents = ledger.active
      ? ledger.scheduledRemainingCents + ledger.unallocatedFutureCents
      : 0;
    const forecastBeforeContingencyCents = ledger.actualPaidCents + activeFutureCents;
    const settledCents =
      ledger.active && ledger.item.ownership === "owned"
        ? Math.max(ledger.estimateCents, ledger.actualPaidCents)
        : ledger.actualPaidCents;
    return {
      item: ledger.item,
      active: ledger.active,
      effectivelyArchived: ledger.effectivelyArchived,
      ...(scheduleStartOn === undefined ? {} : { scheduleStartOn }),
      ...(scheduleFinalOn === undefined ? {} : { scheduleFinalOn }),
      estimateCents: ledger.estimateCents,
      actualPaidCents: ledger.actualPaidCents,
      totalCents: sumCents([settledCents, activeFutureCents, contingencyCents]),
      settledCents,
      scheduledRemainingCents: ledger.active ? ledger.scheduledRemainingCents : 0,
      unallocatedFutureCents: ledger.unallocatedFutureCents,
      contingencyCents,
      forecastBeforeContingencyCents,
      forecastCents: forecastBeforeContingencyCents + contingencyCents,
      remainingForecastCents: activeFutureCents + contingencyCents,
      overdueCents: ledger.overdueCents,
      discrepancy: ledger.discrepancy,
      instalments: ledger.instalments,
    };
  });
}

function buildSummary(items: DerivedItem[]): BudgetSummary {
  const actualPaidCents = sumCents(items.map((entry) => entry.actualPaidCents));
  const totalCashForecastCents = sumCents(items.map((entry) => entry.forecastCents));
  return {
    actualPaidCents,
    totalCashForecastCents,
    remainingCashForecastCents: totalCashForecastCents - actualPaidCents,
  };
}

function byCatalogueOrder<T extends { sortOrder: number; label: string }>(
  left: T,
  right: T,
): number {
  return left.sortOrder - right.sortOrder || ROMANIAN_COLLATOR.compare(left.label, right.label);
}

function byHierarchyOrder(
  left: BudgetHierarchyGroup | BudgetHierarchyItem,
  right: BudgetHierarchyGroup | BudgetHierarchyItem,
): number {
  if (left.kind !== right.kind) return left.kind === "item" ? -1 : 1;
  const leftValue = left.kind === "item" ? left.derived : left;
  const rightValue = right.kind === "item" ? right.derived : right;
  return (
    rightValue.totalCents - leftValue.totalCents ||
    compareUndatedLast(leftValue.scheduleStartOn, rightValue.scheduleStartOn) ||
    byCatalogueOrder(left, right)
  );
}

function buildHierarchy(document: BudgetDocument, items: DerivedItem[]): BudgetHierarchyGroup[] {
  const itemsByGroup = groupBy(items, (item) => item.item.groupId);
  const groupsByParent = groupBy(document.groups, (group) => group.parentId);
  const build = (group: BudgetGroup): BudgetHierarchyGroup =>
    makeHierarchyGroup(
      {
        id: group.id,
        label: group.label,
        milestoneId: group.milestoneId,
        sortOrder: group.sortOrder,
        archived: group.archived,
      },
      [
        ...(groupsByParent.get(group.id) ?? []).map(build),
        ...(itemsByGroup.get(group.id) ?? []).map((derived): BudgetHierarchyItem => ({
          kind: "item",
          id: derived.item.id,
          label: derived.item.label,
          sortOrder: derived.item.sortOrder,
          derived,
        })),
      ],
    );
  return (groupsByParent.get(null) ?? []).sort(byCatalogueOrder).map(build);
}

type HierarchyGroupMetadata = Pick<
  BudgetHierarchyGroup,
  "id" | "label" | "milestoneId" | "sortOrder" | "archived"
> &
  Pick<Partial<BudgetHierarchyGroup>, "sourceGroupId">;

/** Current estimate for outstanding items, settled value otherwise. */
export function hierarchyEstimateCents(entry: DerivedItem): number {
  return entry.active && entry.totalCents > entry.settledCents
    ? entry.estimateCents
    : entry.settledCents;
}

/** Rolls totals up from direct children; child groups already carry their subtree totals. */
function makeHierarchyGroup(
  metadata: HierarchyGroupMetadata,
  children: Array<BudgetHierarchyGroup | BudgetHierarchyItem>,
): BudgetHierarchyGroup {
  const parts = children.map((child) =>
    child.kind === "group"
      ? child
      : { ...child.derived, estimateCents: hierarchyEstimateCents(child.derived) },
  );
  const { start: scheduleStartOn, end: scheduleFinalOn } = dateSpan(
    parts.flatMap((part) => [part.scheduleStartOn, part.scheduleFinalOn]),
  );
  return {
    kind: "group",
    ...metadata,
    ...(scheduleStartOn === undefined ? {} : { scheduleStartOn }),
    ...(scheduleFinalOn === undefined ? {} : { scheduleFinalOn }),
    estimateCents: sumCents(parts.map((part) => part.estimateCents)),
    totalCents: sumCents(parts.map((part) => part.totalCents)),
    settledCents: sumCents(parts.map((part) => part.settledCents)),
    children: children.sort(byHierarchyOrder),
  };
}

function areaNamespace(areaId: BudgetAreaId): string {
  return `area-${areaId.toLowerCase()}`;
}

function filterChildrenByArea(
  children: Array<BudgetHierarchyGroup | BudgetHierarchyItem>,
  areaId: BudgetAreaId,
): Array<BudgetHierarchyGroup | BudgetHierarchyItem> {
  return children.flatMap<BudgetHierarchyGroup | BudgetHierarchyItem>((child) => {
    if (child.kind === "item") return itemAreaId(child.derived.item) === areaId ? [child] : [];
    const filtered = filterHierarchyGroupByArea(child, areaId);
    return filtered ? [filtered] : [];
  });
}

function filterHierarchyGroupByArea(
  group: BudgetHierarchyGroup,
  areaId: BudgetAreaId,
): BudgetHierarchyGroup | undefined {
  const children = filterChildrenByArea(group.children, areaId);
  if (children.length === 0) return undefined;
  const sourceGroupId = group.sourceGroupId ?? group.id;
  return makeHierarchyGroup(
    {
      id: `${areaNamespace(areaId)}--${sourceGroupId}`,
      sourceGroupId,
      label: group.label,
      milestoneId: group.milestoneId,
      sortOrder: group.sortOrder,
      archived: group.archived,
    },
    children,
  );
}

/** Derives the room/area presentation from one existing stage hierarchy root. */
export function getBudgetAreaHierarchy(root: BudgetHierarchyGroup): BudgetHierarchyGroup[] {
  return BUDGET_AREAS.flatMap((area, sortOrder) => {
    const children = filterChildrenByArea(root.children, area.id);
    if (children.length === 0) return [];
    return [
      makeHierarchyGroup(
        {
          id: areaNamespace(area.id),
          label: area.label,
          milestoneId: root.milestoneId,
          sortOrder,
          archived: root.archived,
        },
        children,
      ),
    ];
  });
}

export function emptyCashFlowBucket(periodKey: string): CashFlowBucket {
  return {
    periodKey,
    actualCents: 0,
    scheduledCents: 0,
    unallocatedCents: 0,
    plannedCents: 0,
    contingencyCents: 0,
    totalCents: 0,
    allocations: [],
  };
}

export function addToCashFlowBucket(bucket: CashFlowBucket, allocation: CashFlowAllocation): void {
  bucket.allocations.push(allocation);
  bucket.totalCents += allocation.amountCents;
  if (allocation.kind === "actual") bucket.actualCents += allocation.amountCents;
  if (allocation.kind === "scheduled") bucket.scheduledCents += allocation.amountCents;
  if (allocation.kind === "unallocated") bucket.unallocatedCents += allocation.amountCents;
  if (allocation.kind === "scheduled" || allocation.kind === "unallocated") {
    bucket.plannedCents += allocation.amountCents;
  }
  if (allocation.kind === "contingency") bucket.contingencyCents += allocation.amountCents;
}

export function buildMonthlyCashFlow(allocations: readonly CashFlowAllocation[]): MonthlyCashFlow {
  const byMonth = new Map<string, CashFlowBucket>();
  const undated = emptyCashFlowBucket("undated");
  for (const allocation of allocations) {
    let bucket = undated;
    if (allocation.date) {
      const month = monthKey(allocation.date);
      bucket = byMonth.get(month) ?? emptyCashFlowBucket(month);
      byMonth.set(month, bucket);
    }
    addToCashFlowBucket(bucket, allocation);
  }
  return {
    months: [...byMonth.values()].sort((left, right) =>
      left.periodKey.localeCompare(right.periodKey),
    ),
    undated,
  };
}

/** Adds the running cash total through each bucket, in one pass. */
export function withCumulativeCents<T extends { totalCents: number }>(
  buckets: readonly T[],
): Array<T & { cumulativeCents: number }> {
  let cumulativeCents = 0;
  return buckets.map((bucket) => {
    cumulativeCents += bucket.totalCents;
    return { ...bucket, cumulativeCents };
  });
}

function buildTimeline(document: BudgetDocument, items: DerivedItem[]): BudgetTimelineEntry[] {
  const itemsByMilestone = groupBy(items, (entry) => entry.item.milestoneId);
  return document.milestones
    .map((milestone) => {
      const stageItems = itemsByMilestone.get(milestone.id) ?? [];
      const activeItems = stageItems.filter((entry) => entry.active);
      return {
        milestone,
        forecastCents: sumCents(stageItems.map((entry) => entry.forecastCents)),
        itemCount: activeItems.length,
        completeItemCount: activeItems.filter((entry) => entry.item.completion.complete).length,
      };
    })
    .sort((left, right) => left.milestone.date.localeCompare(right.milestone.date));
}

function buildUpcomingPayments(
  items: DerivedItem[],
  allocations: CashFlowAllocation[],
  asOfMonth: string,
): UpcomingPayment[] {
  const byItem = new Map(items.map((entry) => [entry.item.id, entry]));
  const contingencyByAllocation = new Map<string, number>();
  for (const allocation of allocations) {
    if (allocation.kind === "contingency" && allocation.relatedAllocationId) {
      contingencyByAllocation.set(allocation.relatedAllocationId, allocation.amountCents);
    }
  }
  return allocations
    .filter((allocation) => allocation.kind === "scheduled" || allocation.kind === "unallocated")
    .map((allocation) => {
      const derived = byItem.get(allocation.itemId);
      if (!derived) throw new Error(`Element derivat lipsă: ${allocation.itemId}`);
      const instalment = allocation.instalmentId
        ? derived.instalments.find((entry) => entry.id === allocation.instalmentId)
        : undefined;
      return {
        allocationId: allocation.id,
        itemId: allocation.itemId,
        itemLabel: derived.item.label,
        ...(allocation.instalmentId === undefined ? {} : { instalmentId: allocation.instalmentId }),
        label: instalment?.label ?? "Sumă nealocată",
        ...(allocation.date === undefined ? {} : { dueOn: allocation.date }),
        amountCents: allocation.amountCents,
        contingencyCents: contingencyByAllocation.get(allocation.id) ?? 0,
        overdue: allocation.date !== undefined && allocation.date < asOfMonth,
        unallocated: allocation.kind === "unallocated",
      };
    })
    .sort((left, right) => {
      if (left.dueOn === undefined) return right.dueOn === undefined ? 0 : 1;
      if (right.dueOn === undefined) return -1;
      return (
        left.dueOn.localeCompare(right.dueOn) || ROMANIAN_COLLATOR.compare(left.label, right.label)
      );
    });
}

export function selectBudgetView(source: BudgetDocument, options: BudgetViewOptions): BudgetView {
  let document = source;
  const scope = options.scope ?? "initial";
  if (scope !== "all") {
    const includesMilestone = (id: Milestone["id"]): boolean =>
      (id === EXTRA_MILESTONE_ID) === (scope === "extra");
    const items = document.items.filter((item) => includesMilestone(item.milestoneId));
    const itemIds = new Set(items.map((item) => item.id));
    document = {
      ...document,
      items,
      groups: document.groups.filter((group) => includesMilestone(group.milestoneId)),
      milestones: document.milestones.filter((milestone) => includesMilestone(milestone.id)),
      instalments: document.instalments.filter((entry) => itemIds.has(entry.itemId)),
      payments: document.payments.filter((entry) => itemIds.has(entry.itemId)),
    };
  }
  const asOfMonth = monthKey(options.asOf);
  const context: LedgerContext = {
    archivedGroupIds: getArchivedGroupIds(document.groups),
    instalmentsByItem: groupBy(document.instalments, (entry) => entry.itemId),
    paymentsByItem: groupBy(document.payments, (payment) => payment.itemId),
    paidByInstalment: new Map(
      [...groupBy(document.payments, (payment) => payment.instalmentId)].map(
        ([instalmentId, payments]) => [
          instalmentId,
          sumCents(payments.map((payment) => payment.amountCents)),
        ],
      ),
    ),
    asOfMonth,
  };
  const ledgers = document.items.map((item) => deriveItemLedger(item, context));
  const baseAllocations = makeBaseAllocations(document, ledgers);
  // Separate budgets retain the same cent rounding when displayed together.
  const contingencyAllocations = [false, true].flatMap((extra) =>
    allocateContingency(
      ledgers.filter((ledger) => (ledger.item.milestoneId === EXTRA_MILESTONE_ID) === extra),
      baseAllocations,
    ),
  );
  const allocations = [...baseAllocations, ...contingencyAllocations];
  const items = buildDerivedItems(ledgers, allocations);
  return {
    summary: buildSummary(items),
    items,
    hierarchy: buildHierarchy(document, items),
    timeline: buildTimeline(document, items),
    upcomingPayments: buildUpcomingPayments(items, allocations, asOfMonth),
    allocations,
  };
}
