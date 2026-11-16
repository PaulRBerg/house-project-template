import { dateSpan, monthKey } from "../../domain/dates.js";
import { FIXED_MILESTONES } from "../../domain/schema.js";
import {
  addToCashFlowBucket,
  emptyCashFlowBucket,
  withCumulativeCents,
  type CashFlowAllocation,
  type CashFlowBucket,
} from "../../domain/selectors.js";
import { formatMonth } from "../../ui/format.js";

export type PeriodGranularity = "month" | "quarter";

/** Empty-state range: the planning start through the move-in milestone. */
const DEFAULT_START_MONTH = "2026-11";
const DEFAULT_END_MONTH = FIXED_MILESTONES["la-mutat"];

interface CashFlowPeriod {
  key: string;
  label: string;
  startMonth: string;
  endMonth: string;
}

export interface PeriodCashFlow extends CashFlowBucket {
  label: string;
  cumulativeCents: number;
}

function monthDate(month: string): Date {
  return new Date(`${month}-01T00:00:00Z`);
}

function addMonths(month: string, count: number): string {
  const date = monthDate(month);
  date.setUTCMonth(date.getUTCMonth() + count);
  return date.toISOString().slice(0, 7);
}

function quarterIndex(month: string): number {
  return Math.floor((Number(month.slice(5, 7)) - 1) / 3);
}

function quarterStartMonth(month: string): string {
  return `${month.slice(0, 4)}-${String(quarterIndex(month) * 3 + 1).padStart(2, "0")}`;
}

function quarterKey(month: string): string {
  return `${month.slice(0, 4)}-T${quarterIndex(month) + 1}`;
}

function periodKey(month: string, granularity: PeriodGranularity): string {
  return granularity === "quarter" ? quarterKey(month) : month;
}

export function makeCashFlowPeriods(
  startMonth: string,
  endMonth: string,
  granularity: PeriodGranularity,
): CashFlowPeriod[] {
  const periods: CashFlowPeriod[] = [];
  const quarterly = granularity === "quarter";
  const firstMonth = quarterly ? quarterStartMonth(startMonth) : startMonth;
  const finalMonth = quarterly ? quarterStartMonth(endMonth) : endMonth;

  for (
    let cursor = firstMonth;
    cursor <= finalMonth;
    cursor = addMonths(cursor, quarterly ? 3 : 1)
  ) {
    periods.push(
      quarterly
        ? {
            key: quarterKey(cursor),
            label: `T${quarterIndex(cursor) + 1} ${cursor.slice(0, 4)}`,
            startMonth: cursor,
            endMonth: addMonths(cursor, 2),
          }
        : { key: cursor, label: formatMonth(cursor), startMonth: cursor, endMonth: cursor },
    );
  }
  return periods;
}

export function cashFlowMonthRange(dates: readonly string[]): {
  startMonth: string;
  endMonth: string;
} {
  const { start, end } = dateSpan(dates.map(monthKey));
  return { startMonth: start ?? DEFAULT_START_MONTH, endMonth: end ?? DEFAULT_END_MONTH };
}

/** Buckets allocations into periods with the domain cash-flow rules, plus running totals. */
export function aggregateCashFlowByPeriod(
  allocations: readonly CashFlowAllocation[],
  periods: readonly CashFlowPeriod[],
  granularity: PeriodGranularity,
  allowedItemIds?: ReadonlySet<string>,
): { flows: PeriodCashFlow[]; undated: CashFlowBucket } {
  const byKey = new Map(
    periods.map((period) => [
      period.key,
      { ...emptyCashFlowBucket(period.key), label: period.label },
    ]),
  );
  const undated = emptyCashFlowBucket("undated");

  for (const allocation of allocations) {
    if (allowedItemIds && !allowedItemIds.has(allocation.itemId)) continue;
    const bucket = allocation.date
      ? byKey.get(periodKey(monthKey(allocation.date), granularity))
      : undated;
    if (bucket) addToCashFlowBucket(bucket, allocation);
  }
  return { flows: withCumulativeCents([...byKey.values()]), undated };
}
