import { describe, expect, it } from "vitest";

import {
  makeDocument,
  makeGroup,
  makeInstalment,
  makeItem,
  makePayment,
} from "../test/builders.js";
import { buildMonthlyCashFlow, selectBudgetView } from "./selectors.js";

const options = { asOf: "2027-01-01" };

describe("budget selectors", () => {
  it("keeps contingency rounding identical in separate and combined stage budgets", () => {
    const estimate = {
      kind: "total" as const,
      amounts: { baseCents: 5 },
      fixed: true,
      pricedOn: "2026-09-21",
    };
    const document = makeDocument({
      items: [
        makeItem({ estimate }),
        makeItem({ id: "extra-cent", milestoneId: "extra", estimate }),
      ],
      instalments: [],
    });
    const initial = selectBudgetView(document, options);
    const extra = selectBudgetView(document, { ...options, scope: "extra" });
    const all = selectBudgetView(document, { ...options, scope: "all" });
    expect(initial.items.map((item) => item.contingencyCents)).toEqual([1]);
    expect(extra.items.map((item) => item.contingencyCents)).toEqual([1]);
    expect(all.summary.totalCashForecastCents).toBe(12);
    expect(all.items.map((item) => item.contingencyCents)).toEqual([1, 1]);
  });

  it("separates Extra estimates, payments and cash flow unless explicitly requested", () => {
    const baseline = makeDocument();
    const document = makeDocument({
      groups: [
        ...baseline.groups,
        makeGroup({ id: "extras", label: "Extra", milestoneId: "extra" }),
      ],
      items: [
        ...baseline.items,
        makeItem({ id: "child-wardrobe", groupId: "extras", milestoneId: "extra" }),
      ],
      instalments: [
        ...baseline.instalments,
        makeInstalment({ id: "extra-plan", itemId: "child-wardrobe", dueOn: "2031-06" }),
      ],
      payments: [
        makePayment({
          id: "extra-payment",
          itemId: "child-wardrobe",
          instalmentId: "extra-plan",
          paidOn: "2029-06-20",
          amountCents: 2_000,
        }),
      ],
    });
    const initial = selectBudgetView(document, options);
    const extra = selectBudgetView(document, { ...options, scope: "extra" });
    const all = selectBudgetView(document, { ...options, scope: "all" });
    expect(initial).toEqual(selectBudgetView(baseline, options));
    expect(extra.items.map(({ item }) => item.id)).toEqual(["child-wardrobe"]);
    expect(extra.hierarchy.map(({ id }) => id)).toEqual(["extras"]);
    expect(extra.summary).toMatchObject({
      actualPaidCents: 2_000,
      remainingCashForecastCents: 8_800,
      totalCashForecastCents: 10_800,
    });
    expect(
      buildMonthlyCashFlow(extra.allocations).months.map(({ periodKey }) => periodKey),
    ).toEqual(["2029-06", "2031-06"]);
    expect(extra.upcomingPayments[0]?.itemId).toBe("child-wardrobe");
    expect(all.summary.totalCashForecastCents).toBe(
      initial.summary.totalCashForecastCents + extra.summary.totalCashForecastCents,
    );
    expect(all.allocations.reduce((sum, allocation) => sum + allocation.amountCents, 0)).toBe(
      all.summary.totalCashForecastCents,
    );
    expect(document.items[1]?.included).toBe(true);
    expect(document.payments).toHaveLength(1);
  });

  it("retains Extra actuals after archiving only in its separate and combined budgets", () => {
    const baseline = makeDocument();
    const document = makeDocument({
      groups: [
        ...baseline.groups,
        makeGroup({ id: "extras", milestoneId: "extra", archived: true }),
      ],
      items: [
        ...baseline.items,
        makeItem({ id: "extra-item", groupId: "extras", milestoneId: "extra" }),
      ],
      instalments: [
        ...baseline.instalments,
        makeInstalment({ id: "extra-plan", itemId: "extra-item", dueOn: "2031-06" }),
      ],
      payments: [makePayment({ itemId: "extra-item", instalmentId: "extra-plan" })],
    });
    expect(selectBudgetView(document, options)).toEqual(selectBudgetView(baseline, options));
    const extra = selectBudgetView(document, { ...options, scope: "extra" });
    expect(extra.summary).toMatchObject({
      actualPaidCents: 2_000,
      remainingCashForecastCents: 0,
      totalCashForecastCents: 2_000,
    });
    expect(extra.upcomingPayments).toEqual([]);
  });

  it("rounds quantity-rate money to integer euro cents", () => {
    const item = makeItem({
      estimate: {
        kind: "quantity-rate",
        quantity: 1.5,
        unit: "m²",
        rates: { baseCents: 101 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    });
    const view = selectBudgetView(makeDocument({ items: [item], instalments: [] }), options);
    expect(view.items[0]?.estimateCents).toBe(152);
    expect(view.items[0]?.unallocatedFutureCents).toBe(152);
  });

  it("does not double-count nested group totals", () => {
    const groups = [makeGroup({ id: "etapa" }), makeGroup({ id: "subetapa", parentId: "etapa" })];
    const item = makeItem({ groupId: "subetapa" });
    const view = selectBudgetView(
      makeDocument({ groups, items: [item], instalments: [] }),
      options,
    );
    expect(view.hierarchy).toHaveLength(1);
    expect(view.hierarchy[0]?.estimateCents).toBe(10_000);
    expect(view.hierarchy[0]?.totalCents).toBe(11_000);
    expect(view.summary.totalCashForecastCents).toBe(11_000);
  });

  it("keeps actuals, remaining plan, unallocated estimate, and contingency distinct", () => {
    const view = selectBudgetView(
      makeDocument({
        payments: [makePayment({ amountCents: 5_000 })],
        instalments: [makeInstalment({ projectedCents: 8_000 })],
      }),
      options,
    );
    const item = view.items[0];
    expect(item).toMatchObject({
      actualPaidCents: 5_000,
      scheduledRemainingCents: 3_000,
      unallocatedFutureCents: 2_000,
      contingencyCents: 500,
      forecastBeforeContingencyCents: 10_000,
      forecastCents: 10_500,
      discrepancy: { amountCents: 2_000, kind: "unallocated" },
    });
    expect(buildMonthlyCashFlow(view.allocations).undated.unallocatedCents).toBe(2_000);
    expect(buildMonthlyCashFlow(view.allocations).undated.contingencyCents).toBe(200);
    expect(view.summary).toMatchObject({
      actualPaidCents: 5_000,
      totalCashForecastCents: 10_500,
      remainingCashForecastCents: 5_500,
    });
  });

  it("retains overpayments without creating negative future cash", () => {
    const view = selectBudgetView(
      makeDocument({ payments: [makePayment({ amountCents: 12_000 })] }),
      options,
    );
    expect(view.items[0]).toMatchObject({
      actualPaidCents: 12_000,
      scheduledRemainingCents: 0,
      unallocatedFutureCents: 0,
      forecastCents: 12_000,
      discrepancy: { amountCents: -2_000, kind: "over-scheduled" },
    });
    expect(view.hierarchy[0]).toMatchObject({ estimateCents: 12_000, totalCents: 12_000 });
    expect(view.allocations.every((allocation) => allocation.amountCents >= 0)).toBe(true);
    expect(view.summary.remainingCashForecastCents).toBe(0);
  });

  it("excludes optional future costs, cancels archived plans, and preserves their actuals", () => {
    const optional = makeItem({
      id: "mobilier",
      costScope: "movable",
      costType: "movable-good",
      contingencyEligible: false,
      included: false,
      estimate: {
        kind: "total",
        amounts: { baseCents: 2_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    });
    const archived = makeItem({ id: "vechi", archived: true, sortOrder: 2 });
    const owned = makeItem({
      id: "masa-detinuta",
      costScope: "movable",
      costType: "movable-good",
      contingencyEligible: false,
      ownership: "owned",
      completion: { complete: true, completedOn: "2026-09-18" },
      estimate: {
        kind: "total",
        amounts: { baseCents: 0 },
        fixed: false,
        pricedOn: "2020-01-01",
      },
      sortOrder: 3,
    });
    const view = selectBudgetView(
      makeDocument({
        items: [makeItem(), optional, archived, owned],
        instalments: [
          makeInstalment(),
          makeInstalment({ id: "transa-mobilier", itemId: "mobilier", projectedCents: 2_000 }),
          makeInstalment({ id: "transa-vechi", itemId: "vechi", projectedCents: 10_000 }),
        ],
        payments: [
          makePayment({
            id: "plata-vechi",
            itemId: "vechi",
            instalmentId: "transa-vechi",
            amountCents: 1_000,
          }),
        ],
      }),
      options,
    );
    expect(view.hierarchy[0]).toMatchObject({ estimateCents: 11_000, totalCents: 12_000 });
    expect(view.summary.remainingCashForecastCents).toBe(11_000);
    expect(view.items.find((entry) => entry.item.id === "mobilier")?.forecastCents).toBe(0);
    expect(view.items.find((entry) => entry.item.id === "vechi")?.forecastCents).toBe(1_000);
    expect(view.items.find((entry) => entry.item.id === "masa-detinuta")?.forecastCents).toBe(0);
    expect(view.timeline[0]).toMatchObject({
      itemCount: 2,
      completeItemCount: 1,
      forecastCents: 12_000,
    });
  });

  it("keeps unfixed and fixed estimates at today's prices regardless of the due date", () => {
    const unfixed = makeItem({
      estimate: {
        kind: "total",
        amounts: { baseCents: 10_000 },
        fixed: false,
        pricedOn: "2027-01-01",
      },
    });
    const dated = selectBudgetView(
      makeDocument({
        items: [unfixed],
        instalments: [makeInstalment({ dueOn: "2028-01" })],
      }),
      options,
    );
    const fixed = selectBudgetView(makeDocument(), options);
    expect(dated.items[0]?.scheduledRemainingCents).toBe(10_000);
    expect(fixed.items[0]).toMatchObject({
      estimateCents: 10_000,
      scheduledRemainingCents: 10_000,
      unallocatedFutureCents: 0,
      instalments: [{ projectedCents: 10_000 }],
    });
  });

  it("keeps land at its base estimate and owned purchases settled", () => {
    const land = makeItem({
      id: "teren",
      costType: "land",
      contingencyEligible: false,
      estimate: {
        kind: "total",
        amounts: { baseCents: 8_250_000 },
        fixed: false,
        pricedOn: "2026-01-01",
      },
    });
    const owned = makeItem({
      id: "achizitie-detinuta",
      ownership: "owned",
      completion: { complete: true },
      estimate: {
        kind: "total",
        amounts: { baseCents: 10_000 },
        fixed: false,
        pricedOn: "2026-01-01",
      },
      sortOrder: 1,
    });
    const view = selectBudgetView(
      makeDocument({
        items: [land, owned],
        instalments: [
          makeInstalment({
            id: "transa-teren",
            itemId: "teren",
            projectedCents: 8_250_000,
            dueOn: "2029-01",
          }),
          makeInstalment({
            id: "transa-detinuta",
            itemId: "achizitie-detinuta",
            projectedCents: 10_000,
            dueOn: "2029-01",
          }),
        ],
      }),
      options,
    );
    expect(view.items.find((entry) => entry.item.id === "teren")?.scheduledRemainingCents).toBe(
      8_250_000,
    );
    expect(
      view.items.find((entry) => entry.item.id === "achizitie-detinuta")?.scheduledRemainingCents,
    ).toBe(0);

    expect(view.items.find((entry) => entry.item.id === "teren")?.estimateCents).toBe(8_250_000);
    expect(view.items.find((entry) => entry.item.id === "achizitie-detinuta")?.estimateCents).toBe(
      10_000,
    );
  });

  it("keeps completion independent from money", () => {
    const incomplete = selectBudgetView(makeDocument(), options);
    const complete = selectBudgetView(
      makeDocument({ items: [makeItem({ completion: { complete: true } })] }),
      options,
    );
    expect(complete.summary.totalCashForecastCents).toBe(incomplete.summary.totalCashForecastCents);
  });

  it.each([0, 2_500, 12_000])(
    "includes owned prices once in nested table totals with %i cents of recorded payments",
    (recordedCents) => {
      const owned = makeItem({
        id: "owned-device",
        groupId: "devices",
        ownership: "owned",
        completion: { complete: true },
      });
      const view = selectBudgetView(
        makeDocument({
          groups: [makeGroup(), makeGroup({ id: "devices", parentId: "constructie" })],
          items: [makeItem(), owned],
          payments: recordedCents
            ? [
                makePayment({
                  itemId: owned.id,
                  instalmentId: "owned-instalment",
                  amountCents: recordedCents,
                }),
              ]
            : [],
          instalments: [
            makeInstalment(),
            makeInstalment({ id: "owned-instalment", itemId: owned.id }),
          ],
        }),
        options,
      );
      const ownedTotal = Math.max(10_000, recordedCents);

      expect(view.items.find((entry) => entry.item.id === owned.id)).toMatchObject({
        totalCents: ownedTotal,
        settledCents: ownedTotal,
        forecastCents: recordedCents,
      });
      expect(view.hierarchy[0]).toMatchObject({
        estimateCents: 10_000 + ownedTotal,
        totalCents: 11_000 + ownedTotal,
        settledCents: ownedTotal,
        children: expect.arrayContaining([
          expect.objectContaining({
            id: "devices",
            estimateCents: ownedTotal,
            totalCents: ownedTotal,
            settledCents: ownedTotal,
          }),
        ]),
      });
      expect(view.summary.totalCashForecastCents).toBe(11_000 + recordedCents);
      expect(view.summary.remainingCashForecastCents).toBe(11_000);
      expect(view.allocations.filter((allocation) => allocation.itemId === owned.id)).toEqual(
        recordedCents
          ? [expect.objectContaining({ kind: "actual", amountCents: recordedCents })]
          : [],
      );
    },
  );

  it.each([{ included: false }, { archived: true }])(
    "excludes inactive owned values from table totals while retaining recorded payments: %j",
    (state) => {
      const view = selectBudgetView(
        makeDocument({
          items: [makeItem({ ownership: "owned", completion: { complete: true }, ...state })],
          payments: [makePayment()],
        }),
        options,
      );

      expect(view.hierarchy[0]).toMatchObject({
        estimateCents: 2_000,
        totalCents: 2_000,
        settledCents: 2_000,
      });
    },
  );

  it("retains a zero-cost completed owned acquisition", () => {
    const owned = makeItem({
      id: "obiect-detinut",
      ownership: "owned",
      completion: { complete: true, completedOn: "2026-09-18" },
      estimate: {
        kind: "total",
        amounts: { baseCents: 0 },
        fixed: false,
        pricedOn: "2026-09-18",
      },
    });
    const view = selectBudgetView(
      makeDocument({ items: [owned], instalments: [], payments: [] }),
      options,
    );
    expect(view.items).toHaveLength(1);
    expect(view.items[0]).toMatchObject({
      forecastCents: 0,
      item: { id: "obiect-detinut", ownership: "owned", completion: { complete: true } },
    });
  });

  it("keeps positive owned estimates visible without creating future obligations", () => {
    const owned = makeItem({
      ownership: "owned",
      completion: { complete: true, completedOn: "2026-11-20" },
      estimate: {
        kind: "total",
        amounts: { baseCents: 10_000 },
        fixed: false,
        pricedOn: "2025-01-01",
      },
    });
    const document = makeDocument({
      items: [owned],
      instalments: [makeInstalment({ projectedCents: 10_000, dueOn: "2026-12" })],
      payments: [makePayment({ amountCents: 2_500 })],
    });

    const view = selectBudgetView(document, options);
    expect(view.items[0]).toMatchObject({
      active: true,
      estimateCents: 10_000,
      actualPaidCents: 2_500,
      scheduledRemainingCents: 0,
      unallocatedFutureCents: 0,
      contingencyCents: 0,
      overdueCents: 0,
      discrepancy: { amountCents: 0, kind: "balanced" },
    });
    expect(view.summary).toMatchObject({
      actualPaidCents: 2_500,
      totalCashForecastCents: 2_500,
      remainingCashForecastCents: 0,
    });
    expect(view.upcomingPayments).toEqual([]);
    expect(buildMonthlyCashFlow(view.allocations).months).toEqual([
      expect.objectContaining({ periodKey: "2026-11", actualCents: 2_500, scheduledCents: 0 }),
    ]);
    expect(view.timeline[0]).toMatchObject({ itemCount: 1, completeItemCount: 1 });
  });

  it("allocates the fixed 10 % contingency proportionally without losing a cent", () => {
    const first = makeItem({
      id: "primul",
      estimate: {
        kind: "total",
        amounts: { baseCents: 15 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    });
    const second = makeItem({
      id: "al-doilea",
      sortOrder: 1,
      estimate: {
        kind: "total",
        amounts: { baseCents: 25 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    });
    const view = selectBudgetView(
      makeDocument({
        items: [first, second],
        instalments: [
          makeInstalment({ id: "transa-unu", itemId: "primul", projectedCents: 15 }),
          makeInstalment({ id: "transa-doi", itemId: "al-doilea", projectedCents: 25 }),
        ],
      }),
      options,
    );
    const contingency = view.allocations.filter((allocation) => allocation.kind === "contingency");
    expect(contingency.map((allocation) => allocation.amountCents)).toEqual([2, 2]);
  });

  it("subtracts actual payments from the plan and keeps overspend visible", () => {
    const item = makeItem({
      estimate: {
        kind: "total",
        amounts: { baseCents: 120 },
        fixed: false,
        pricedOn: "2027-01-01",
      },
    });
    const partial = selectBudgetView(
      makeDocument({
        items: [item],
        instalments: [makeInstalment({ projectedCents: 120, dueOn: "2028-01" })],
        payments: [makePayment({ amountCents: 50 })],
      }),
      options,
    );
    expect(partial.items[0]?.instalments[0]).toMatchObject({
      actualPaidCents: 50,
      projectedCents: 120,
      remainingCents: 70,
    });
    expect(partial.items[0]?.unallocatedFutureCents).toBe(0);
    expect(
      buildMonthlyCashFlow(partial.allocations).months.some(
        (month) => month.periodKey === "2028-01",
      ),
    ).toBe(true);

    const fullyPaid = selectBudgetView(
      makeDocument({
        items: [item],
        instalments: [makeInstalment({ projectedCents: 120, dueOn: "2028-01" })],
        payments: [makePayment({ amountCents: 130 })],
      }),
      options,
    );
    expect(fullyPaid.items[0]).toMatchObject({
      actualPaidCents: 130,
      scheduledRemainingCents: 0,
      forecastCents: 130,
      discrepancy: { amountCents: -10, kind: "over-scheduled" },
    });
  });

  it("shows overdue and undated rows in shared timeline selectors", () => {
    const groups = [makeGroup(), makeGroup({ id: "finisaje", milestoneId: "la-gri" })];
    const undatedItem = makeItem({
      id: "tencuiala",
      groupId: "finisaje",
      milestoneId: "la-gri",
      sortOrder: 1,
    });
    const document = makeDocument({
      groups,
      items: [makeItem(), undatedItem],
      instalments: [
        makeInstalment({ dueOn: "2026-12" }),
        makeInstalment({ id: "transa-tencuiala", itemId: "tencuiala", dueOn: undefined }),
      ],
    });
    const view = selectBudgetView(document, options);
    expect(view.items[0]?.overdueCents).toBe(10_000);
    expect(view.upcomingPayments.some((payment) => payment.overdue)).toBe(true);
    expect(buildMonthlyCashFlow(view.allocations).undated.scheduledCents).toBe(10_000);
    expect(view.timeline.find((entry) => entry.milestone.id === "la-gri")?.itemCount).toBe(1);
  });

  it("lists the next unpaid instalment, not the advance already paid", () => {
    const view = selectBudgetView(
      makeDocument({
        instalments: [
          makeInstalment({ projectedCents: 5_000, dueOn: "2027-01" }),
          makeInstalment({ id: "transa-finala", projectedCents: 5_000, dueOn: "2027-03" }),
        ],
        payments: [makePayment({ amountCents: 5_000 })],
      }),
      { asOf: "2027-01-02" },
    );
    expect(view.upcomingPayments.map((payment) => payment.dueOn)).toEqual(["2027-03"]);
  });

  it("marks a monthly deadline overdue only after that month ends", () => {
    const document = makeDocument({
      instalments: [makeInstalment({ dueOn: "2027-01" })],
    });

    const duringMonth = selectBudgetView(document, { asOf: "2027-01-31" });
    const afterMonth = selectBudgetView(document, { asOf: "2027-02-01" });

    expect(duringMonth.items[0]?.instalments[0]?.overdue).toBe(false);
    expect(duringMonth.upcomingPayments[0]?.overdue).toBe(false);
    expect(afterMonth.items[0]?.instalments[0]?.overdue).toBe(true);
    expect(afterMonth.upcomingPayments[0]?.overdue).toBe(true);
  });

  it("places standalone items before child categories while sorting each block by cost", () => {
    const groups = [
      makeGroup({ id: "root" }),
      makeGroup({ id: "category-high", parentId: "root" }),
      makeGroup({ id: "category-low", parentId: "root" }),
    ];
    const items = [
      makeItem({ id: "item-low", groupId: "root" }),
      makeItem({
        id: "item-high",
        groupId: "root",
        estimate: {
          kind: "total",
          amounts: { baseCents: 20_000 },
          fixed: true,
          pricedOn: "2026-09-18",
        },
      }),
      makeItem({
        id: "category-high-item",
        groupId: "category-high",
        estimate: {
          kind: "total",
          amounts: { baseCents: 40_000 },
          fixed: true,
          pricedOn: "2026-09-18",
        },
      }),
      makeItem({
        id: "category-low-item",
        groupId: "category-low",
        estimate: {
          kind: "total",
          amounts: { baseCents: 30_000 },
          fixed: true,
          pricedOn: "2026-09-18",
        },
      }),
    ];
    const view = selectBudgetView(
      makeDocument({ groups, items, instalments: [], payments: [] }),
      options,
    );

    expect(view.hierarchy[0]?.children.map((child) => child.id)).toEqual([
      "item-high",
      "item-low",
      "category-high",
      "category-low",
    ]);
  });

  it("derives item and descendant group bounds from every dated scheduled instalment", () => {
    const groups = [makeGroup({ id: "root" }), makeGroup({ id: "child", parentId: "root" })];
    const ranged = makeItem({ id: "ranged", groupId: "child" });
    const single = makeItem({ id: "single", groupId: "root", sortOrder: 1 });
    const undated = makeItem({ id: "undated", groupId: "child", sortOrder: 2 });
    const view = selectBudgetView(
      makeDocument({
        groups,
        items: [ranged, single, undated],
        instalments: [
          makeInstalment({
            id: "ranged-first",
            itemId: "ranged",
            dueOn: "2027-02",
            projectedCents: 5_000,
          }),
          makeInstalment({
            id: "ranged-last",
            itemId: "ranged",
            dueOn: "2028-08",
            projectedCents: 5_000,
          }),
          makeInstalment({
            id: "single-date",
            itemId: "single",
            dueOn: "2029-01",
          }),
          makeInstalment({ id: "without-date", itemId: "undated", dueOn: undefined }),
        ],
        payments: [
          makePayment({
            id: "paid-first",
            itemId: "ranged",
            instalmentId: "ranged-first",
            amountCents: 5_000,
          }),
          makePayment({
            id: "paid-last",
            itemId: "ranged",
            instalmentId: "ranged-last",
            amountCents: 5_000,
          }),
        ],
      }),
      options,
    );

    expect(view.items.find((entry) => entry.item.id === "ranged")).toMatchObject({
      scheduledRemainingCents: 0,
      scheduleStartOn: "2027-02",
      scheduleFinalOn: "2028-08",
    });
    expect(view.items.find((entry) => entry.item.id === "single")).toMatchObject({
      scheduleStartOn: "2029-01",
      scheduleFinalOn: "2029-01",
    });
    expect(view.items.find((entry) => entry.item.id === "undated")).not.toHaveProperty(
      "scheduleStartOn",
    );
    expect(view.items.find((entry) => entry.item.id === "undated")).not.toHaveProperty(
      "scheduleFinalOn",
    );
    expect(view.hierarchy[0]).toMatchObject({
      scheduleStartOn: "2027-02",
      scheduleFinalOn: "2029-01",
    });
    expect(view.hierarchy[0]?.children.find((child) => child.kind === "group")).toMatchObject({
      scheduleStartOn: "2027-02",
      scheduleFinalOn: "2028-08",
    });
  });
});
