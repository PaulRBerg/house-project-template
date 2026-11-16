import { describe, expect, it } from "vitest";

import type { CashFlowAllocation } from "../../domain/selectors.js";
import {
  aggregateCashFlowByPeriod,
  makeCashFlowPeriods,
  cashFlowMonthRange,
} from "./cash-flow-periods.js";

const allocations: CashFlowAllocation[] = [
  { id: "actual-a", itemId: "a", kind: "actual", date: "2027-02-03", amountCents: 12_000 },
  { id: "scheduled-a", itemId: "a", kind: "scheduled", date: "2027-03", amountCents: 40_000 },
  { id: "reserve-a", itemId: "a", kind: "contingency", date: "2027-03", amountCents: 4_000 },
  { id: "scheduled-b", itemId: "b", kind: "scheduled", date: "2027-04", amountCents: 80_000 },
  { id: "unallocated-a", itemId: "a", kind: "unallocated", amountCents: 6_000 },
];

describe("cash-flow periods", () => {
  it("uses the first and last dated flow, with a practical empty-state fallback", () => {
    expect(cashFlowMonthRange(["2030-02-05", "2027-09-01"])).toEqual({
      startMonth: "2027-09",
      endMonth: "2030-02",
    });
    expect(cashFlowMonthRange([])).toEqual({ startMonth: "2026-11", endMonth: "2029-06" });
    expect(makeCashFlowPeriods("2026-11", "2027-02", "month").map((period) => period.key)).toEqual([
      "2026-11",
      "2026-12",
      "2027-01",
      "2027-02",
    ]);
  });

  it("labels calendar periods with full Romanian years", () => {
    expect(
      makeCashFlowPeriods("2027-09", "2027-10", "month").map((period) => period.label),
    ).toEqual(["Sep 2027", "Oct 2027"]);
    expect(
      makeCashFlowPeriods("2027-02", "2027-08", "quarter").map((period) => period.label),
    ).toEqual(["T1 2027", "T2 2027", "T3 2027"]);
  });

  it("aggregates filtered payments by quarter without mixing the reserve into obligations", () => {
    const periods = makeCashFlowPeriods("2027-01", "2027-06", "quarter");
    const { flows, undated } = aggregateCashFlowByPeriod(
      allocations,
      periods,
      "quarter",
      new Set(["a"]),
    );

    expect(flows.map((flow) => flow.periodKey)).toEqual(["2027-T1", "2027-T2"]);
    expect(flows[0]).toMatchObject({
      actualCents: 12_000,
      scheduledCents: 40_000,
      contingencyCents: 4_000,
      totalCents: 56_000,
    });
    expect(flows[1]?.totalCents).toBe(0);
    expect(undated).toMatchObject({ unallocatedCents: 6_000, totalCents: 6_000 });
  });
});
