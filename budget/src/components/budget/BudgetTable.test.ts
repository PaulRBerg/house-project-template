import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { budgetTableProps } from "../../test/budget-table.js";
import {
  makeDocument,
  makeGroup,
  makeInstalment,
  makeItem,
  makePayment,
} from "../../test/builders.js";
import { BudgetTable } from "./BudgetTable.js";
import type { CostScopeFilter, StatusFilter } from "./BudgetToolbar.js";

function renderTable(
  document: ReturnType<typeof makeDocument>,
  search = "",
  selectedCategory = "constructie",
  grouping: "rooms" | "categories" = "rooms",
  activeFilters: Partial<{ costScope: CostScopeFilter; status: StatusFilter }> = {},
): string {
  return renderToStaticMarkup(
    createElement(
      BudgetTable,
      budgetTableProps(document, {
        filters: { search, costScope: "all", status: "all", ...activeFilters },
        grouping,
        selectedCategory,
      }),
    ),
  );
}

function rowById(markup: string, id: string): string {
  return markup.match(new RegExp(`<tr[^>]*data-budget-id="${id}"[^>]*>.*?<\\/tr>`, "s"))?.[0] ?? "";
}

function summaryById(markup: string, id: string): string {
  const start = markup.indexOf(`data-budget-summary="${id}"`);
  return start === -1 ? "" : markup.slice(start, markup.indexOf("<table", start));
}

function areaSummaryById(markup: string, id: string): string {
  const start = markup.indexOf(`data-budget-area-summary="${id}"`);
  return start === -1 ? "" : markup.slice(start, markup.indexOf("<table", start));
}

describe("BudgetTable", () => {
  it("offers item details from both root and nested rows without completion controls", () => {
    const nestedGroup = makeGroup({ id: "nested", parentId: "constructie" });
    const rootItem = makeItem({ id: "root-item", label: "Cost direct" });
    const nestedItem = makeItem({
      id: "nested-item",
      groupId: nestedGroup.id,
      label: "Cost grupat",
    });
    const markup = renderTable(
      makeDocument({ groups: [makeGroup(), nestedGroup], items: [rootItem, nestedItem] }),
    );

    for (const item of [rootItem, nestedItem]) {
      const row = rowById(markup, item.id);
      expect(row).toContain('aria-haspopup="dialog"');
      expect(row).toContain("<button");
      expect(row).toContain(item.label);
      expect(row).not.toContain("<input");
    }
  });

  it.each([
    ["planned", false, "planned", "work", "€3,900–€4,290"],
    ["fixed", true, "planned", "work", "€3,900–€4,290"],
    ["owned", false, "owned", "work", "€3,900"],
    ["land", false, "planned", "land", "€3,900"],
  ] as const)(
    "shows the base quantity-derived total for %s costs",
    (_label, fixed, ownership, costType, total) => {
      const item = makeItem({
        ownership,
        costType,
        contingencyEligible: costType !== "land",
        completion: { complete: ownership === "owned" },
        estimate: {
          kind: "quantity-rate",
          quantity: 260,
          unit: "m²",
          rates: { baseCents: 1_500 },
          fixed,
          pricedOn: "2026-09-19",
        },
      });
      const document = makeDocument({ items: [item], instalments: [], payments: [] });
      const row = rowById(renderTable(document, "", item.groupId), item.id);

      expect(row).toContain(`<strong>${total}</strong>`);
    },
  );

  it("shows an owned item's historical paid price without a zero forecast", () => {
    const item = makeItem({
      label: "Obiect deja cumpărat",
      ownership: "owned",
      completion: { complete: true, completedOn: "2026-09-18" },
      estimate: {
        kind: "total",
        amounts: { baseCents: 260_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    });

    const markup = renderTable(makeDocument({ items: [item], instalments: [], payments: [] }));
    const row = rowById(markup, item.id);

    expect(row).toContain("<strong>€2,600</strong>");
    expect(row).not.toContain("€0");
    expect(summaryById(markup, item.groupId)).toContain("€2,600</strong>");
    expect(summaryById(markup, item.groupId)).toContain("Plătit");
    expect(summaryById(markup, item.groupId)).not.toContain('role="progressbar"');
  });

  it("shows an unpaid total once with a quiet label and no progress bar or percentage", () => {
    const row = summaryById(renderTable(makeDocument()), "constructie");

    expect(row.match(/€110/g)).toHaveLength(1);
    expect(row).toContain("€100–€110</strong>");
    expect(row).toContain("Neplătit");
    expect(row).not.toContain('role="progressbar"');
    expect(row).not.toContain("0%");
    expect(row).not.toContain("rămas");
  });

  it("rolls item ranges up through nested groups and the category summary", () => {
    const nestedGroup = makeGroup({ id: "furniture", label: "Mobilier", parentId: "constructie" });
    const item = makeItem({ groupId: nestedGroup.id });
    const markup = renderTable(makeDocument({ groups: [makeGroup(), nestedGroup], items: [item] }));

    expect(rowById(markup, item.id)).toContain("<strong>€100–€110</strong>");
    expect(rowById(markup, nestedGroup.id)).toContain("<strong>€100–€110</strong>");
    expect(summaryById(markup, "constructie")).toContain("€100–€110</strong>");
  });

  it("shows paid and remaining amounts for a partial payment, including contingency", () => {
    const markup = renderTable(makeDocument({ payments: [makePayment({ amountCents: 5_000 })] }));
    for (const id of ["constructie", "structura"]) {
      const row = id === "constructie" ? summaryById(markup, id) : rowById(markup, id);
      expect(row).toContain("€50 plătit");
      expect(row).toContain("€55 rămas");
      expect(row).toContain('aria-valuenow="5000"');
      expect(row).toContain('aria-valuemax="10500"');
      expect(row).toContain('aria-valuetext="€50 plătit, €55 rămas"');
    }
  });

  it("does not show payment progress for a zero-cost group", () => {
    const row = summaryById(
      renderTable(makeDocument({ items: [], instalments: [] })),
      "constructie",
    );
    expect(row).toContain("€0</strong>");
    expect(row).not.toContain('role="progressbar"');
    expect(row).not.toContain("Plătit");
  });

  it("hides one-off row progress while retaining group, partial-progress and mixed category totals", () => {
    const nestedGroup = makeGroup({
      id: "constructie-fitness",
      label: "Fitness",
      parentId: "constructie",
    });
    const unpaid = makeItem({
      id: "one-off-unpaid",
      label: "Achiziție unică neplătită",
      groupId: nestedGroup.id,
      paymentMode: "one-off",
      contingencyEligible: false,
      estimate: {
        kind: "total",
        amounts: { baseCents: 10_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    });
    const owned = makeItem({
      id: "one-off-owned",
      label: "Achiziție unică deținută",
      groupId: nestedGroup.id,
      ownership: "owned",
      completion: { complete: true, completedOn: "2026-09-18" },
      paymentMode: "one-off",
      contingencyEligible: false,
      estimate: {
        kind: "total",
        amounts: { baseCents: 20_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    });
    const staged = makeItem({
      id: "staged",
      label: "Achiziție etapizată",
      paymentMode: "partial-progress",
      contingencyEligible: false,
      estimate: {
        kind: "total",
        amounts: { baseCents: 30_000 },
        fixed: true,
        pricedOn: "2026-09-18",
      },
    });
    const markup = renderTable(
      makeDocument({
        groups: [makeGroup(), nestedGroup],
        items: [unpaid, owned, staged],
        instalments: [makeInstalment({ itemId: staged.id, projectedCents: 30_000 })],
        payments: [
          makePayment({
            itemId: staged.id,
            instalmentId: "transa-structura",
            amountCents: 5_000,
          }),
        ],
      }),
      "achiziție",
    );

    for (const id of [unpaid.id, owned.id]) {
      const row = rowById(markup, id);
      expect(row).not.toContain("Neplătit");
      expect(row).not.toContain("Plătit");
      expect(row).not.toContain('role="progressbar"');
      expect(row.match(/<td/g) ?? []).toHaveLength(4);
    }
    const group = rowById(markup, nestedGroup.id);
    expect(group).toContain("€200 plătit");
    expect(group).toContain("€100 rămas");
    expect(group).toContain('role="progressbar"');
    const stagedRow = rowById(markup, staged.id);
    expect(stagedRow).toContain("€50 plătit");
    expect(stagedRow).toContain("€250 rămas");
    expect(stagedRow).toContain('role="progressbar"');
    const summary = summaryById(markup, "constructie");
    expect(summary).toContain("€600</strong>");
    expect(summary).toContain("€250 plătit");
    expect(summary).toContain("€350 rămas");
    expect(summary).toContain('aria-valuenow="25000"');
    expect(summary).toContain('aria-valuemax="60000"');
    expect(summary).toContain('role="progressbar"');
  });

  it("shows a paid label without a zero remainder, progress bar, or redundant percentage", () => {
    const item = makeItem();
    const document = makeDocument({
      items: [item],
      instalments: [
        makeInstalment({ projectedCents: 5_000 }),
        makeInstalment({ id: "transa-finala", projectedCents: 5_000 }),
      ],
      payments: [
        makePayment({ amountCents: 5_000 }),
        makePayment({ id: "plata-finala", instalmentId: "transa-finala", amountCents: 5_000 }),
      ],
    });

    const row = rowById(renderTable(document), item.id);

    expect(row).toContain("<strong>€100</strong>");
    expect(row).not.toContain("€0");
    expect(row).toContain("Plătit");
    expect(row).not.toContain('role="progressbar"');
    expect(row).not.toContain("100%");
  });

  it("explains when the selected category has no children", () => {
    const markup = renderTable(makeDocument({ items: [], instalments: [] }));

    expect(markup).toContain("Niciun element din categoria La roșu nu corespunde filtrelor.");
  });

  it("initially expands groups and shows their items without a search", () => {
    const nestedGroup = makeGroup({
      id: "constructie-structura",
      label: "Structură",
      parentId: "constructie",
    });
    const parent = makeItem({ id: "root-item", groupId: "constructie" });
    const nested = makeItem({ id: "nested-item", groupId: nestedGroup.id });
    const markup = renderTable(
      makeDocument({ groups: [makeGroup(), nestedGroup], items: [parent, nested] }),
    );

    expect(summaryById(markup, "constructie")).toContain("La roșu");
    expect(rowById(markup, "constructie")).toBe("");
    expect(rowById(markup, parent.id)).toContain(parent.label);
    expect(rowById(markup, "constructie-structura")).toContain('aria-expanded="true"');
    expect(rowById(markup, nested.id)).toContain(nested.label);
  });

  it("uses concise cost and payment labels and a pointer for expandable rows", () => {
    const nestedGroup = makeGroup({
      id: "constructie-structura",
      label: "Structură",
      parentId: "constructie",
    });
    const markup = renderTable(
      makeDocument({
        groups: [makeGroup(), nestedGroup],
        items: [makeItem({ groupId: nestedGroup.id })],
      }),
    );

    expect(markup).toContain(">Cost</th>");
    expect(markup).not.toContain("Estimare-prognoză");
    expect(rowById(markup, nestedGroup.id)).toContain("cursor-pointer");
  });

  it("renders groups as tinted bands with item counts and indents items past the chevron", () => {
    const nestedGroup = makeGroup({
      id: "constructie-structura",
      label: "Structură",
      parentId: "constructie",
    });
    const deepGroup = makeGroup({
      id: "constructie-structura-fundatie",
      label: "Fundație",
      parentId: nestedGroup.id,
    });
    const rootItem = makeItem({ id: "root-item", groupId: "constructie" });
    const nestedItem = makeItem({ id: "nested-item", groupId: nestedGroup.id });
    const deepItem = makeItem({ id: "deep-item", groupId: deepGroup.id });
    const markup = renderTable(
      makeDocument({
        groups: [makeGroup(), nestedGroup, deepGroup],
        items: [rootItem, nestedItem, deepItem],
      }),
    );

    const nestedRow = rowById(markup, nestedGroup.id);
    expect(nestedRow).toContain("bg-stage-tint/50");
    expect(nestedRow).toContain("2 elemente");
    const deepRow = rowById(markup, deepGroup.id);
    expect(deepRow).toContain("bg-stage-tint/25");
    expect(deepRow).toContain("1 element<");
    expect(rowById(markup, rootItem.id)).toContain("padding-inline-start:43px");
    expect(rowById(markup, nestedItem.id)).toContain("padding-inline-start:59px");
  });

  it("expands matching nested groups while searching", () => {
    const nestedGroup = makeGroup({
      id: "constructie-structura",
      label: "Structură",
      parentId: "constructie",
    });
    const nested = makeItem({
      id: "matching-item",
      groupId: nestedGroup.id,
      label: "Grindă",
    });
    const markup = renderTable(
      makeDocument({ groups: [makeGroup(), nestedGroup], items: [nested] }),
      "grindă",
    );

    expect(summaryById(markup, "constructie")).toContain("La roșu");
    expect(rowById(markup, "constructie-structura")).toContain('aria-expanded="true"');
    expect(rowById(markup, nested.id)).toContain(nested.label);
  });

  it("reveals a category's children when its root label matches the search", () => {
    const nestedGroup = makeGroup({
      id: "constructie-structura",
      label: "Structură",
      parentId: "constructie",
    });
    const nested = makeItem({
      id: "nested-item",
      groupId: nestedGroup.id,
      label: "Grindă",
    });
    const markup = renderTable(
      makeDocument({ groups: [makeGroup(), nestedGroup], items: [nested] }),
      "roșu",
    );

    expect(rowById(markup, nestedGroup.id)).toContain('aria-expanded="true"');
    expect(rowById(markup, nested.id)).toContain(nested.label);
  });

  it("isolates the selected root without duplicating stage navigation", () => {
    const plans = makeGroup({ id: "professional", label: "Planuri", sortOrder: 0 });
    const construction = makeGroup({ id: "construction", label: "La roșu", sortOrder: 1 });
    const planItem = makeItem({ id: "plan-item", label: "Arhitectură", groupId: plans.id });
    const constructionItem = makeItem({
      id: "construction-item",
      label: "Fundație",
      groupId: construction.id,
    });
    const document = makeDocument({
      groups: [plans, construction],
      items: [planItem, constructionItem],
      instalments: [],
    });
    const markup = renderTable(document, "", plans.id);

    expect(markup).not.toContain('role="tablist"');
    expect(markup).toContain("Planuri");
    expect(markup).not.toContain("La roșu");
    expect(markup).toContain("Arhitectură");
    expect(markup).not.toContain("Fundație");
    expect(summaryById(markup, plans.id)).toContain("Planuri");
  });

  it("keeps the selected category visible when its filters have no matches", () => {
    const plans = makeGroup({ id: "professional", label: "Planuri", sortOrder: 0 });
    const construction = makeGroup({ id: "construction", label: "La roșu", sortOrder: 1 });
    const document = makeDocument({
      groups: [plans, construction],
      items: [makeItem({ id: "plan-item", groupId: plans.id })],
      instalments: [],
    });
    const markup = renderTable(document, "lipsă", plans.id);

    expect(markup).toContain("Planuri");
    expect(markup).not.toContain("La roșu");
    expect(markup).toContain("Niciun element din categoria Planuri nu corespunde filtrelor.");
  });

  it("uses rooms by default only for finish, move and Extra stages, while preserving category view", () => {
    const finish = makeGroup({ id: "finish", label: "La cheie", milestoneId: "la-cheie" });
    const interior = makeGroup({
      id: "finish-interior",
      label: "Finisaje interioare",
      milestoneId: "la-cheie",
      parentId: finish.id,
    });
    const document = makeDocument({
      groups: [finish, interior],
      items: [
        makeItem({
          id: "living-finish",
          label: "Pardoseală living",
          groupId: interior.id,
          milestoneId: "la-cheie",
          areaId: "G-LIV",
        }),
        makeItem({
          id: "whole-house-finish",
          label: "Sistem integrat",
          groupId: interior.id,
          milestoneId: "la-cheie",
          areaId: "whole-house",
        }),
        makeItem({
          id: "fallback-finish",
          label: "Element fără amplasare",
          groupId: interior.id,
          milestoneId: "la-cheie",
        }),
      ],
      instalments: [],
    });

    const rooms = renderTable(document, "", finish.id, "rooms");
    const categories = renderTable(document, "", finish.id, "categories");
    const earlierStage = renderTable(
      makeDocument({
        items: [makeItem({ areaId: "G-LIV" })],
        instalments: [],
      }),
      "",
      "constructie",
      "rooms",
    );

    expect(rooms).toContain("Pe camere");
    expect(rooms).toContain('aria-pressed="true"');
    expect(rooms).toContain("Întreaga casă");
    expect(rooms).toContain("Living și dining");
    expect(rooms).toContain("Amplasare de stabilit");
    expect(rooms).toContain("Subtotal în La cheie");
    expect(rooms).toContain("Totalurile pe camere acoperă doar etapa selectată.");
    expect(categories).toContain("Pe categorii");
    expect(categories).not.toContain("Subtotal în La cheie");
    expect(earlierStage).not.toContain("Pe camere");
    expect(earlierStage).not.toContain("Living și dining");
  });

  it("keeps room, category, item search and scope filters within matching room sections", () => {
    const finish = makeGroup({ id: "finish", label: "La cheie", milestoneId: "la-cheie" });
    const interior = makeGroup({
      id: "finish-interior",
      label: "Finisaje interioare",
      milestoneId: "la-cheie",
      parentId: finish.id,
    });
    const document = makeDocument({
      groups: [finish, interior],
      items: [
        makeItem({
          id: "living-floor",
          label: "Parchet",
          groupId: interior.id,
          milestoneId: "la-cheie",
          areaId: "G-LIV",
        }),
        makeItem({
          id: "kitchen-floor",
          label: "Gresie",
          groupId: interior.id,
          milestoneId: "la-cheie",
          areaId: "G-KIT",
          costScope: "movable",
        }),
      ],
      instalments: [],
    });

    const roomSearch = renderTable(document, "bucătărie", finish.id, "rooms");
    const categorySearch = renderTable(document, "finisaje", finish.id, "rooms");
    const itemSearch = renderTable(document, "parchet", finish.id, "rooms");
    const movableOnly = renderTable(document, "", finish.id, "rooms", { costScope: "movable" });

    expect(roomSearch).toContain("Gresie");
    expect(roomSearch).not.toContain("Parchet");
    expect(categorySearch).toContain("Parchet");
    expect(categorySearch).toContain("Gresie");
    expect(itemSearch).toContain("Parchet");
    expect(itemSearch).not.toContain("Gresie");
    expect(movableOnly).toContain("Gresie");
    expect(movableOnly).not.toContain("Parchet");
  });

  it("retains each item once with room totals, payment progress, and detail access", () => {
    const finish = makeGroup({ id: "finish", label: "La cheie", milestoneId: "la-cheie" });
    const document = makeDocument({
      groups: [finish],
      items: [
        makeItem({
          id: "living-payment",
          label: "Finisaj living",
          groupId: finish.id,
          milestoneId: "la-cheie",
          areaId: "G-LIV",
        }),
        makeItem({
          id: "kitchen-payment",
          label: "Finisaj bucătărie",
          groupId: finish.id,
          milestoneId: "la-cheie",
          areaId: "G-KIT",
        }),
      ],
      instalments: [
        makeInstalment({ itemId: "living-payment" }),
        makeInstalment({ id: "transa-bucatarie", itemId: "kitchen-payment" }),
      ],
      payments: [makePayment({ itemId: "living-payment", amountCents: 5_000 })],
    });
    const markup = renderTable(document, "", finish.id, "rooms");

    for (const itemId of ["living-payment", "kitchen-payment"]) {
      expect(markup.match(new RegExp(`data-budget-id="${itemId}"`, "g"))).toHaveLength(1);
      expect(rowById(markup, itemId)).toContain('aria-haspopup="dialog"');
    }
    expect(summaryById(markup, finish.id)).toContain('aria-valuenow="5000"');
    expect(areaSummaryById(markup, "area-g-liv")).toContain('aria-valuenow="5000"');
    expect(areaSummaryById(markup, "area-g-kit")).toContain("Neplătit");
    expect(areaSummaryById(markup, "area-g-kit")).not.toContain('role="progressbar"');
  });
});
