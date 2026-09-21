import type { CashFlowAllocation, CashFlowBucket } from "../../domain/selectors.js";
import { formatMonth } from "../../ui/format.js";

export type PeriodGranularity = "month" | "quarter";

export interface PlanningPeriod {
  key: string;
  label: string;
  startMonth: string;
  endMonth: string;
}

export interface PlanningFlow extends CashFlowBucket {
  label: string;
}

function monthDate(month: string): Date {
  return new Date(`${month}-01T00:00:00Z`);
}

export function addMonths(month: string, count: number): string {
  const date = monthDate(month);
  date.setUTCMonth(date.getUTCMonth() + count);
  return date.toISOString().slice(0, 7);
}

export function quarterKey(month: string): string {
  const [year, monthNumber] = month.split("-").map(Number);
  if (year === undefined || monthNumber === undefined) return month;
  return `${year}-T${Math.ceil(monthNumber / 3)}`;
}

export function makePlanningPeriods(
  startMonth: string,
  endMonth: string,
  granularity: PeriodGranularity,
): PlanningPeriod[] {
  const periods: PlanningPeriod[] = [];
  const firstMonth =
    granularity === "quarter"
      ? `${startMonth.slice(0, 4)}-${String(Math.floor((Number(startMonth.slice(5, 7)) - 1) / 3) * 3 + 1).padStart(2, "0")}`
      : startMonth;
  const finalMonth =
    granularity === "quarter"
      ? `${endMonth.slice(0, 4)}-${String(Math.floor((Number(endMonth.slice(5, 7)) - 1) / 3) * 3 + 1).padStart(2, "0")}`
      : endMonth;

  for (
    let cursor = firstMonth;
    cursor <= finalMonth;
    cursor = addMonths(cursor, granularity === "month" ? 1 : 3)
  ) {
    if (granularity === "month") {
      periods.push({
        key: cursor,
        label: formatMonth(cursor),
        startMonth: cursor,
        endMonth: cursor,
      });
      continue;
    }
    const monthIndex = Number(cursor.slice(5, 7)) - 1;
    periods.push({
      key: quarterKey(cursor),
      label: `T${Math.floor(monthIndex / 3) + 1} ${cursor.slice(0, 4)}`,
      startMonth: cursor,
      endMonth: addMonths(cursor, 2),
    });
  }
  return periods;
}

export function planningMonthRange(dates: readonly string[]): {
  startMonth: string;
  endMonth: string;
} {
  if (dates.length === 0) {
    return { startMonth: "2026-11", endMonth: "2029-06" };
  }
  const months = dates.map((date) => date.slice(0, 7));
  return {
    startMonth: [...months].sort()[0] ?? "2026-11",
    endMonth: [...months].sort().at(-1) ?? "2029-06",
  };
}

function emptyFlow(period: PlanningPeriod): PlanningFlow {
  return {
    month: period.key,
    label: period.label,
    actualCents: 0,
    scheduledCents: 0,
    unallocatedCents: 0,
    contingencyCents: 0,
    totalCents: 0,
    allocations: [],
  };
}

export function aggregatePlanningFlows(
  allocations: readonly CashFlowAllocation[],
  periods: readonly PlanningPeriod[],
  allowedItemIds?: ReadonlySet<string>,
): { flows: PlanningFlow[]; undated: PlanningFlow } {
  const byKey = new Map(periods.map((period) => [period.key, emptyFlow(period)]));
  const undated: PlanningFlow = {
    ...emptyFlow({ key: "fără-termen", label: "Fără termen", startMonth: "", endMonth: "" }),
    month: "undated",
  };

  for (const allocation of allocations) {
    if (allowedItemIds && !allowedItemIds.has(allocation.itemId)) continue;
    const month = allocation.date?.slice(0, 7);
    const key = month ? (periods[0]?.key.includes("-T") ? quarterKey(month) : month) : undefined;
    const flow = key ? byKey.get(key) : undated;
    if (!flow) continue;
    flow.allocations.push(allocation);
    flow.totalCents += allocation.amountCents;
    if (allocation.kind === "actual") flow.actualCents += allocation.amountCents;
    if (allocation.kind === "scheduled") flow.scheduledCents += allocation.amountCents;
    if (allocation.kind === "unallocated") flow.unallocatedCents += allocation.amountCents;
    if (allocation.kind === "contingency") flow.contingencyCents += allocation.amountCents;
  }
  return { flows: periods.map((period) => byKey.get(period.key) ?? emptyFlow(period)), undated };
}

export function flowTotalForItems(
  buckets: readonly CashFlowBucket[],
  itemIds: ReadonlySet<string>,
): number {
  return buckets.reduce(
    (sum, bucket) =>
      sum +
      bucket.allocations
        .filter((allocation) => itemIds.has(allocation.itemId))
        .reduce((allocationSum, allocation) => allocationSum + allocation.amountCents, 0),
    0,
  );
}
