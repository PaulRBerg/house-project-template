import { Search, SlidersHorizontal } from "lucide-react";

import { AppButton } from "../shared/AppButton.js";
import { AppSelect } from "../shared/AppSelect.js";

export type ScopeFilter = "all" | "core" | "movable";
export type StatusFilter = "active" | "complete" | "overdue" | "excluded" | "archived" | "all";

interface ToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  scope: ScopeFilter;
  onScopeChange: (scope: ScopeFilter) => void;
  status: StatusFilter;
  onStatusChange: (status: StatusFilter) => void;
  onOpenAssumptions: () => void;
  disabled: boolean;
}

export function BudgetToolbar(props: ToolbarProps) {
  return (
    <section className="mt-8 flex items-center gap-2.5" aria-label="Instrumente și filtre">
      <label className="flex min-h-10.5 w-full max-w-80 items-center gap-2 rounded-[7px] border border-line bg-surface px-3 py-0 focus-within:border-olive">
        <Search className="flex-none text-muted" aria-hidden="true" size={17} />
        <span className="sr-only">Caută în categoria selectată</span>
        <input
          className="w-full min-w-0 cursor-text border-0 bg-transparent px-0.5 py-px text-[0.76rem] outline-0"
          name="budget-search"
          onChange={(event) => props.onSearchChange(event.target.value)}
          placeholder="Caută în categoria selectată…"
          type="search"
          value={props.search}
        />
      </label>
      <AppSelect
        className="min-w-35"
        label="Tip de cost"
        name="budget-scope"
        onValueChange={props.onScopeChange}
        options={[
          { value: "all", label: "Casă + bunuri" },
          { value: "core", label: "Buget de bază" },
          { value: "movable", label: "Bunuri mobile" },
        ]}
        value={props.scope}
      />
      <AppSelect
        className="min-w-35"
        label="Stare"
        name="budget-status"
        onValueChange={props.onStatusChange}
        options={[
          { value: "active", label: "Active" },
          { value: "complete", label: "Gata" },
          { value: "overdue", label: "Întârziate" },
          { value: "excluded", label: "Opționale neincluse" },
          { value: "archived", label: "Arhivate" },
          { value: "all", label: "Toate stările" },
        ]}
        value={props.status}
      />
      <p className="ml-auto text-[0.7rem] whitespace-nowrap text-muted">
        Totalurile de sus acoperă tot proiectul.
      </p>
      <AppButton disabled={props.disabled} onClick={props.onOpenAssumptions} type="button">
        <SlidersHorizontal aria-hidden="true" size={16} /> Ipoteze
      </AppButton>
    </section>
  );
}
