import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { ArchiveRestore, ChevronDown, Circle, CircleCheck, TriangleAlert } from "lucide-react";
import { type MouseEvent, useMemo, useRef, useState } from "react";

import {
  getBudgetAreaHierarchy,
  type BudgetHierarchyGroup,
  type BudgetHierarchyItem,
  type DerivedItem,
} from "../../domain/index.js";
import { formatDateRange, formatMoney, formatMoneyRange } from "../../ui/format.js";
import { CategoryIcon, categoryStage } from "../shared/CategoryIcon.js";
import { ItemIcon } from "../shared/ItemIcon.js";
import { ItemStatus } from "../shared/ItemStatus.js";
import {
  cn,
  moneyCellStyles,
  segmentedGroupStyles,
  segmentedToggleStyles,
} from "../shared/styles.js";
import { AnimatedBudgetRow, AnimatedCellContent } from "./AnimatedBudgetRow.js";
import type { ScopeFilter, StatusFilter } from "./BudgetToolbar.js";

const tableCellStyles = "px-3.5 text-left align-middle select-text";
const tableHeaderStyles =
  "sticky top-0 z-(--z-sticky) bg-table-head px-3.5 py-3 text-left text-[0.65rem] font-[760] tracking-[0.08em] text-muted uppercase";

interface Filters {
  search: string;
  scope: ScopeFilter;
  status: StatusFilter;
}

interface BudgetTableProps {
  hierarchy: BudgetHierarchyGroup[];
  filters: Filters;
  grouping: BudgetGrouping;
  selectedCategory: string;
  onGroupingChange: (grouping: BudgetGrouping) => void;
  onOpenItem: (itemId: string) => void;
}

export type BudgetGrouping = "rooms" | "categories";

const ROOM_GROUPING_CATEGORY_IDS = new Set(["finish", "move"]);

function isTextSelectionClick(event: MouseEvent<HTMLElement>): boolean {
  const selection = event.currentTarget.ownerDocument.getSelection();
  return (
    event.detail > 0 && !!selection?.toString() && selection.containsNode(event.currentTarget, true)
  );
}

function itemMatches(entry: DerivedItem, filters: Filters, searchMatched = false): boolean {
  const query = filters.search.trim().toLocaleLowerCase("ro");
  if (filters.scope !== "all" && entry.item.costScope !== filters.scope) return false;
  if (!searchMatched && query && !entry.item.label.toLocaleLowerCase("ro").includes(query))
    return false;
  if (filters.status === "active" && !entry.active) return false;
  if (filters.status === "complete" && !entry.item.completion.complete) return false;
  if (filters.status === "overdue" && entry.overdueCents === 0) return false;
  if (filters.status === "excluded" && (entry.item.included || entry.effectivelyArchived))
    return false;
  if (filters.status === "archived" && !entry.effectivelyArchived) return false;
  return true;
}

function groupHasMatches(
  group: BudgetHierarchyGroup,
  filters: Filters,
  ancestorMatched = false,
): boolean {
  const query = filters.search.trim().toLocaleLowerCase("ro");
  const groupMatched =
    ancestorMatched || (!!query && group.label.toLocaleLowerCase("ro").includes(query));
  if (group.children.length === 0) {
    const searchMatches = !query || groupMatched;
    const statusMatches =
      filters.status === "all" ||
      (filters.status === "active" && !group.archived) ||
      (filters.status === "archived" && group.archived);
    return filters.scope === "all" && searchMatches && statusMatches;
  }
  return group.children.some((child) =>
    child.kind === "item"
      ? itemMatches(child.derived, filters, groupMatched)
      : groupHasMatches(child, filters, groupMatched),
  );
}

function PaymentProgress({
  label,
  totalCents,
  settledCents,
}: {
  label: string;
  totalCents: number;
  settledCents: number;
}) {
  if (totalCents === 0) return null;
  const paid = settledCents === totalCents;
  const unpaid = settledCents === 0;

  if (paid || unpaid) {
    const Icon = paid ? CircleCheck : Circle;
    return (
      <div
        className={cn(
          "flex items-center gap-2 text-[0.7rem]",
          paid ? "font-medium text-olive" : "text-muted",
        )}
      >
        <Icon aria-hidden="true" className="shrink-0" size={16} strokeWidth={1.75} />
        <span>{paid ? "Plătit" : "Neplătit"}</span>
      </div>
    );
  }

  const remaining = totalCents - settledCents;
  const status = `${formatMoney(settledCents)} plătit`;
  const detail = `${formatMoney(remaining)} rămas`;

  return (
    <div className="flex items-center gap-2">
      <div
        aria-label={`Plăți: ${label}`}
        aria-valuemax={totalCents}
        aria-valuemin={0}
        aria-valuenow={settledCents}
        aria-valuetext={`${status}, ${detail}`}
        className="size-5 shrink-0 text-olive"
        role="progressbar"
      >
        <svg aria-hidden="true" className="size-full -rotate-90" fill="none" viewBox="0 0 20 20">
          <circle className="stroke-muted/25" cx="10" cy="10" r="8" strokeWidth="2" />
          <circle
            cx="10"
            cy="10"
            pathLength="100"
            r="8"
            stroke="currentColor"
            strokeDasharray={`${(settledCents / totalCents) * 100} 100`}
            strokeLinecap="round"
            strokeWidth="2"
          />
        </svg>
      </div>
      <div className="grid gap-0.5 text-[0.7rem] tabular-nums">
        <span className="font-medium">{status}</span>
        <span className="text-[0.65rem] text-muted">{detail}</span>
      </div>
    </div>
  );
}

function ItemRow({
  child,
  depth,
  open,
  ancestors,
  onOpen,
}: {
  child: BudgetHierarchyItem;
  depth: number;
  open: boolean;
  ancestors: string[];
  onOpen: () => void;
}) {
  const entry = child.derived;
  const remaining = Math.max(0, entry.forecastCents - entry.actualPaidCents);
  const paidPrice =
    entry.item.ownership === "owned"
      ? entry.active
        ? entry.totalCents
        : entry.estimateCents
      : entry.actualPaidCents > 0 && remaining === 0
        ? entry.actualPaidCents
        : undefined;
  const estimateForecast =
    paidPrice === undefined
      ? formatMoneyRange(entry.estimateCents, entry.forecastCents)
      : formatMoney(paidPrice);

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
        if (isTextSelectionClick(event)) return;
        if (event.target instanceof Element && event.target.closest("button")) return;
        event.currentTarget.querySelector("button")?.focus();
        onOpen();
      }}
    >
      {(phase, animationRef) => (
        <>
          <th className={cn(tableCellStyles, "font-normal")} scope="row">
            <AnimatedCellContent phase={phase} ref={animationRef}>
              <div
                className="flex items-center gap-2"
                style={{ paddingInlineStart: `${depth * 16}px` }}
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
                  </span>
                </button>
                <ItemStatus item={entry.item} />
              </div>
            </AnimatedCellContent>
          </th>
          <td className={cn(tableCellStyles, moneyCellStyles, "text-right")}>
            <AnimatedCellContent phase={phase}>
              <strong>{estimateForecast}</strong>
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
  depth,
  searchActive,
  open,
  ancestors,
  onOpenItem,
  ancestorMatched = false,
}: {
  group: BudgetHierarchyGroup;
  filters: Filters;
  depth: number;
  searchActive: boolean;
  open: boolean;
  ancestors: string[];
  onOpenItem: (itemId: string) => void;
  ancestorMatched?: boolean;
}) {
  const query = filters.search.trim().toLocaleLowerCase("ro");
  const groupMatched =
    ancestorMatched || (!!query && group.label.toLocaleLowerCase("ro").includes(query));
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [expanded, setExpanded] = useState(true);
  if (!groupHasMatches(group, filters, ancestorMatched)) return null;
  const isExpanded = searchActive || expanded;
  const contentOpen = open && isExpanded;

  const toggle = () => {
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
          "cursor-pointer border-t border-line bg-group",
          depth === 1 ? "bg-group-nested" : depth >= 2 && "bg-group-deep",
        )}
        onClick={(event) => {
          if (isTextSelectionClick(event)) return;
          if (event.target instanceof Element && event.target.closest("button")) return;
          toggle();
        }}
      >
        {(phase, animationRef) => (
          <>
            <th className={cn(tableCellStyles, "font-normal")} scope="row">
              <AnimatedCellContent phase={phase} ref={animationRef}>
                <div
                  className="flex items-center gap-1.75 text-[0.79rem] font-[760]"
                  style={{ paddingInlineStart: `${depth * 16}px` }}
                >
                  <button
                    ref={triggerRef}
                    aria-expanded={isExpanded}
                    aria-label={`${isExpanded ? "Restrânge" : "Extinde"} ${group.label}`}
                    className="inline-flex min-h-9 min-w-9 items-center justify-center rounded-[5px] border-0 bg-transparent p-0 hover:bg-line/60"
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
                  <span>{group.label}</span>
                  {group.archived && <ArchiveRestore aria-label="Categorie arhivată" size={14} />}
                </div>
              </AnimatedCellContent>
            </th>
            <td className={cn(tableCellStyles, moneyCellStyles, "text-right")}>
              <AnimatedCellContent phase={phase}>
                <strong>{formatMoneyRange(group.estimateCents, group.totalCents)}</strong>
              </AnimatedCellContent>
            </td>
            <td className={tableCellStyles}>
              <AnimatedCellContent phase={phase}>
                <PaymentProgress
                  label={group.label}
                  totalCents={group.totalCents}
                  settledCents={group.settledCents}
                />
              </AnimatedCellContent>
            </td>
            <td className={cn(tableCellStyles, "text-[0.72rem]")}>
              <AnimatedCellContent phase={phase}>
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
            depth={depth + 1}
            filters={filters}
            group={child}
            key={child.id}
            onOpenItem={onOpenItem}
            open={contentOpen}
            searchActive={searchActive}
          />
        ) : itemMatches(child.derived, filters, groupMatched) ? (
          <ItemRow
            ancestors={[...ancestors, group.id]}
            child={child}
            depth={depth + 1}
            key={child.id}
            onOpen={() => onOpenItem(child.id)}
            open={contentOpen}
          />
        ) : null,
      )}
    </>
  );
}

function CategorySummary({ group }: { group: BudgetHierarchyGroup }) {
  return (
    <div
      className="mb-2.5 grid grid-cols-[minmax(0,1.25fr)_minmax(120px,0.65fr)_minmax(180px,0.9fr)_minmax(130px,0.7fr)] items-center gap-4 rounded-xl border border-stage/24 bg-stage-header px-4 py-3"
      data-budget-summary={group.id}
      data-stage={categoryStage(group.id)}
    >
      <div className="flex min-w-0 items-center gap-2 text-[0.83rem] font-[760]">
        <CategoryIcon categoryId={group.id} size={18} />
        <span>{group.label}</span>
        {group.archived && <ArchiveRestore aria-label="Categorie arhivată" size={14} />}
      </div>
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
  searchActive,
  searchMatched,
  tableKey,
}: {
  ancestors: string[];
  children: Array<BudgetHierarchyGroup | BudgetHierarchyItem>;
  emptyMessage: string;
  filters: Filters;
  onOpenItem: (itemId: string) => void;
  searchActive: boolean;
  searchMatched: boolean;
  tableKey: string;
}) {
  return (
    <div
      aria-label="Tabel de buget derulabil pe orizontală"
      className="max-w-full overflow-auto rounded-xl border border-line bg-surface focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
      tabIndex={0}
    >
      <table className="w-full min-w-225 table-fixed border-collapse">
        <thead>
          <tr>
            <th className={tableHeaderStyles}>Element</th>
            <th className={cn(tableHeaderStyles, "w-[18%] text-right")}>Cost</th>
            <th className={cn(tableHeaderStyles, "w-[22%]")}>Plăți</th>
            <th className={cn(tableHeaderStyles, "w-[21%]")}>Calendar</th>
          </tr>
        </thead>
        <tbody key={tableKey}>
          {children.map((child) =>
            child.kind === "group" ? (
              <GroupRows
                ancestorMatched={searchMatched}
                ancestors={ancestors}
                depth={0}
                filters={filters}
                group={child}
                key={child.id}
                onOpenItem={onOpenItem}
                open
                searchActive={searchActive}
              />
            ) : (
              <ItemRow
                ancestors={ancestors}
                child={child}
                depth={0}
                key={child.id}
                onOpen={() => onOpenItem(child.id)}
                open
              />
            ),
          )}
          {children.length === 0 && (
            <tr className="border-t border-line">
              <td className="px-5 py-13 text-center text-muted" colSpan={4}>
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
  stageLabel,
}: {
  ancestorMatched: boolean;
  area: BudgetHierarchyGroup;
  filters: Filters;
  onOpenItem: (itemId: string) => void;
  stageLabel: string;
}) {
  const searchActive = filters.search.trim().length > 0;
  const searchMatched = Boolean(
    ancestorMatched ||
    (searchActive &&
      area.label.toLocaleLowerCase("ro").includes(filters.search.trim().toLocaleLowerCase("ro"))),
  );
  const visibleChildren = area.children.filter((child) =>
    child.kind === "group"
      ? groupHasMatches(child, filters, searchMatched)
      : itemMatches(child.derived, filters, searchMatched),
  );
  const headingId = `budget-area-heading-${area.id}`;

  return (
    <section aria-labelledby={headingId} className="mt-5 first:mt-0">
      <div
        className="mb-2 grid grid-cols-[minmax(0,1.25fr)_minmax(120px,0.65fr)_minmax(180px,0.9fr)_minmax(130px,0.7fr)] items-center gap-4 px-1"
        data-budget-area-summary={area.id}
      >
        <div className="min-w-0">
          <h3 className="text-[0.86rem] font-[780]" id={headingId}>
            {area.label}
          </h3>
          <p className="text-[0.67rem] text-muted">Subtotal în {stageLabel}</p>
        </div>
        <strong className="text-right text-[0.84rem] tabular-nums">
          {formatMoneyRange(area.estimateCents, area.totalCents)}
        </strong>
        <PaymentProgress
          label={`${area.label}, ${stageLabel}`}
          settledCents={area.settledCents}
          totalCents={area.totalCents}
        />
        <span className="text-[0.72rem] text-muted">
          {formatDateRange(area.scheduleStartOn, area.scheduleFinalOn)}
        </span>
      </div>
      <GroupTable
        ancestors={[area.id]}
        children={visibleChildren}
        emptyMessage={`Niciun element din zona ${area.label} nu corespunde filtrelor.`}
        filters={filters}
        onOpenItem={onOpenItem}
        searchActive={searchActive}
        searchMatched={searchMatched}
        tableKey={area.id}
      />
    </section>
  );
}

export function BudgetTable(props: BudgetTableProps) {
  const selectedRoot =
    props.hierarchy.find((group) => group.id === props.selectedCategory) ?? props.hierarchy[0];
  const rootSearchMatched = Boolean(
    selectedRoot &&
    props.filters.search.trim() &&
    selectedRoot.label
      .toLocaleLowerCase("ro")
      .includes(props.filters.search.trim().toLocaleLowerCase("ro")),
  );
  const visibleChildren = useMemo(
    () =>
      selectedRoot?.children.filter((child) =>
        child.kind === "group"
          ? groupHasMatches(child, props.filters, rootSearchMatched)
          : itemMatches(child.derived, props.filters, rootSearchMatched),
      ) ?? [],
    [props.filters, rootSearchMatched, selectedRoot],
  );
  const supportsRoomGrouping = Boolean(
    selectedRoot && ROOM_GROUPING_CATEGORY_IDS.has(selectedRoot.id),
  );
  const grouping = supportsRoomGrouping ? props.grouping : "categories";
  const visibleAreas = useMemo(
    () =>
      selectedRoot
        ? getBudgetAreaHierarchy(selectedRoot).filter((area) =>
            groupHasMatches(area, props.filters, rootSearchMatched),
          )
        : [],
    [props.filters, rootSearchMatched, selectedRoot],
  );

  return (
    <section className="mt-4">
      {selectedRoot && (
        <>
          <CategorySummary group={selectedRoot} />
          {supportsRoomGrouping && (
            <div className="mb-2.5 flex justify-end">
              <ToggleGroup
                aria-label="Grupare buget"
                className={segmentedGroupStyles}
                onValueChange={(nextValues) => {
                  const [nextValue] = nextValues;
                  if (nextValue === "rooms" || nextValue === "categories") {
                    props.onGroupingChange(nextValue);
                  }
                }}
                value={[grouping]}
              >
                {(
                  [
                    ["rooms", "Pe camere"],
                    ["categories", "Pe categorii"],
                  ] as const
                ).map(([value, label]) => (
                  <Toggle className={segmentedToggleStyles} key={value} value={value}>
                    {label}
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
                    filters={props.filters}
                    key={area.id}
                    onOpenItem={props.onOpenItem}
                    stageLabel={selectedRoot.label}
                  />
                ))
              ) : (
                <div className="rounded-xl border border-line bg-surface px-5 py-13 text-center text-muted">
                  Niciun element din etapa {selectedRoot.label} nu corespunde filtrelor.
                </div>
              )}
            </div>
          ) : (
            <GroupTable
              ancestors={[selectedRoot.id]}
              children={visibleChildren}
              emptyMessage={`Niciun element din categoria ${selectedRoot.label} nu corespunde filtrelor.`}
              filters={props.filters}
              onOpenItem={props.onOpenItem}
              searchActive={props.filters.search.trim().length > 0}
              searchMatched={rootSearchMatched}
              tableKey={selectedRoot.id}
            />
          )}
        </>
      )}
    </section>
  );
}
