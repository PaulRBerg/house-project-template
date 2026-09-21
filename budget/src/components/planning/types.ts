import type { BudgetDocument, Milestone } from "../../domain/schema.js";
import type { BudgetView } from "../../domain/selectors.js";

export interface PlanningViewProps {
  document: BudgetDocument;
  view: BudgetView;
  onOpenItem: (itemId: string) => void;
  milestoneId?: Milestone["id"] | "all";
}
