import type { ComponentProps } from "react";

import type { BudgetTable } from "../components/budget/BudgetTable.js";
import type { BudgetDocument } from "../domain/schema.js";
import { selectBudgetView } from "../domain/selectors.js";

type BudgetTableProps = ComponentProps<typeof BudgetTable>;

/** BudgetTable props over a document's full hierarchy, with no-op callbacks and no filters. */
export function budgetTableProps(
  document: BudgetDocument,
  overrides: Partial<BudgetTableProps> = {},
): BudgetTableProps {
  const view = selectBudgetView(document, { asOf: "2026-09-19" });
  return {
    beneficiaries: document.beneficiaries,
    filters: { search: "", costScope: "all", status: "all" },
    grouping: "rooms",
    hierarchy: view.hierarchy,
    onGroupingChange: () => undefined,
    onOpenBeneficiary: () => undefined,
    onOpenItem: () => undefined,
    selectedCategory: "constructie",
    ...overrides,
  };
}
