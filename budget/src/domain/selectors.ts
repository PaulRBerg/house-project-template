import { BUDGET_AREAS, FALLBACK_BUDGET_AREA_ID, type BudgetAreaId } from "./areas.js";
import { daysBetween, monthKey } from "./dates.js";
import {
  MAX_ANNUAL_GROWTH_BPS,
  MAX_GROWTH_DAYS,
  MAX_MONEY_CENTS,
  type BudgetDocument,
  type BudgetGroup,
  type BudgetItem,
  type Estimate,
  type Milestone,
  type Scenario,
} from "./schema.js";

export interface SelectOptions {
  scenario: Scenario;
  /** Calendar date in the user's locale, as YYYY-MM-DD. */
  asOf: string;
}

export type BudgetWarningCode =
  | "estimate-under-scheduled"
  | "estimate-unallocated"
  | "instalment-overpaid"
  | "instalment-overdue";

export interface DerivedInstalment {
  id: string;
  itemId: string;
  label: string;
  dueOn?: string;
  /** Stored base-scenario plan before scenario scaling. */
  projectedCents: number;
  /** Plan for the selected scenario, before subtracting actual payments. */
  scenarioProjectedCents: number;
  actualPaidCents: number;
  remainingRawCents: number;
  remainingForecastCents: number;
  overspendCents: number;
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
  /** Fixed, owned, and land costs retain their base estimate in every view. */
  estimateScenario: Scenario;
  actualPaidCents: number;
  /** Table value includes active owned purchases at their historical price, counted once. */
  totalCents: number;
  /** Recorded payments plus historical owned value absent from the payment ledger. */
  settledCents: number;
  scheduledRemainingRawCents: number;
  scheduledRemainingForecastCents: number;
  unallocatedFutureCents: number;
  excludedFutureCents: number;
  contingencyCents: number;
  forecastBeforeContingencyCents: number;
  forecastCents: number;
  overdueCents: number;
  discrepancy: EstimateDiscrepancy;
  warnings: BudgetWarningCode[];
  instalments: DerivedInstalment[];
}

export interface BudgetSummary {
  scenario: Scenario;
  actualPaidCents: number;
  scheduledFutureCents: number;
  unallocatedFutureCents: number;
  contingencyCents: number;
  coreBeforeContingencyCents: number;
  coreForecastCents: number;
  movableForecastCents: number;
  totalCashForecastCents: number;
  remainingCashForecastCents: number;
  optionalExcludedFutureCents: number;
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
  actualPaidCents: number;
  futureCents: number;
  contingencyCents: number;
  forecastCents: number;
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
  month: string;
  actualCents: number;
  scheduledCents: number;
  unallocatedCents: number;
  contingencyCents: number;
  totalCents: number;
  allocations: CashFlowAllocation[];
}

export interface MonthlyCashFlow {
  months: CashFlowBucket[];
  undated: CashFlowBucket;
}

export interface CumulativeCashPoint {
  month: string;
  monthCents: number;
  cumulativeCents: number;
}

export interface BudgetTimelineEntry {
  milestone: Milestone;
  actualPaidCents: number;
  futureCents: number;
  contingencyCents: number;
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
  monthlyCashFlow: MonthlyCashFlow;
  cumulativeCashFlow: CumulativeCashPoint[];
  timeline: BudgetTimelineEntry[];
  upcomingPayments: UpcomingPayment[];
  allocations: CashFlowAllocation[];
}

interface ItemWork {
  item: BudgetItem;
  effectiveArchived: boolean;
  active: boolean;
  estimateCents: number;
  estimateScenario: Scenario;
  actualPaidCents: number;
  instalments: DerivedInstalment[];
  scheduledRemainingRawCents: number;
  scheduledRemainingForecastCents: number;
  unallocatedFutureCents: number;
  excludedFutureCents: number;
  overdueCents: number;
  discrepancy: EstimateDiscrepancy;
  warnings: BudgetWarningCode[];
}

export function estimateCents(estimate: Estimate, scenario: Scenario): number {
  const key = `${scenario}Cents` as const;
  if (estimate.kind === "total") {
    const amountCents = estimate.amounts[key];
    assertSafeCentAmount(amountCents, "Estimarea totală");
    return amountCents;
  }
  const amountCents = Math.round(estimate.quantity * estimate.rates[key]);
  assertSafeCentAmount(amountCents, "Estimarea cantitate × tarif");
  return amountCents;
}

/** Compounds whole-cent estimates and never deflates when the payment date is earlier. */
export function growCents(
  amountCents: number,
  pricedOn: string,
  paymentOn: string | undefined,
  annualGrowthBps: number,
): number {
  if (!paymentOn || amountCents === 0) return amountCents;
  if (
    !Number.isInteger(annualGrowthBps) ||
    annualGrowthBps < 0 ||
    annualGrowthBps > MAX_ANNUAL_GROWTH_BPS
  ) {
    throw new RangeError(
      `Rata anuală trebuie să fie între 0 și ${MAX_ANNUAL_GROWTH_BPS} puncte de bază.`,
    );
  }
  const elapsedDays = Math.max(0, daysBetween(pricedOn, paymentOn));
  if (elapsedDays > MAX_GROWTH_DAYS) {
    throw new RangeError(`Intervalul de creștere nu poate depăși ${MAX_GROWTH_DAYS} zile.`);
  }
  const years = elapsedDays / 365.2425;
  const result = Math.round(amountCents * (1 + annualGrowthBps / 10_000) ** years);
  assertSafeCentAmount(result, "Estimarea după creștere");
  return result;
}

function sum(values: readonly number[]): number {
  return values.reduce((total, value) => {
    const result = total + value;
    if (!Number.isSafeInteger(result)) {
      throw new RangeError("Totalul monetar depășește limita sigură pentru cenți întregi.");
    }
    return result;
  }, 0);
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

function allocateProportionally(targetCents: number, weights: readonly number[]): number[] {
  const weightTotal = sum(weights);
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
  let centsLeft = targetCents - sum(shares.map((share) => share.cents));
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

function deriveOwnedItemWork(
  item: BudgetItem,
  itemInstalments: BudgetDocument["instalments"],
  payments: BudgetDocument["payments"],
  effectivelyArchived: boolean,
  active: boolean,
  historicalEstimateCents: number,
): ItemWork {
  const actualPaidCents = sum(payments.map((payment) => payment.amountCents));
  const instalments: DerivedInstalment[] = itemInstalments.map((instalment) => {
    const paidCents = sum(
      payments
        .filter((payment) => payment.instalmentId === instalment.id)
        .map((payment) => payment.amountCents),
    );
    return {
      id: instalment.id,
      itemId: item.id,
      label: instalment.label,
      ...(instalment.dueOn === undefined ? {} : { dueOn: instalment.dueOn }),
      projectedCents: instalment.projectedCents,
      scenarioProjectedCents: instalment.projectedCents,
      actualPaidCents: paidCents,
      remainingRawCents: 0,
      remainingForecastCents: 0,
      overspendCents: Math.max(paidCents - instalment.projectedCents, 0),
      overdue: false,
      active,
    };
  });
  return {
    item,
    effectiveArchived: effectivelyArchived,
    active,
    estimateCents: historicalEstimateCents,
    estimateScenario: "base",
    actualPaidCents,
    instalments,
    scheduledRemainingRawCents: 0,
    scheduledRemainingForecastCents: 0,
    unallocatedFutureCents: 0,
    excludedFutureCents: 0,
    overdueCents: 0,
    discrepancy: { amountCents: 0, kind: "balanced" },
    warnings: [],
  };
}

function deriveItemWork(
  document: BudgetDocument,
  item: BudgetItem,
  archivedGroupIds: Set<string>,
  options: SelectOptions,
): ItemWork {
  const itemInstalments = document.instalments.filter((entry) => entry.itemId === item.id);
  const payments = document.payments.filter((payment) => payment.itemId === item.id);
  const actualPaidCents = sum(payments.map((payment) => payment.amountCents));
  const effectivelyArchived = item.archived || archivedGroupIds.has(item.groupId);
  const active = item.included && !effectivelyArchived;
  const baseEstimateCents = estimateCents(item.estimate, "base");
  if (item.ownership === "owned") {
    return deriveOwnedItemWork(
      item,
      itemInstalments,
      payments,
      effectivelyArchived,
      active,
      baseEstimateCents,
    );
  }
  const shouldGrow = !item.estimate.fixed && item.costType !== "land";
  const estimateScenario = shouldGrow ? options.scenario : "base";
  const selectedEstimateCents = estimateCents(item.estimate, estimateScenario);
  const basePlanCents = sum(itemInstalments.map((instalment) => instalment.projectedCents));
  const selectedPlanCents =
    shouldGrow && baseEstimateCents > 0
      ? roundedRatio(basePlanCents, selectedEstimateCents, baseEstimateCents)
      : basePlanCents;
  const scenarioPlans =
    shouldGrow && baseEstimateCents > 0
      ? allocateProportionally(
          selectedPlanCents,
          itemInstalments.map((instalment) => instalment.projectedCents),
        )
      : itemInstalments.map((instalment) => instalment.projectedCents);

  const instalments: DerivedInstalment[] = itemInstalments.map((instalment, index) => {
    const instalmentPayments = payments.filter((payment) => payment.instalmentId === instalment.id);
    const paidCents = sum(instalmentPayments.map((payment) => payment.amountCents));
    const scenarioProjectedCents = scenarioPlans[index] ?? 0;
    const remainingRawCents = Math.max(scenarioProjectedCents - paidCents, 0);
    const remainingForecastCents = shouldGrow
      ? growCents(
          remainingRawCents,
          item.estimate.pricedOn,
          instalment.dueOn,
          document.project.annualGrowthBps,
        )
      : remainingRawCents;
    return {
      id: instalment.id,
      itemId: item.id,
      label: instalment.label,
      ...(instalment.dueOn === undefined ? {} : { dueOn: instalment.dueOn }),
      projectedCents: instalment.projectedCents,
      scenarioProjectedCents,
      actualPaidCents: paidCents,
      remainingRawCents,
      remainingForecastCents,
      overspendCents: Math.max(paidCents - scenarioProjectedCents, 0),
      overdue:
        active &&
        instalment.dueOn !== undefined &&
        instalment.dueOn < monthKey(options.asOf) &&
        remainingRawCents > 0,
      active,
    };
  });

  const scheduledRemainingRawCents = sum(instalments.map((entry) => entry.remainingRawCents));
  const scheduledRemainingForecastCents = sum(
    instalments.map((entry) => entry.remainingForecastCents),
  );
  const discrepancyAmount = selectedEstimateCents - actualPaidCents - scheduledRemainingRawCents;
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
  const excludedFutureCents =
    !item.included && !effectivelyArchived
      ? scheduledRemainingForecastCents + Math.max(discrepancyAmount, 0)
      : 0;
  const overdueCents = active
    ? sum(instalments.filter((entry) => entry.overdue).map((entry) => entry.remainingForecastCents))
    : 0;
  const warnings: BudgetWarningCode[] = [];
  if (discrepancy.kind === "unallocated") warnings.push("estimate-unallocated");
  if (discrepancy.kind === "over-scheduled") warnings.push("estimate-under-scheduled");
  if (instalments.some((entry) => entry.overspendCents > 0)) warnings.push("instalment-overpaid");
  if (instalments.some((entry) => entry.overdue)) warnings.push("instalment-overdue");

  return {
    item,
    effectiveArchived: effectivelyArchived,
    active,
    estimateCents: selectedEstimateCents,
    estimateScenario,
    actualPaidCents,
    instalments,
    scheduledRemainingRawCents,
    scheduledRemainingForecastCents,
    unallocatedFutureCents,
    excludedFutureCents,
    overdueCents,
    discrepancy,
    warnings,
  };
}

function makeBaseAllocations(document: BudgetDocument, work: ItemWork[]): CashFlowAllocation[] {
  const allocations: CashFlowAllocation[] = document.payments.map((payment) => ({
    id: `actual-${payment.id}`,
    itemId: payment.itemId,
    instalmentId: payment.instalmentId,
    kind: "actual",
    date: payment.paidOn,
    amountCents: payment.amountCents,
  }));

  for (const entry of work) {
    if (!entry.active) continue;
    for (const instalment of entry.instalments) {
      if (instalment.remainingForecastCents === 0) continue;
      allocations.push({
        id: `scheduled-${instalment.id}`,
        itemId: entry.item.id,
        instalmentId: instalment.id,
        kind: "scheduled",
        ...(instalment.dueOn === undefined ? {} : { date: instalment.dueOn }),
        amountCents: instalment.remainingForecastCents,
      });
    }
    if (entry.unallocatedFutureCents > 0) {
      allocations.push({
        id: `unallocated-${entry.item.id}`,
        itemId: entry.item.id,
        kind: "unallocated",
        amountCents: entry.unallocatedFutureCents,
      });
    }
  }
  return allocations;
}

function allocateContingency(
  document: BudgetDocument,
  work: ItemWork[],
  allocations: CashFlowAllocation[],
): CashFlowAllocation[] {
  const eligibleItems = new Set(
    work
      .filter((entry) => entry.active && entry.item.contingencyEligible)
      .map((entry) => entry.item.id),
  );
  const eligible = allocations.filter(
    (allocation) =>
      eligibleItems.has(allocation.itemId) &&
      (allocation.kind === "scheduled" || allocation.kind === "unallocated") &&
      allocation.amountCents > 0,
  );
  const eligibleTotal = sum(eligible.map((allocation) => allocation.amountCents));
  const target = roundedRatio(eligibleTotal, document.project.contingencyBps, 10_000);
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

function buildDerivedItems(work: ItemWork[], allocations: CashFlowAllocation[]): DerivedItem[] {
  return work.map((entry) => {
    const scheduleDates = entry.instalments
      .flatMap((instalment) => (instalment.dueOn ? [instalment.dueOn] : []))
      .sort();
    const scheduleStartOn = scheduleDates[0];
    const scheduleFinalOn = scheduleDates.at(-1);
    const contingencyCents = sum(
      allocations
        .filter(
          (allocation) => allocation.itemId === entry.item.id && allocation.kind === "contingency",
        )
        .map((allocation) => allocation.amountCents),
    );
    const activeFutureCents = entry.active
      ? entry.scheduledRemainingForecastCents + entry.unallocatedFutureCents
      : 0;
    const forecastBeforeContingencyCents = entry.actualPaidCents + activeFutureCents;
    const settledCents =
      entry.active && entry.item.ownership === "owned"
        ? Math.max(entry.estimateCents, entry.actualPaidCents)
        : entry.actualPaidCents;
    return {
      item: entry.item,
      active: entry.active,
      effectivelyArchived: entry.effectiveArchived,
      ...(scheduleStartOn === undefined ? {} : { scheduleStartOn }),
      ...(scheduleFinalOn === undefined ? {} : { scheduleFinalOn }),
      estimateCents: entry.estimateCents,
      estimateScenario: entry.estimateScenario,
      actualPaidCents: entry.actualPaidCents,
      totalCents: sum([settledCents, activeFutureCents, contingencyCents]),
      settledCents,
      scheduledRemainingRawCents: entry.scheduledRemainingRawCents,
      scheduledRemainingForecastCents: entry.active ? entry.scheduledRemainingForecastCents : 0,
      unallocatedFutureCents: entry.unallocatedFutureCents,
      excludedFutureCents: entry.excludedFutureCents,
      contingencyCents,
      forecastBeforeContingencyCents,
      forecastCents: forecastBeforeContingencyCents + contingencyCents,
      overdueCents: entry.overdueCents,
      discrepancy: entry.discrepancy,
      warnings: entry.warnings,
      instalments: entry.instalments,
    };
  });
}

function buildSummary(items: DerivedItem[], scenario: Scenario): BudgetSummary {
  const coreItems = items.filter((entry) => entry.item.costScope === "core");
  const movableItems = items.filter((entry) => entry.item.costScope === "movable");
  const coreBeforeContingencyCents = sum(
    coreItems.map((entry) => entry.forecastBeforeContingencyCents),
  );
  const contingencyCents = sum(coreItems.map((entry) => entry.contingencyCents));
  const coreForecastCents = coreBeforeContingencyCents + contingencyCents;
  const movableForecastCents = sum(movableItems.map((entry) => entry.forecastCents));
  const actualPaidCents = sum(items.map((entry) => entry.actualPaidCents));
  const totalCashForecastCents = coreForecastCents + movableForecastCents;
  return {
    scenario,
    actualPaidCents,
    scheduledFutureCents: sum(items.map((entry) => entry.scheduledRemainingForecastCents)),
    unallocatedFutureCents: sum(items.map((entry) => entry.unallocatedFutureCents)),
    contingencyCents,
    coreBeforeContingencyCents,
    coreForecastCents,
    movableForecastCents,
    totalCashForecastCents,
    remainingCashForecastCents: totalCashForecastCents - actualPaidCents,
    optionalExcludedFutureCents: sum(items.map((entry) => entry.excludedFutureCents)),
  };
}

function byCatalogueOrder<T extends { sortOrder: number; label: string }>(
  left: T,
  right: T,
): number {
  return left.sortOrder - right.sortOrder || left.label.localeCompare(right.label, "ro");
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
    (leftValue.scheduleStartOn ?? "9999-12-31").localeCompare(
      rightValue.scheduleStartOn ?? "9999-12-31",
    ) ||
    byCatalogueOrder(left, right)
  );
}

function buildHierarchy(document: BudgetDocument, items: DerivedItem[]): BudgetHierarchyGroup[] {
  const itemsByGroup = new Map<string, DerivedItem[]>();
  items.forEach((item) => {
    const siblings = itemsByGroup.get(item.item.groupId) ?? [];
    siblings.push(item);
    itemsByGroup.set(item.item.groupId, siblings);
  });
  const groupsByParent = new Map<string | null, BudgetGroup[]>();
  document.groups.forEach((group) => {
    const siblings = groupsByParent.get(group.parentId) ?? [];
    siblings.push(group);
    groupsByParent.set(group.parentId, siblings);
  });
  const build = (group: BudgetGroup): BudgetHierarchyGroup => {
    const childGroups = (groupsByParent.get(group.id) ?? []).map(build);
    const childItems: BudgetHierarchyItem[] = (itemsByGroup.get(group.id) ?? []).map((derived) => ({
      kind: "item",
      id: derived.item.id,
      label: derived.item.label,
      sortOrder: derived.item.sortOrder,
      derived,
    }));
    const children: Array<BudgetHierarchyGroup | BudgetHierarchyItem> = [
      ...childGroups,
      ...childItems,
    ].sort(byHierarchyOrder);
    return makeHierarchyGroup(
      {
        id: group.id,
        label: group.label,
        milestoneId: group.milestoneId,
        sortOrder: group.sortOrder,
        archived: group.archived,
      },
      children,
    );
  };
  return (groupsByParent.get(null) ?? []).sort(byCatalogueOrder).map(build);
}

type HierarchyGroupMetadata = Pick<
  BudgetHierarchyGroup,
  "id" | "label" | "milestoneId" | "sortOrder" | "archived"
> &
  Pick<Partial<BudgetHierarchyGroup>, "sourceGroupId">;

function makeHierarchyGroup(
  metadata: HierarchyGroupMetadata,
  children: Array<BudgetHierarchyGroup | BudgetHierarchyItem>,
): BudgetHierarchyGroup {
  const descendantItems = flattenHierarchyItems(children);
  const scheduleDates = descendantItems
    .flatMap((entry) =>
      [entry.scheduleStartOn, entry.scheduleFinalOn].filter(
        (date): date is string => date !== undefined,
      ),
    )
    .sort();
  const scheduleStartOn = scheduleDates[0];
  const scheduleFinalOn = scheduleDates.at(-1);
  const actualPaidCents = sum(descendantItems.map((entry) => entry.actualPaidCents));
  const contingencyCents = sum(descendantItems.map((entry) => entry.contingencyCents));
  const forecastCents = sum(descendantItems.map((entry) => entry.forecastCents));
  return {
    kind: "group",
    ...metadata,
    ...(scheduleStartOn === undefined ? {} : { scheduleStartOn }),
    ...(scheduleFinalOn === undefined ? {} : { scheduleFinalOn }),
    actualPaidCents,
    futureCents: forecastCents - actualPaidCents - contingencyCents,
    contingencyCents,
    forecastCents,
    estimateCents: sum(
      descendantItems.map((entry) =>
        entry.active && entry.totalCents > entry.settledCents
          ? entry.estimateCents
          : entry.settledCents,
      ),
    ),
    totalCents: sum(descendantItems.map((entry) => entry.totalCents)),
    settledCents: sum(descendantItems.map((entry) => entry.settledCents)),
    children: children.sort(byHierarchyOrder),
  };
}

function areaNamespace(areaId: BudgetAreaId): string {
  return `area-${areaId.toLowerCase()}`;
}

function filterHierarchyGroupByArea(
  group: BudgetHierarchyGroup,
  areaId: BudgetAreaId,
): BudgetHierarchyGroup | undefined {
  const children = group.children.flatMap<BudgetHierarchyGroup | BudgetHierarchyItem>((child) => {
    if (child.kind === "item") {
      return (child.derived.item.areaId ?? FALLBACK_BUDGET_AREA_ID) === areaId ? [child] : [];
    }
    const filtered = filterHierarchyGroupByArea(child, areaId);
    return filtered ? [filtered] : [];
  });
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

function flattenHierarchyItems(
  children: Array<BudgetHierarchyGroup | BudgetHierarchyItem>,
): DerivedItem[] {
  return children.flatMap((child) =>
    child.kind === "item" ? [child.derived] : flattenHierarchyItems(child.children),
  );
}

/** Derives the room/area presentation from one existing stage hierarchy root. */
export function getBudgetAreaHierarchy(root: BudgetHierarchyGroup): BudgetHierarchyGroup[] {
  return BUDGET_AREAS.flatMap((area, sortOrder) => {
    const children = root.children.flatMap<BudgetHierarchyGroup | BudgetHierarchyItem>((child) => {
      if (child.kind === "item") {
        return (child.derived.item.areaId ?? FALLBACK_BUDGET_AREA_ID) === area.id ? [child] : [];
      }
      const filtered = filterHierarchyGroupByArea(child, area.id);
      return filtered ? [filtered] : [];
    });
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
        children.sort(byHierarchyOrder),
      ),
    ];
  });
}

function emptyBucket(month: string): CashFlowBucket {
  return {
    month,
    actualCents: 0,
    scheduledCents: 0,
    unallocatedCents: 0,
    contingencyCents: 0,
    totalCents: 0,
    allocations: [],
  };
}

function buildMonthlyCashFlow(allocations: CashFlowAllocation[]): MonthlyCashFlow {
  const byMonth = new Map<string, CashFlowBucket>();
  const undated = emptyBucket("undated");
  for (const allocation of allocations) {
    const bucket = allocation.date
      ? (byMonth.get(monthKey(allocation.date)) ?? emptyBucket(monthKey(allocation.date)))
      : undated;
    bucket.allocations.push(allocation);
    bucket.totalCents += allocation.amountCents;
    if (allocation.kind === "actual") bucket.actualCents += allocation.amountCents;
    if (allocation.kind === "scheduled") bucket.scheduledCents += allocation.amountCents;
    if (allocation.kind === "unallocated") bucket.unallocatedCents += allocation.amountCents;
    if (allocation.kind === "contingency") bucket.contingencyCents += allocation.amountCents;
    if (allocation.date) byMonth.set(bucket.month, bucket);
  }
  return {
    months: [...byMonth.values()].sort((left, right) => left.month.localeCompare(right.month)),
    undated,
  };
}

function buildCumulativeCashFlow(monthly: MonthlyCashFlow): CumulativeCashPoint[] {
  let cumulativeCents = 0;
  return monthly.months.map((bucket) => {
    cumulativeCents += bucket.totalCents;
    return { month: bucket.month, monthCents: bucket.totalCents, cumulativeCents };
  });
}

function buildTimeline(document: BudgetDocument, items: DerivedItem[]): BudgetTimelineEntry[] {
  return document.milestones
    .map((milestone) => {
      const stageItems = items.filter((entry) => entry.item.milestoneId === milestone.id);
      const activeItems = stageItems.filter((entry) => entry.active);
      const actualPaidCents = sum(stageItems.map((entry) => entry.actualPaidCents));
      const contingencyCents = sum(stageItems.map((entry) => entry.contingencyCents));
      const forecastCents = sum(stageItems.map((entry) => entry.forecastCents));
      return {
        milestone,
        actualPaidCents,
        futureCents: forecastCents - actualPaidCents - contingencyCents,
        contingencyCents,
        forecastCents,
        itemCount: activeItems.length,
        completeItemCount: activeItems.filter((entry) => entry.item.completion.complete).length,
      };
    })
    .sort((left, right) => left.milestone.date.localeCompare(right.milestone.date));
}

function buildUpcomingPayments(
  items: DerivedItem[],
  allocations: CashFlowAllocation[],
  asOf: string,
): UpcomingPayment[] {
  const byItem = new Map(items.map((entry) => [entry.item.id, entry]));
  const contingencyByAllocation = new Map<string, number>();
  allocations
    .filter((allocation) => allocation.kind === "contingency")
    .forEach((allocation) => {
      if (allocation.relatedAllocationId) {
        contingencyByAllocation.set(allocation.relatedAllocationId, allocation.amountCents);
      }
    });
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
        overdue: allocation.date !== undefined && allocation.date < monthKey(asOf),
        unallocated: allocation.kind === "unallocated",
      };
    })
    .sort((left, right) => {
      if (left.dueOn === undefined) return right.dueOn === undefined ? 0 : 1;
      if (right.dueOn === undefined) return -1;
      return left.dueOn.localeCompare(right.dueOn) || left.label.localeCompare(right.label, "ro");
    });
}

export function selectBudgetView(document: BudgetDocument, options: SelectOptions): BudgetView {
  const archivedGroupIds = getArchivedGroupIds(document.groups);
  const work = document.items.map((item) =>
    deriveItemWork(document, item, archivedGroupIds, options),
  );
  const baseAllocations = makeBaseAllocations(document, work);
  const contingencyAllocations = allocateContingency(document, work, baseAllocations);
  const allocations = [...baseAllocations, ...contingencyAllocations];
  const items = buildDerivedItems(work, allocations);
  const monthlyCashFlow = buildMonthlyCashFlow(allocations);
  return {
    summary: buildSummary(items, options.scenario),
    items,
    hierarchy: buildHierarchy(document, items),
    monthlyCashFlow,
    cumulativeCashFlow: buildCumulativeCashFlow(monthlyCashFlow),
    timeline: buildTimeline(document, items),
    upcomingPayments: buildUpcomingPayments(items, allocations, options.asOf),
    allocations,
  };
}

export function getBudgetSummary(document: BudgetDocument, options: SelectOptions): BudgetSummary {
  return selectBudgetView(document, options).summary;
}

export function getBudgetHierarchy(
  document: BudgetDocument,
  options: SelectOptions,
): BudgetHierarchyGroup[] {
  return selectBudgetView(document, options).hierarchy;
}

export function getMonthlyCashFlow(
  document: BudgetDocument,
  options: SelectOptions,
): MonthlyCashFlow {
  return selectBudgetView(document, options).monthlyCashFlow;
}

export function getCumulativeCashFlow(
  document: BudgetDocument,
  options: SelectOptions,
): CumulativeCashPoint[] {
  return selectBudgetView(document, options).cumulativeCashFlow;
}

export function getBudgetTimeline(
  document: BudgetDocument,
  options: SelectOptions,
): BudgetTimelineEntry[] {
  return selectBudgetView(document, options).timeline;
}

export function getUpcomingPayments(
  document: BudgetDocument,
  options: SelectOptions,
  limit?: number,
): UpcomingPayment[] {
  const payments = selectBudgetView(document, options).upcomingPayments;
  return limit === undefined ? payments : payments.slice(0, Math.max(0, limit));
}
