import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { selectBudgetView } from "../../domain/index.js";
import { makeDocument, makeGroup, makeInstalment, makeItem } from "../../domain/test-fixtures.js";
import { render, screen, waitFor } from "../../test/render.js";
import { BudgetTable } from "./BudgetTable.js";

const filters = { scope: "all", search: "", status: "all" } as const;

function tableDocument() {
  const professional = makeGroup({ id: "professional", label: "Profesional", sortOrder: 0 });
  const construction = makeGroup({ id: "construction", label: "Construcție", sortOrder: 1 });
  const structure = makeGroup({ id: "structure", label: "Structură", parentId: construction.id });
  const item = makeItem({ id: "foundation", label: "Fundație", groupId: structure.id });
  return makeDocument({
    groups: [professional, construction, structure],
    items: [item],
    instalments: [makeInstalment({ itemId: item.id })],
  });
}

function roomGroupingDocument() {
  const finish = makeGroup({
    id: "finish",
    label: "Finisaje",
    milestoneId: "la-cheie",
    sortOrder: 0,
  });
  const bedroom = makeGroup({
    id: "bedroom-finish",
    label: "Dormitor",
    milestoneId: "la-cheie",
    parentId: finish.id,
  });
  const item = makeItem({
    areaId: "bedroom",
    groupId: bedroom.id,
    id: "bedroom-floor",
    label: "Parchet dormitor",
    milestoneId: "la-cheie",
  });
  return makeDocument({
    groups: [finish, bedroom],
    instalments: [makeInstalment({ itemId: item.id })],
    items: [item],
  });
}

it("renders ownership and completion as separate readable states", () => {
  const owned = makeItem({
    id: "owned-device",
    label: "Owned device",
    ownership: "owned",
    completion: { complete: true },
  });
  const complete = makeItem({
    id: "complete",
    label: "Lucrare finalizată",
    completion: { complete: true },
  });
  const planned = makeItem({ id: "planned", label: "Lucrare planificată" });
  const view = selectBudgetView(
    makeDocument({
      items: [owned, complete, planned],
      instalments: [
        makeInstalment({ itemId: owned.id }),
        makeInstalment({ id: "complete-ins", itemId: complete.id }),
        makeInstalment({ id: "planned-ins", itemId: planned.id }),
      ],
    }),
    { asOf: "2026-09-19", scenario: "base" },
  );
  render(
    <BudgetTable
      filters={filters}
      grouping="categories"
      hierarchy={view.hierarchy}
      onGroupingChange={vi.fn()}
      onOpenItem={vi.fn()}
      selectedCategory="constructie"
    />,
  );

  expect(screen.getByRole("row", { name: /Owned device/ })).toHaveTextContent("Deja cumpărat");
  expect(screen.getByRole("row", { name: /Lucrare finalizată/ })).toHaveTextContent("Finalizat");
  expect(screen.getByRole("row", { name: /Lucrare planificată/ })).toHaveTextContent("Planificat");
});

function renderTable(
  selectedCategory = "construction",
  search = "",
  onGroupingChange = vi.fn(),
  onOpenItem = vi.fn(),
) {
  const view = selectBudgetView(tableDocument(), { asOf: "2026-09-19", scenario: "base" });
  return {
    ...render(
      <BudgetTable
        filters={{ ...filters, search }}
        grouping="categories"
        hierarchy={view.hierarchy}
        onGroupingChange={onGroupingChange}
        onOpenItem={onOpenItem}
        selectedCategory={selectedCategory}
      />,
    ),
    view,
  };
}

describe("BudgetTable interactions", () => {
  it("collapses groups, but search reveals a matching item", async () => {
    const { user, rerender } = renderTable();
    await user.click(screen.getByRole("button", { name: "Restrânge Structură" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Fundație" })).not.toBeInTheDocument(),
    );

    rerender(
      <BudgetTable
        filters={{ ...filters, search: "Fundație" }}
        grouping="categories"
        hierarchy={
          selectBudgetView(tableDocument(), { asOf: "2026-09-19", scenario: "base" }).hierarchy
        }
        onGroupingChange={vi.fn()}
        onOpenItem={vi.fn()}
        selectedCategory="construction"
      />,
    );
    expect(await screen.findByRole("button", { name: "Fundație" })).toBeVisible();
  });

  it("resets collapsed expansion when re-entering a category and opens item details", async () => {
    const onOpenItem = vi.fn();
    const { user, rerender, view } = renderTable("construction", "", vi.fn(), onOpenItem);
    await user.click(screen.getByRole("button", { name: "Restrânge Structură" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Fundație" })).not.toBeInTheDocument(),
    );

    rerender(
      <BudgetTable
        {...{
          filters,
          grouping: "categories" as const,
          hierarchy: view.hierarchy,
          onGroupingChange: vi.fn(),
          onOpenItem,
          selectedCategory: "professional",
        }}
      />,
    );
    rerender(
      <BudgetTable
        {...{
          filters,
          grouping: "categories" as const,
          hierarchy: view.hierarchy,
          onGroupingChange: vi.fn(),
          onOpenItem,
          selectedCategory: "construction",
        }}
      />,
    );
    await user.click(await screen.findByRole("button", { name: "Fundație" }));
    expect(onOpenItem).toHaveBeenCalledWith("foundation");
  });

  it("resets collapsed expansion when entering room grouping", async () => {
    const view = selectBudgetView(roomGroupingDocument(), { asOf: "2026-09-19", scenario: "base" });
    const { rerender, user } = render(
      <BudgetTable
        filters={filters}
        grouping="categories"
        hierarchy={view.hierarchy}
        onGroupingChange={vi.fn()}
        onOpenItem={vi.fn()}
        selectedCategory="finish"
      />,
    );
    await user.click(screen.getByRole("button", { name: "Restrânge Dormitor" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Parchet dormitor" })).not.toBeInTheDocument(),
    );

    rerender(
      <BudgetTable
        filters={filters}
        grouping="rooms"
        hierarchy={view.hierarchy}
        onGroupingChange={vi.fn()}
        onOpenItem={vi.fn()}
        selectedCategory="finish"
      />,
    );
    expect(await screen.findByRole("button", { name: "Parchet dormitor" })).toBeVisible();
  });

  it("keeps one room grouping selected for click and keyboard controls", async () => {
    const onGroupingChange = vi.fn();
    const view = selectBudgetView(roomGroupingDocument(), { asOf: "2026-09-19", scenario: "base" });
    function ControlledTable() {
      const [grouping, setGrouping] = useState<"rooms" | "categories">("categories");
      return (
        <BudgetTable
          filters={filters}
          grouping={grouping}
          hierarchy={view.hierarchy}
          onGroupingChange={(nextGrouping) => {
            onGroupingChange(nextGrouping);
            setGrouping(nextGrouping);
          }}
          onOpenItem={vi.fn()}
          selectedCategory="finish"
        />
      );
    }
    const { user } = render(<ControlledTable />);
    const rooms = screen.getByRole("button", { name: "Pe camere" });
    const categories = screen.getByRole("button", { name: "Pe categorii" });

    expect(categories).toHaveAttribute("aria-pressed", "true");
    await user.click(rooms);
    expect(rooms).toHaveAttribute("aria-pressed", "true");
    expect(onGroupingChange).toHaveBeenLastCalledWith("rooms");

    await user.click(rooms);
    expect(rooms).toHaveAttribute("aria-pressed", "true");
    expect(onGroupingChange).toHaveBeenCalledTimes(1);

    rooms.focus();
    await user.keyboard("{ArrowRight}{Enter}");
    expect(document.activeElement).toBe(categories);
    expect(categories).toHaveAttribute("aria-pressed", "true");
    expect(onGroupingChange).toHaveBeenLastCalledWith("categories");
  });
});
