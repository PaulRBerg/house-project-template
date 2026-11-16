import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { ArchiveRestore, ChevronDown, TriangleAlert } from "lucide-react";
import { type MouseEvent, useMemo, useRef, useState } from "react";

import {
  beneficiaryName,
  beneficiaryNamesById,
  getBudgetAreaHierarchy,
  TBD_BENEFICIARY_ID,
  type Beneficiary,
  type BudgetHierarchyGroup,
  type BudgetHierarchyItem,
  type DerivedItem,
} from "../../domain/index.js";
import {
  formatCount,
  formatDateRange,
  formatItemCost,
  formatMoneyRange,
  labelMatches,
  normalizeSearch,
} from "../../ui/format.js";
import { CategoryIcon } from "../shared/CategoryIcon.js";
import { ItemBrandIcon, ItemIcon } from "../shared/ItemIcon.js";
import { PaymentProgress } from "../shared/PaymentProgress.js";
import {
  BUDGET_TABLE_COLUMNS,
  cn,
  emptyStatePanelStyles,
  emptyStateStyles,
  eyebrowStyles,
  iconButtonStyles,
  linkButtonStyles,
  moneyCellStyles,
  segmentedGroupStyles,
  segmentedToggleStyles,
  tableCellStyles,
  tableHeaderStyles,
  tableScrollerStyles,
} from "../shared/styles.js";
import { AnimatedBudgetRow, AnimatedCellContent } from "./AnimatedBudgetRow.js";
import type { CostScopeFilter, StatusFilter } from "./BudgetToolbar.js";
import { BUDGET_GROUPINGS, supportsRoomGrouping, type BudgetGrouping } from "./categories.js";

interface Filters {
  search: string;
  costScope: CostScopeFilter;
  status: StatusFilter;
}

/** Filters with the search text normalized once per render. */
interface MatchFilters extends Filters {
  query: string;
}

type HierarchyChild = BudgetHierarchyGroup | BudgetHierarchyItem;

interface GroupVisibility {
  visible: boolean;
  itemCount: number;
}

interface BudgetTableProps {
  hierarchy: BudgetHierarchyGroup[];
  filters: Filters;
  grouping: BudgetGrouping;
  /** Stage root resolved by the caller; null only when the hierarchy is empty. */
  selectedCategory: string | null;
  beneficiaries: readonly Beneficiary[];
  onGroupingChange: (grouping: BudgetGrouping) => void;
  onOpenItem: (itemId: string) => void;
  onOpenBeneficiary: (beneficiaryId: string) => void;
}

const GROUPING_LABELS: Record<BudgetGrouping, string> = {
  rooms: "Pe camere",
  categories: "Pe categorii",
};

/** Each hierarchy level shifts its leading icon by one step. */
const TREE_INDENT_PX = 16;
/** Chevron button width (36px) plus its gap, so items indent past the parent band's gutter. */
const CHEVRON_GUTTER_PX = 43;

function isTextSelectionClick(event: MouseEvent<HTMLElement>): boolean {
  const selection = event.currentTarget.ownerDocument.getSelection();
  return (
    event.detail > 0 && !!selection?.toString() && selection.containsNode(event.currentTarget, true)
  );
}

/** Row click that activates the row, ignoring text selection and clicks on its own buttons. */
function handleRowClick(event: MouseEvent<HTMLElement>, activate: () => void): void {
  if (isTextSelectionClick(event)) return;
  if (event.target instanceof Element && event.target.closest("button")) return;
  activate();
}

function itemMatches(entry: DerivedItem, filters: MatchFilters, searchMatched = false): boolean {
  if (filters.costScope !== "all" && entry.item.costScope !== filters.costScope) return false;
  if (!searchMatched && filters.query && !labelMatches(entry.item.label, filters.query)) {
    return false;
  }
  if (filters.status === "active" && !entry.active) return false;
  if (filters.status === "complete" && !entry.item.completion.complete) return false;
  if (filters.status === "overdue" && entry.overdueCents === 0) return false;
  if (filters.status === "excluded" && (entry.item.included || entry.effectivelyArchived))
    return false;
  if (filters.status === "archived" && !entry.effectivelyArchived) return false;
  return true;
}

/**
 * Records whether each group in a subtree has matching content and how many items it shows,
 * visiting every node once.
 */
function collectVisibility(
  group: BudgetHierarchyGroup,
  filters: MatchFilters,
  ancestorMatched: boolean,
  into: Map<string, GroupVisibility>,
): GroupVisibility {
  const groupMatched = ancestorMatched || labelMatches(group.label, filters.query);
  let visibility: GroupVisibility;
  if (group.children.length === 0) {
    const searchMatches = !filters.query || groupMatched;
    const statusMatches =
      filters.status === "all" ||
      (filters.status === "active" && !group.archived) ||
      (filters.status === "archived" && group.archived);
    visibility = {
      visible: filters.costScope === "all" && searchMatches && statusMatches,
      itemCount: 0,
    };
  } else {
    visibility = { visible: false, itemCount: 0 };
    for (const child of group.children) {
      const childVisibility =
        child.kind === "item"
          ? itemMatches(child.derived, filters, groupMatched)
            ? { visible: true, itemCount: 1 }
            : undefined
          : collectVisibility(child, filters, groupMatched, into);
      if (!childVisibility) continue;
      visibility.visible ||= childVisibility.visible;
      visibility.itemCount += childVisibility.itemCount;
    }
  }
  into.set(group.id, visibility);
  return visibility;
}

/** Visible direct children plus the visibility of every nested group. */
function visibleChildren(
  children: readonly HierarchyChild[],
  filters: MatchFilters,
  searchMatched: boolean,
): { children: HierarchyChild[]; visibility: Map<string, GroupVisibility> } {
  const visibility = new Map<string, GroupVisibility>();
  return {
    children: children.filter((child) =>
      child.kind === "group"
        ? collectVisibility(child, filters, searchMatched, visibility).visible
        : itemMatches(child.derived, filters, searchMatched),
    ),
    visibility,
  };
}

function ItemRow({
  child,
  depth,
  open,
  ancestors,
  onOpen,
  beneficiaryNames,
  onOpenBeneficiary,
}: {
  child: BudgetHierarchyItem;
  depth: number;
  open: boolean;
  ancestors: string[];
  onOpen: () => void;
  beneficiaryNames: ReadonlyMap<string, string>;
  onOpenBeneficiary: (beneficiaryId: string) => void;
}) {
  const entry = child.derived;
  const beneficiaryId = entry.item.beneficiaryId ?? TBD_BENEFICIARY_ID;
  const payee = beneficiaryName(entry.item, beneficiaryNames);

  return (
    <AnimatedBudgetRow
      data-budget-ancestors={ancestors.join(" ")}
      data-budget-id={child.id}
      data-budget-row="item"
      open={open}
      className={cn(
        "cursor-pointer border-t border-line hover:bg-canvas/55",
        entry.item.ownership === "owned" && "border-l-2 border-l-olive",
        entry.effectivelyArchived && "opacity-58",
      )}
      onClick={(event) => {
        const row = event.currentTarget;
        handleRowClick(event, () => {
          row.querySelector("button")?.focus();
          onOpen();
        });
      }}
    >
      {(phase, animationRef) => (
        <>
          <th className={cn(tableCellStyles, "font-normal")} scope="row">
            <AnimatedCellContent phase={phase} ref={animationRef}>
              <div
                className="flex items-center gap-2"
                style={{ paddingInlineStart: `${depth * TREE_INDENT_PX + CHEVRON_GUTTER_PX}px` }}
              >
                <ItemIcon itemId={entry.item.id} />
                <button
                  aria-haspopup="dialog"
                  className="flex min-h-11 w-full min-w-0 flex-1 cursor-pointer flex-col items-start justify-center border-0 bg-transparent px-1.5 py-1 text-left select-text"
                  onClick={(event) => {
                    if (!isTextSelectionClick(event)) onOpen();
                  }}
                  type="button"
                >
                  <span className="flex items-center gap-1.5 text-[0.84rem] font-[680]">
                    {entry.item.label}
                    <ItemBrandIcon itemId={entry.item.id} />
                  </span>
                </button>
              </div>
            </AnimatedCellContent>
          </th>
          <td className={tableCellStyles}>
            <AnimatedCellContent phase={phase}>
              <button
                aria-label={`Beneficiar: ${payee}`}
                className={cn(
                  linkButtonStyles,
                  "text-[0.78rem] font-medium focus-visible:outline-accent",
                  entry.item.beneficiaryId === undefined && "text-muted",
                )}
                onClick={() => onOpenBeneficiary(beneficiaryId)}
                type="button"
              >
                {payee}
              </button>
            </AnimatedCellContent>
          </td>
          <td className={cn(tableCellStyles, moneyCellStyles, "text-right")}>
            <AnimatedCellContent phase={phase}>
              <strong>{formatItemCost(entry)}</strong>
              {entry.discrepancy.kind !== "balanced" && (
                <small className="text-accent!">
                  <TriangleAlert aria-hidden="true" size={12} />
                  {entry.discrepancy.kind === "unallocated"
                    ? "sumă nealocată"
                    : "plan peste estimare"}
                </small>
              )}
            </AnimatedCellContent>
          </td>
          <td className={tableCellStyles}>
            <AnimatedCellContent phase={phase}>
              {entry.item.paymentMode === "partial-progress" && (
                <PaymentProgress
                  label={entry.item.label}
                  totalCents={entry.totalCents}
                  settledCents={entry.settledCents}
                />
              )}
            </AnimatedCellContent>
          </td>
          <td className={cn(tableCellStyles, "text-[0.72rem]")}>
            <AnimatedCellContent phase={phase}>
              {formatDateRange(entry.scheduleStartOn, entry.scheduleFinalOn)}
            </AnimatedCellContent>
          </td>
        </>
      )}
    </AnimatedBudgetRow>
  );
}

function GroupRows({
  group,
  filters,
  visibility,
  depth,
  open,
  ancestors,
  onOpenItem,
  beneficiaryNames,
  onOpenBeneficiary,
  ancestorMatched,
}: {
  group: BudgetHierarchyGroup;
  filters: MatchFilters;
  visibility: ReadonlyMap<string, GroupVisibility>;
  depth: number;
  open: boolean;
  ancestors: string[];
  onOpenItem: (itemId: string) => void;
  beneficiaryNames: ReadonlyMap<string, string>;
  onOpenBeneficiary: (beneficiaryId: string) => void;
  ancestorMatched: boolean;
}) {
  const groupMatched = ancestorMatched || labelMatches(group.label, filters.query);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [expanded, setExpanded] = useState(true);
  const { visible, itemCount: visibleItemCount } = visibility.get(group.id) ?? {
    visible: false,
    itemCount: 0,
  };
  if (!visible) return null;
  const isExpanded = filters.query !== "" || expanded;
  const contentOpen = open && isExpanded;

  const toggle = () => {
    if (filters.query !== "") return;
    const focusedRow = document.activeElement?.closest<HTMLTableRowElement>("tr[data-budget-row]");
    if (isExpanded && focusedRow?.dataset.budgetAncestors?.split(" ").includes(group.id)) {
      triggerRef.current?.focus();
    }
    setExpanded((current) => !current);
  };

  return (
    <>
      <AnimatedBudgetRow
        data-budget-ancestors={ancestors.join(" ")}
        data-budget-id={group.id}
        data-budget-row="group"
        open={open}
        className={cn(
          "cursor-pointer border-t border-line hover:bg-stage-tint",
          depth === 0 ? "bg-stage-tint/50" : "bg-stage-tint/25",
        )}
        onClick={(event) => handleRowClick(event, toggle)}
      >
        {(phase, animationRef) => (
          <>
            <th className={cn(tableCellStyles, "font-normal")} scope="row">
              <AnimatedCellContent className="py-2" phase={phase} ref={animationRef}>
                <div
                  className="flex items-center gap-1.75"
                  style={{ paddingInlineStart: `${depth * TREE_INDENT_PX}px` }}
                >
                  <button
                    ref={triggerRef}
                    aria-expanded={isExpanded}
                    aria-label={`${isExpanded ? "Restrânge" : "Extinde"} ${group.label}`}
                    className={iconButtonStyles}
                    disabled={filters.query !== ""}
                    onClick={toggle}
                    type="button"
                  >
                    <ChevronDown
                      aria-hidden="true"
                      className={
                        isExpanded
                          ? "transition-transform duration-160 ease-[ease]"
                          : "-rotate-90 transition-transform duration-160 ease-[ease]"
                      }
                      size={17}
                    />
                  </button>
                  <CategoryIcon categoryId={group.sourceGroupId ?? group.id} />
                  <span className={cn(eyebrowStyles, "mb-0 text-ink")}>{group.label}</span>
                  {visibleItemCount > 0 && (
                    <span className="text-[0.68rem] text-muted tabular-nums">
                      {formatCount(visibleItemCount, { one: "element", other: "elemente" })}
                    </span>
                  )}
                  {group.archived && <ArchivedIcon />}
                </div>
              </AnimatedCellContent>
            </th>
            <td className={tableCellStyles} />
            <td
              className={cn(
                tableCellStyles,
                moneyCellStyles,
                "text-right [&_strong]:font-semibold",
              )}
            >
              <AnimatedCellContent className="py-2" phase={phase}>
                <strong>{formatMoneyRange(group.estimateCents, group.totalCents)}</strong>
              </AnimatedCellContent>
            </td>
            <td className={tableCellStyles}>
              <AnimatedCellContent className="py-2" phase={phase}>
                <PaymentProgress
                  label={group.label}
                  totalCents={group.totalCents}
                  settledCents={group.settledCents}
                />
              </AnimatedCellContent>
            </td>
            <td className={cn(tableCellStyles, "text-[0.72rem]")}>
              <AnimatedCellContent className="py-2" phase={phase}>
                {formatDateRange(group.scheduleStartOn, group.scheduleFinalOn)}
              </AnimatedCellContent>
            </td>
          </>
        )}
      </AnimatedBudgetRow>
      {group.children.map((child) =>
        child.kind === "group" ? (
          <GroupRows
            ancestorMatched={groupMatched}
            ancestors={[...ancestors, group.id]}
            beneficiaryNames={beneficiaryNames}
            depth={depth + 1}
            filters={filters}
            group={child}
            key={child.id}
            onOpenBeneficiary={onOpenBeneficiary}
            onOpenItem={onOpenItem}
            open={contentOpen}
            visibility={visibility}
          />
        ) : itemMatches(child.derived, filters, groupMatched) ? (
          <ItemRow
            ancestors={[...ancestors, group.id]}
            beneficiaryNames={beneficiaryNames}
            child={child}
            depth={depth + 1}
            key={child.id}
            onOpen={() => onOpenItem(child.id)}
            onOpenBeneficiary={onOpenBeneficiary}
            open={contentOpen}
          />
        ) : null,
      )}
    </>
  );
}

function ArchivedIcon() {
  return <ArchiveRestore aria-label="Categorie arhivată" size={14} />;
}

function CategorySummary({ group }: { group: BudgetHierarchyGroup }) {
  return (
    <div
      className="mb-2.5 grid grid-cols-[minmax(0,1.25fr)_minmax(110px,0.55fr)_minmax(120px,0.65fr)_minmax(180px,0.9fr)_minmax(130px,0.7fr)] items-center gap-4 rounded-xl border border-stage/24 bg-stage-header px-4 py-3"
      data-budget-summary={group.id}
      data-stage={group.milestoneId}
    >
      <div className="flex min-w-0 items-center gap-2 text-[0.83rem] font-[760]">
        <CategoryIcon categoryId={group.id} size={18} />
        <span>{group.label}</span>
        {group.archived && <ArchivedIcon />}
      </div>
      <span aria-hidden="true" />
      <strong className="text-right text-[0.88rem] tabular-nums">
        {formatMoneyRange(group.estimateCents, group.totalCents)}
      </strong>
      <PaymentProgress
        label={group.label}
        settledCents={group.settledCents}
        totalCents={group.totalCents}
      />
      <span className="text-[0.72rem] text-muted">
        {formatDateRange(group.scheduleStartOn, group.scheduleFinalOn)}
      </span>
    </div>
  );
}

function GroupTable({
  ancestors,
  children,
  emptyMessage,
  filters,
  onOpenItem,
  beneficiaryNames,
  onOpenBeneficiary,
  searchMatched,
  tableKey,
}: {
  ancestors: string[];
  children: readonly HierarchyChild[];
  emptyMessage: string;
  filters: MatchFilters;
  onOpenItem: (itemId: string) => void;
  beneficiaryNames: ReadonlyMap<string, string>;
  onOpenBeneficiary: (beneficiaryId: string) => void;
  searchMatched: boolean;
  tableKey: string;
}) {
  const visible = visibleChildren(children, filters, searchMatched);
  return (
    <div
      aria-label="Tabel de buget derulabil pe orizontală"
      role="region"
      className={tableScrollerStyles}
      tabIndex={0}
    >
      <table className="w-full min-w-225 table-fixed border-collapse">
        <thead>
          <tr>
            <th className={tableHeaderStyles}>Element</th>
            <th className={cn(tableHeaderStyles, BUDGET_TABLE_COLUMNS.beneficiary)}>Beneficiar</th>
            <th className={cn(tableHeaderStyles, BUDGET_TABLE_COLUMNS.cost, "text-right")}>Cost</th>
            <th className={cn(tableHeaderStyles, BUDGET_TABLE_COLUMNS.payments)}>Plăți</th>
            <th className={cn(tableHeaderStyles, BUDGET_TABLE_COLUMNS.schedule)}>Calendar</th>
          </tr>
        </thead>
        <tbody key={tableKey}>
          {visible.children.map((child) =>
            child.kind === "group" ? (
              <GroupRows
                ancestorMatched={searchMatched}
                ancestors={ancestors}
                beneficiaryNames={beneficiaryNames}
                depth={0}
                filters={filters}
                group={child}
                key={child.id}
                onOpenBeneficiary={onOpenBeneficiary}
                onOpenItem={onOpenItem}
                open
                visibility={visible.visibility}
              />
            ) : (
              <ItemRow
                ancestors={ancestors}
                beneficiaryNames={beneficiaryNames}
                child={child}
                depth={0}
                key={child.id}
                onOpen={() => onOpenItem(child.id)}
                onOpenBeneficiary={onOpenBeneficiary}
                open
              />
            ),
          )}
          {visible.children.length === 0 && (
            <tr className="border-t border-line">
              <td className={emptyStateStyles} colSpan={5}>
                {emptyMessage}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function AreaSection({
  ancestorMatched,
  area,
  filters,
  onOpenItem,
  beneficiaryNames,
  onOpenBeneficiary,
  stageLabel,
}: {
  ancestorMatched: boolean;
  area: BudgetHierarchyGroup;
  filters: MatchFilters;
  onOpenItem: (itemId: string) => void;
  beneficiaryNames: ReadonlyMap<string, string>;
  onOpenBeneficiary: (beneficiaryId: string) => void;
  stageLabel: string;
}) {
  const searchMatched = ancestorMatched || labelMatches(area.label, filters.query);
  const headingId = `budget-area-heading-${area.id}`;

  return (
    <section aria-labelledby={headingId} className="mt-5 first:mt-0">
      <div
        className={cn("mx-px mb-2 grid items-center", BUDGET_TABLE_COLUMNS.areaGrid)}
        data-budget-area-summary={area.id}
      >
        <div className="min-w-0 px-3.5">
          <h2 className="text-[0.86rem] font-[780]" id={headingId}>
            {area.label}
          </h2>
          <p className="text-[0.67rem] text-muted">Subtotal în {stageLabel}</p>
        </div>
        <span aria-hidden="true" />
        <strong className="px-3.5 text-right text-[0.84rem] tabular-nums">
          {formatMoneyRange(area.estimateCents, area.totalCents)}
        </strong>
        <div className="px-3.5">
          <PaymentProgress
            label={`${area.label}, ${stageLabel}`}
            settledCents={area.settledCents}
            totalCents={area.totalCents}
          />
        </div>
        <span className="px-3.5 text-[0.72rem] text-muted">
          {formatDateRange(area.scheduleStartOn, area.scheduleFinalOn)}
        </span>
      </div>
      <GroupTable
        ancestors={[area.id]}
        beneficiaryNames={beneficiaryNames}
        children={area.children}
        emptyMessage={`Niciun element din zona ${area.label} nu corespunde filtrelor.`}
        filters={filters}
        onOpenBeneficiary={onOpenBeneficiary}
        onOpenItem={onOpenItem}
        searchMatched={searchMatched}
        tableKey={area.id}
      />
    </section>
  );
}

export function BudgetTable(props: BudgetTableProps) {
  const beneficiaryNames = useMemo(
    () => beneficiaryNamesById(props.beneficiaries),
    [props.beneficiaries],
  );
  const filters = useMemo(
    () => ({ ...props.filters, query: normalizeSearch(props.filters.search) }),
    [props.filters],
  );
  const selectedRoot = props.hierarchy.find((group) => group.id === props.selectedCategory);
  const rootSearchMatched = Boolean(
    selectedRoot && labelMatches(selectedRoot.label, filters.query),
  );
  const roomGrouping = Boolean(selectedRoot && supportsRoomGrouping(selectedRoot.id));
  const grouping = roomGrouping ? props.grouping : "categories";
  const areas = useMemo(
    () => (roomGrouping && selectedRoot ? getBudgetAreaHierarchy(selectedRoot) : []),
    [roomGrouping, selectedRoot],
  );
  const visibleAreas = useMemo(
    () => visibleChildren(areas, filters, rootSearchMatched).children as BudgetHierarchyGroup[],
    [areas, filters, rootSearchMatched],
  );

  return (
    <section className="mt-4" data-stage={selectedRoot?.milestoneId}>
      {selectedRoot && (
        <>
          <CategorySummary group={selectedRoot} />
          {roomGrouping && (
            <div className="mb-2.5 flex justify-end">
              <ToggleGroup
                aria-label="Grupare buget"
                className={segmentedGroupStyles}
                onValueChange={(nextValues) => {
                  const nextValue = BUDGET_GROUPINGS.find((value) => value === nextValues[0]);
                  if (nextValue) props.onGroupingChange(nextValue);
                }}
                value={[grouping]}
              >
                {BUDGET_GROUPINGS.map((value) => (
                  <Toggle className={segmentedToggleStyles} key={value} value={value}>
                    {GROUPING_LABELS[value]}
                  </Toggle>
                ))}
              </ToggleGroup>
            </div>
          )}
          {grouping === "rooms" ? (
            <div>
              <p className="mb-3 text-[0.71rem] text-muted">
                Totalurile pe camere acoperă doar etapa selectată.
              </p>
              {visibleAreas.length > 0 ? (
                visibleAreas.map((area) => (
                  <AreaSection
                    ancestorMatched={rootSearchMatched}
                    area={area}
                    beneficiaryNames={beneficiaryNames}
                    filters={filters}
                    key={area.id}
                    onOpenBeneficiary={props.onOpenBeneficiary}
                    onOpenItem={props.onOpenItem}
                    stageLabel={selectedRoot.label}
                  />
                ))
              ) : (
                <div className={emptyStatePanelStyles}>
                  Niciun element din etapa {selectedRoot.label} nu corespunde filtrelor.
                </div>
              )}
            </div>
          ) : (
            <GroupTable
              ancestors={[selectedRoot.id]}
              beneficiaryNames={beneficiaryNames}
              children={selectedRoot.children}
              emptyMessage={`Niciun element din categoria ${selectedRoot.label} nu corespunde filtrelor.`}
              filters={filters}
              onOpenBeneficiary={props.onOpenBeneficiary}
              onOpenItem={props.onOpenItem}
              searchMatched={rootSearchMatched}
              tableKey={selectedRoot.id}
            />
          )}
        </>
      )}
    </section>
  );
}
