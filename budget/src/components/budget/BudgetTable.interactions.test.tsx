import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { TBD_BENEFICIARY_ID } from "../../domain/index.js";
import { budgetTableProps } from "../../test/budget-table.js";
import {
  makeBeneficiary,
  makeDocument,
  makeGroup,
  makeInstalment,
  makeItem,
} from "../../test/builders.js";
import { render, screen, waitFor } from "../../test/render.js";
import { BudgetTable } from "./BudgetTable.js";
import type { BudgetGrouping } from "./categories.js";

const filters = { costScope: "all", search: "", status: "all" } as const;

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
    areaId: "U-MBED",
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

it("marks owned rows by design only, without status badges", () => {
  const owned = makeItem({
    id: "asset-apple-tv",
    label: "Media player",
    ownership: "owned",
    completion: { complete: true },
  });
  const complete = makeItem({
    id: "complete",
    label: "Lucrare finalizată",
    completion: { complete: true },
  });
  const planned = makeItem({ id: "planned", label: "Lucrare planificată" });
  const document = makeDocument({
    items: [owned, complete, planned],
    instalments: [
      makeInstalment({ itemId: owned.id }),
      makeInstalment({ id: "complete-ins", itemId: complete.id }),
      makeInstalment({ id: "planned-ins", itemId: planned.id }),
    ],
  });
  render(<BudgetTable {...budgetTableProps(document, { grouping: "categories" })} />);

  const ownedRow = screen.getByRole("row", { name: /Media player/ });
  expect(ownedRow).toHaveClass("border-l-olive");
  expect(ownedRow).not.toHaveTextContent("Deja cumpărat");
  expect(screen.getByRole("row", { name: /Lucrare finalizată/ })).not.toHaveTextContent(
    "Finalizat",
  );
  expect(screen.getByRole("row", { name: /Lucrare planificată/ })).not.toHaveTextContent(
    "Planificat",
  );
});

function renderTable(
  selectedCategory = "construction",
  search = "",
  onGroupingChange = vi.fn(),
  onOpenItem = vi.fn(),
) {
  const props = budgetTableProps(tableDocument(), {
    filters: { ...filters, search },
    grouping: "categories",
    onGroupingChange,
    onOpenBeneficiary: vi.fn(),
    onOpenItem,
    selectedCategory,
  });
  return { ...render(<BudgetTable {...props} />), props };
}

describe("BudgetTable interactions", () => {
  it("collapses groups, but search reveals a matching item", async () => {
    const { user, rerender, props } = renderTable();
    await user.click(screen.getByRole("button", { name: "Restrânge Structură" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Fundație" })).not.toBeInTheDocument(),
    );

    rerender(<BudgetTable {...props} filters={{ ...filters, search: "Fundație" }} />);
    expect(await screen.findByRole("button", { name: "Fundație" })).toBeVisible();
  });

  it("ignores collapse clicks while a search keeps groups open", async () => {
    const { user, rerender, props } = renderTable("construction", "Fundație");
    expect(screen.getByRole("button", { name: "Restrânge Structură" })).toBeDisabled();
    await user.click(screen.getByRole("row", { name: /Structură/ }));

    rerender(<BudgetTable {...props} filters={filters} />);
    expect(await screen.findByRole("button", { name: "Fundație" })).toBeVisible();
  });

  it("resets collapsed expansion when re-entering a category and opens item details", async () => {
    const onOpenItem = vi.fn();
    const { user, rerender, props } = renderTable("construction", "", vi.fn(), onOpenItem);
    await user.click(screen.getByRole("button", { name: "Restrânge Structură" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Fundație" })).not.toBeInTheDocument(),
    );

    rerender(<BudgetTable {...props} selectedCategory="professional" />);
    rerender(<BudgetTable {...props} selectedCategory="construction" />);
    await user.click(await screen.findByRole("button", { name: "Fundație" }));
    expect(onOpenItem).toHaveBeenCalledWith("foundation");
  });

  it("resets collapsed expansion when entering room grouping", async () => {
    const props = budgetTableProps(roomGroupingDocument(), {
      grouping: "categories",
      selectedCategory: "finish",
    });
    const { rerender, user } = render(<BudgetTable {...props} />);
    await user.click(screen.getByRole("button", { name: "Restrânge Dormitor" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Parchet dormitor" })).not.toBeInTheDocument(),
    );

    rerender(<BudgetTable {...props} grouping="rooms" />);
    expect(await screen.findByRole("button", { name: "Parchet dormitor" })).toBeVisible();
  });

  it("keeps one room grouping selected for click and keyboard controls", async () => {
    const onGroupingChange = vi.fn();
    const props = budgetTableProps(roomGroupingDocument(), { selectedCategory: "finish" });
    function ControlledTable() {
      const [grouping, setGrouping] = useState<BudgetGrouping>("categories");
      return (
        <BudgetTable
          {...props}
          grouping={grouping}
          onGroupingChange={(nextGrouping) => {
            onGroupingChange(nextGrouping);
            setGrouping(nextGrouping);
          }}
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

  it("shows each item's beneficiary and routes clicks to onOpenBeneficiary, not onOpenItem", async () => {
    const beneficiary = makeBeneficiary();
    const assigned = makeItem({
      id: "assigned-item",
      label: "Structură",
      beneficiaryId: beneficiary.id,
    });
    const unassigned = makeItem({ id: "unassigned-item", label: "Instalații" });
    const doc = makeDocument({
      beneficiaries: [beneficiary],
      items: [assigned, unassigned],
      instalments: [
        makeInstalment({ itemId: assigned.id }),
        makeInstalment({ id: "instalment-unassigned", itemId: unassigned.id }),
      ],
    });
    const onOpenBeneficiary = vi.fn();
    const onOpenItem = vi.fn();
    const { user } = render(
      <BudgetTable
        {...budgetTableProps(doc, { grouping: "categories", onOpenBeneficiary, onOpenItem })}
      />,
    );

    expect(screen.getByRole("row", { name: /Structură/ })).toHaveTextContent("Constructor Exemplu");
    expect(screen.getByRole("row", { name: /Instalații/ })).toHaveTextContent("TBD");

    await user.click(screen.getByRole("button", { name: "Beneficiar: Constructor Exemplu" }));
    expect(onOpenBeneficiary).toHaveBeenCalledWith(beneficiary.id);

    await user.click(screen.getByRole("button", { name: "Beneficiar: TBD" }));
    expect(onOpenBeneficiary).toHaveBeenCalledWith(TBD_BENEFICIARY_ID);

    expect(onOpenItem).not.toHaveBeenCalled();
  });
});
