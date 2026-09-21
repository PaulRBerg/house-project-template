import { describe, expect, it } from "vitest";

import { FALLBACK_BUDGET_AREA_ID } from "./areas.js";
import {
  getBudgetAreaHierarchy,
  selectBudgetView,
  type BudgetHierarchyGroup,
  type BudgetHierarchyItem,
} from "./selectors.js";
import { makeDocument, makeGroup, makeInstalment, makeItem, makePayment } from "./test-fixtures.js";

function hierarchyItems(groups: BudgetHierarchyGroup[]): BudgetHierarchyItem[] {
  return groups.flatMap((group) =>
    group.children.flatMap((child) => (child.kind === "item" ? [child] : hierarchyItems([child]))),
  );
}

function sum(groups: BudgetHierarchyGroup[], field: keyof BudgetHierarchyGroup): number {
  return groups.reduce((total, group) => total + Number(group[field]), 0);
}

function requireGroup(group: BudgetHierarchyGroup | undefined): BudgetHierarchyGroup {
  if (!group) throw new Error("Grupul așteptat lipsește din ierarhie.");
  return group;
}

function makeAreaDocument() {
  const groups = [
    makeGroup({
      id: "finish",
      label: "La cheie",
      milestoneId: "la-cheie",
      sortOrder: 0,
    }),
    makeGroup({
      id: "finish-interior",
      label: "Finisaje",
      parentId: "finish",
      milestoneId: "la-cheie",
      sortOrder: 1,
    }),
    makeGroup({
      id: "finish-systems",
      label: "Sisteme",
      parentId: "finish",
      milestoneId: "la-cheie",
      sortOrder: 2,
    }),
  ];
  const items = [
    makeItem({
      id: "living-large",
      label: "Living mare",
      groupId: "finish-interior",
      areaId: "living-room",
      milestoneId: "la-cheie",
      sortOrder: 3,
      estimate: {
        kind: "total",
        amounts: { baseCents: 30_000, highCents: 30_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    }),
    makeItem({
      id: "living-owned",
      label: "Living deținut",
      groupId: "finish-interior",
      areaId: "living-room",
      milestoneId: "la-cheie",
      sortOrder: 1,
      costScope: "movable",
      costType: "movable-good",
      contingencyEligible: false,
      ownership: "owned",
      completion: { complete: true, completedOn: "2026-09-18" },
      estimate: {
        kind: "total",
        amounts: { baseCents: 15_000, highCents: 15_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    }),
    makeItem({
      id: "bedrooms-shared",
      label: "Dormitoare comun",
      groupId: "finish-interior",
      areaId: "bedroom",
      milestoneId: "la-cheie",
      sortOrder: 2,
      estimate: {
        kind: "total",
        amounts: { baseCents: 20_000, highCents: 20_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    }),
    makeItem({
      id: "fallback-system",
      label: "Sistem fără amplasare",
      groupId: "finish-systems",
      milestoneId: "la-cheie",
      sortOrder: 1,
      estimate: {
        kind: "total",
        amounts: { baseCents: 10_000, highCents: 10_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    }),
    makeItem({
      id: "archived-system",
      label: "Sistem arhivat",
      groupId: "finish-systems",
      areaId: "whole-house",
      milestoneId: "la-cheie",
      sortOrder: 2,
      archived: true,
      estimate: {
        kind: "total",
        amounts: { baseCents: 12_000, highCents: 12_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    }),
  ];
  return makeDocument({
    groups,
    items,
    instalments: [
      makeInstalment({
        id: "living-late",
        itemId: "living-large",
        label: "Living",
        dueOn: "2028-08",
        projectedCents: 30_000,
      }),
      makeInstalment({
        id: "bedrooms-early",
        itemId: "bedrooms-shared",
        label: "Dormitoare",
        dueOn: "2028-02",
        projectedCents: 20_000,
      }),
      makeInstalment({
        id: "archived-paid",
        itemId: "archived-system",
        label: "Arhivat",
        dueOn: "2027-12",
        projectedCents: 12_000,
      }),
    ],
    payments: [
      makePayment({
        id: "archived-payment",
        itemId: "archived-system",
        instalmentId: "archived-paid",
        paidOn: "2027-10-01",
        amountCents: 4_000,
      }),
    ],
  });
}

describe("getBudgetAreaHierarchy", () => {
  it("assigns every item once and preserves the stage rollups and schedule bounds", () => {
    const root = requireGroup(
      selectBudgetView(makeAreaDocument(), {
        scenario: "base",
        asOf: "2026-09-19",
      }).hierarchy[0],
    );
    const areas = getBudgetAreaHierarchy(root);
    const areaItems = hierarchyItems(areas);

    expect(areaItems.map((item) => item.id).sort()).toEqual(
      hierarchyItems([root])
        .map((item) => item.id)
        .sort(),
    );
    expect(new Set(areaItems.map((item) => item.id))).toHaveProperty("size", areaItems.length);
    for (const field of [
      "actualPaidCents",
      "futureCents",
      "contingencyCents",
      "forecastCents",
      "estimateCents",
      "totalCents",
      "settledCents",
    ] as const) {
      expect(sum(areas, field)).toBe(root[field]);
    }
    expect(areas.flatMap((area) => area.scheduleStartOn ?? []).sort()[0]).toBe(
      root.scheduleStartOn,
    );
    expect(
      areas
        .flatMap((area) => area.scheduleFinalOn ?? [])
        .sort()
        .at(-1),
    ).toBe(root.scheduleFinalOn);
  });

  it("keeps shared and fallback areas, namespaced category IDs, accounting, and row order", () => {
    const root = requireGroup(
      selectBudgetView(makeAreaDocument(), {
        scenario: "base",
        asOf: "2026-09-19",
      }).hierarchy[0],
    );
    const areas = getBudgetAreaHierarchy(root);
    const shared = requireGroup(areas.find((area) => area.id === "area-bedroom"));
    const fallback = requireGroup(
      areas.find((area) => area.id === `area-${FALLBACK_BUDGET_AREA_ID}`),
    );
    const living = requireGroup(areas.find((area) => area.id === "area-living-room"));
    const wholeHouse = requireGroup(areas.find((area) => area.id === "area-whole-house"));

    expect(shared.label).toBe("Bedroom");
    expect(hierarchyItems([fallback]).map((item) => item.id)).toEqual(["fallback-system"]);
    expect(shared.children[0]).toMatchObject({
      id: "area-bedroom--finish-interior",
      sourceGroupId: "finish-interior",
    });
    expect(living.children[0]).toMatchObject({
      id: "area-living-room--finish-interior",
      sourceGroupId: "finish-interior",
    });
    expect(hierarchyItems([living]).map((item) => item.id)).toEqual([
      "living-large",
      "living-owned",
    ]);
    expect(living.settledCents).toBe(15_000);
    expect(wholeHouse.actualPaidCents).toBe(4_000);
    expect(wholeHouse.totalCents).toBe(4_000);
    expect(wholeHouse.estimateCents).toBe(4_000);
  });
});
