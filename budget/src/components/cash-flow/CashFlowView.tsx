import { Collapsible } from "@base-ui/react/collapsible";
import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { Tooltip } from "@base-ui/react/tooltip";
import {
  CalendarClock,
  ChartColumnIncreasing,
  ChevronDown,
  Clock3,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { type ReactNode, useId, useMemo, useState } from "react";

import { UI_LOCALE } from "../../domain/collections.js";
import type { Milestone } from "../../domain/schema.js";
import type { BudgetView, CashFlowAllocation, CashFlowBucket } from "../../domain/selectors.js";
import { formatDate, formatMoney, pluralNoun } from "../../ui/format.js";
import { ItemBrandIcon, ItemIcon } from "../shared/ItemIcon.js";
import {
  cn,
  eyebrowStyles,
  iconLabelStyles,
  pageHeadingStyles,
  segmentedGroupStyles,
  segmentedToggleStyles,
} from "../shared/styles.js";
import {
  aggregateCashFlowByPeriod,
  makeCashFlowPeriods,
  cashFlowMonthRange,
  type PeriodGranularity,
  type PeriodCashFlow,
} from "./cash-flow-periods.js";

interface CashFlowViewProps {
  view: BudgetView;
  onOpenItem: (itemId: string) => void;
  milestoneId?: Milestone["id"] | "all";
}

const chartTextStyles = "fill-muted font-planning text-[11.25px] tabular-nums";
const chartCumulativeTextStyles = "fill-ink font-planning text-[11.25px] font-bold tabular-nums";
const listButtonStyles =
  "flex min-h-11 w-full cursor-pointer items-center justify-between border-0 border-t border-line bg-transparent px-0 py-1.75 text-left text-[0.8rem] hover:bg-canvas/55";
const exactCellStyles = "border-b border-line px-2.5 py-2 text-right whitespace-nowrap";

/** Stacked cash-flow series, bottom to top, shared by the legend, bars, labels and tables. */
const CASH_FLOW_SERIES: ReadonlyArray<{
  label: string;
  dotClassName: string;
  barClassName: string;
  cents: (bucket: CashFlowBucket) => number;
}> = [
  {
    label: "Plătit",
    dotClassName: "bg-accent",
    barClassName: "fill-accent",
    cents: (bucket) => bucket.actualCents,
  },
  {
    label: "Obligație de bază",
    dotClassName: "bg-olive",
    barClassName: "fill-olive",
    cents: (bucket) => bucket.plannedCents,
  },
  {
    label: "Rezervă",
    dotClassName: "bg-reserve",
    barClassName: "fill-reserve",
    cents: (bucket) => bucket.contingencyCents,
  },
];

const EXACT_COLUMNS = ["Lună", ...CASH_FLOW_SERIES.map(({ label }) => label), "Total", "Cumul"];

function StatTile({
  icon: Icon,
  label,
  note,
  value,
}: {
  icon: LucideIcon;
  label: string;
  note: string;
  value: ReactNode;
}) {
  return (
    <div className="flex min-h-24 flex-col px-4.5 py-3.5">
      <span className={cn("text-[0.71rem] text-muted", iconLabelStyles)}>
        <Icon aria-hidden="true" size={16} /> {label}
      </span>
      <strong className="mt-1.5 mb-0.5 text-[1.45rem] tracking-[-0.04em] tabular-nums">
        {value}
      </strong>
      <small className="text-[0.71rem] text-muted">{note}</small>
    </div>
  );
}

function allocationLabel(allocation: CashFlowAllocation): string {
  if (allocation.kind === "actual") return "Plătit";
  if (allocation.kind === "contingency") return "Rezervă";
  if (allocation.kind === "unallocated") return "Nealocat";
  return "Planificat";
}

function CashFlowChart({
  flows,
  selectedKey,
  onSelect,
}: {
  flows: PeriodCashFlow[];
  selectedKey: string;
  onSelect: (key: string) => void;
}) {
  const tooltipId = useId();
  const width = Math.max(680, flows.length * 58 + 36);
  const height = 250;
  const baseline = 196;
  const top = 28;
  const max = Math.max(1, ...flows.map((flow) => flow.totalCents));
  const maxCumulative = Math.max(1, flows.at(-1)?.cumulativeCents ?? 0);
  const points = flows.map((flow, index) => ({
    x: 38 + index * 58 + 21,
    y: baseline - (flow.cumulativeCents / maxCumulative) * (baseline - top),
    flow,
  }));
  const line = points
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x} ${point.y}`)
    .join(" ");
  const first = points[0];
  const last = points.at(-1);
  const area = first && last ? `${line} L${last.x} ${baseline} L${first.x} ${baseline} Z` : "";

  return (
    <div
      className="max-w-full overflow-x-auto border-b border-line [overscroll-behavior-inline:contain]"
      aria-label="Grafic de flux de numerar, derulabil pe orizontală"
      role="region"
    >
      <svg
        className="block min-w-full"
        height={height}
        aria-label="Plăți pe perioadă și cumulul investiției"
        role="group"
        viewBox={`0 0 ${width} ${height}`}
        width={width}
      >
        <title>Plăți pe perioadă și cumulul investiției</title>
        <text className={chartTextStyles} x="2" y={top + 5}>
          {formatMoney(max)}
        </text>
        <text className={chartTextStyles} x="2" y={baseline + 4}>
          {formatMoney(0)}
        </text>
        <text className={chartCumulativeTextStyles} textAnchor="end" x={width - 2} y={top + 5}>
          {formatMoney(maxCumulative)}
        </text>
        <text className={chartCumulativeTextStyles} textAnchor="end" x={width - 2} y={baseline + 4}>
          {formatMoney(0)}
        </text>
        {[0.25, 0.5, 0.75, 1].map((ratio) => (
          <line
            className="stroke-line stroke-1 [stroke-dasharray:2_4]"
            key={ratio}
            x1="32"
            x2={width - 14}
            y1={baseline - ratio * (baseline - top)}
            y2={baseline - ratio * (baseline - top)}
          />
        ))}
        <line
          className="stroke-line stroke-1"
          x1="32"
          x2={width - 14}
          y1={baseline}
          y2={baseline}
        />
        {area && <path className="fill-ink/6" d={area} />}
        {points.map(({ flow, x: centerX }) => {
          const x = centerX - 21;
          let y = baseline;
          return (
            <Tooltip.Root key={flow.periodKey}>
              <g className="group/chart" data-selected={flow.periodKey === selectedKey}>
                {CASH_FLOW_SERIES.map(({ label, barClassName, cents }) => {
                  const amount = cents(flow);
                  const barHeight = (amount / max) * (baseline - top);
                  y -= barHeight;
                  return amount > 0 ? (
                    <rect
                      className={cn(
                        "transition-opacity duration-140 ease-[ease] group-focus-within/chart:opacity-80 group-hover/chart:opacity-80 motion-reduce:transition-none forced-colors:forced-color-adjust-none",
                        barClassName,
                      )}
                      height={barHeight}
                      key={label}
                      rx="2"
                      width="42"
                      x={x}
                      y={y}
                    />
                  ) : null;
                })}
                <Tooltip.Trigger
                  aria-describedby={`${tooltipId}-${flow.periodKey}`}
                  aria-label={`${flow.label}: ${CASH_FLOW_SERIES.map(({ label, cents }) => `${label.toLocaleLowerCase(UI_LOCALE)} ${formatMoney(cents(flow))}`).join(", ")}, cumul până aici ${formatMoney(flow.cumulativeCents)}`}
                  className="cursor-pointer fill-transparent outline-none focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-accent"
                  delay={0}
                  onClick={() => onSelect(flow.periodKey)}
                  onFocus={() => onSelect(flow.periodKey)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect(flow.periodKey);
                    }
                  }}
                  render={<rect height="220" rx="5" width="48" x={x - 3} y="8" />}
                  role="button"
                  tabIndex={0}
                />
                <text
                  className="pointer-events-none fill-muted font-planning text-[11.25px] font-[650] group-data-[selected=true]/chart:fill-ink"
                  textAnchor="middle"
                  x={x + 21}
                  y="220"
                >
                  {flow.label}
                </text>
                {flow.periodKey === selectedKey && (
                  <rect className="fill-accent" height="3" rx="1.5" width="28" x={x + 7} y="226" />
                )}
              </g>
              <Tooltip.Portal>
                <Tooltip.Positioner
                  className="z-(--z-dropdown)"
                  sideOffset={10}
                  collisionPadding={12}
                >
                  <Tooltip.Popup
                    id={`${tooltipId}-${flow.periodKey}`}
                    role="tooltip"
                    className="min-w-56 origin-(--transform-origin) rounded-xl bg-ink px-4 py-3.5 font-planning text-surface shadow-panel transition-[opacity,transform] duration-150 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0 motion-reduce:transition-none"
                  >
                    <Tooltip.Arrow className="data-[side=bottom]:-top-1.5 data-[side=bottom]:rotate-180 data-[side=top]:-bottom-1.5">
                      <svg
                        width="12"
                        height="6"
                        viewBox="0 0 12 6"
                        className="fill-ink"
                        aria-hidden="true"
                      >
                        <path d="M0 0H12L6 6Z" />
                      </svg>
                    </Tooltip.Arrow>
                    <p className="mb-3 text-[0.68rem] font-bold tracking-widest text-surface/70 uppercase">
                      {flow.label}
                    </p>
                    <p className="text-[0.72rem] text-surface/75">Cumul până aici</p>
                    <p className="mt-0.5 text-2xl font-[650] tracking-[-0.04em] tabular-nums">
                      {formatMoney(flow.cumulativeCents)}
                    </p>
                    <div className="mt-3 flex items-center justify-between gap-6 border-t border-surface/20 pt-2.5 text-[0.72rem]">
                      <span className="text-surface/75">În această perioadă</span>
                      <span className="font-semibold tabular-nums">
                        {formatMoney(flow.totalCents)}
                      </span>
                    </div>
                  </Tooltip.Popup>
                </Tooltip.Positioner>
              </Tooltip.Portal>
            </Tooltip.Root>
          );
        })}
        {points.length > 0 && (
          <path
            className="pointer-events-none fill-none stroke-ink stroke-[2.25] [stroke-linecap:round] [stroke-linejoin:round]"
            d={line}
          />
        )}
        {points.map((point) => (
          <circle
            className="pointer-events-none fill-surface stroke-ink stroke-2"
            cx={point.x}
            cy={point.y}
            key={point.flow.periodKey}
            r="3.5"
          />
        ))}
      </svg>
    </div>
  );
}

export function CashFlowView({ view, milestoneId = "all", onOpenItem }: CashFlowViewProps) {
  const [granularity, setGranularity] = useState<PeriodGranularity>("month");
  const visibleItemIds = useMemo(
    () =>
      new Set(
        view.items
          .filter((entry) => milestoneId === "all" || entry.item.milestoneId === milestoneId)
          .map((entry) => entry.item.id),
      ),
    [milestoneId, view.items],
  );
  const dates = useMemo(
    () => [
      ...view.allocations.flatMap((allocation) =>
        visibleItemIds.has(allocation.itemId) && allocation.date ? [allocation.date] : [],
      ),
      ...view.timeline
        .filter(({ milestone }) => milestoneId === "all" || milestone.id === milestoneId)
        .flatMap(({ milestone }) =>
          milestone.startDate ? [milestone.startDate, milestone.date] : [milestone.date],
        ),
    ],
    [milestoneId, view.allocations, view.timeline, visibleItemIds],
  );
  const range = useMemo(() => cashFlowMonthRange(dates), [dates]);
  const monthSeries = useMemo(
    () =>
      aggregateCashFlowByPeriod(
        view.allocations,
        makeCashFlowPeriods(range.startMonth, range.endMonth, "month"),
        "month",
        visibleItemIds,
      ),
    [range.endMonth, range.startMonth, view.allocations, visibleItemIds],
  );
  const quarterSeries = useMemo(
    () =>
      granularity === "quarter"
        ? aggregateCashFlowByPeriod(
            view.allocations,
            makeCashFlowPeriods(range.startMonth, range.endMonth, "quarter"),
            "quarter",
            visibleItemIds,
          )
        : undefined,
    [granularity, range.endMonth, range.startMonth, view.allocations, visibleItemIds],
  );
  const series = quarterSeries ?? monthSeries;
  const itemLabels = useMemo(
    () => new Map(view.items.map((entry) => [entry.item.id, entry.item.label])),
    [view.items],
  );
  const [selectedKey, setSelectedKey] = useState<string | undefined>();
  const selected =
    series.flows.find((flow) => flow.periodKey === selectedKey) ??
    series.flows.find((flow) => flow.totalCents > 0) ??
    series.flows[0];
  const largestMonth = monthSeries.flows.reduce<PeriodCashFlow | undefined>(
    (largest, flow) => (largest && largest.totalCents >= flow.totalCents ? largest : flow),
    undefined,
  );
  const datedTotal = series.flows.at(-1)?.cumulativeCents ?? 0;
  const allUpcoming = view.upcomingPayments.filter((payment) => visibleItemIds.has(payment.itemId));
  const upcoming = allUpcoming.slice(0, 4);

  return (
    <section
      className="max-w-full font-planning text-ink [&_h2]:text-base/[1.45] [&_h2]:font-[650]"
      aria-labelledby="cashflow-title"
    >
      <header className="mb-5 flex items-end justify-between gap-6">
        <div>
          <p className={eyebrowStyles}>Ritm de finanțare</p>
          <h1 id="cashflow-title" className={cn(pageHeadingStyles, iconLabelStyles)}>
            <ChartColumnIncreasing aria-hidden="true" size={25} /> Fluxul de numerar
          </h1>
          <p className="mt-2.5 text-[0.9rem] text-muted">
            {milestoneId === "all"
              ? "Până la mutare"
              : view.timeline.find(({ milestone }) => milestone.id === milestoneId)?.milestone
                  .label}{" "}
            · {formatMoney(datedTotal)} cu dată stabilită
          </p>
        </div>
        <ToggleGroup
          className={segmentedGroupStyles}
          aria-label="Agregarea fluxului de numerar"
          onValueChange={(nextValues) => {
            const [nextValue] = nextValues;
            if (nextValue === "month" || nextValue === "quarter") setGranularity(nextValue);
          }}
          value={[granularity]}
        >
          <Toggle className={segmentedToggleStyles} value="month">
            Luni
          </Toggle>
          <Toggle className={segmentedToggleStyles} value="quarter">
            Trimestre
          </Toggle>
        </ToggleGroup>
      </header>

      <div
        className="mb-4.5 grid grid-cols-3 border-y border-line [&>div+div]:border-l [&>div+div]:border-line"
        aria-label="Repere flux de numerar"
        role="group"
      >
        <StatTile
          icon={TrendingUp}
          label="Vârf de numerar"
          note={largestMonth?.label ?? "Fără plăți datate"}
          value={formatMoney(largestMonth?.totalCents ?? 0)}
        />
        <StatTile
          icon={CalendarClock}
          label="Plăți viitoare"
          note={`${pluralNoun(allUpcoming.length, { one: "element", other: "elemente" })} în filtru`}
          value={allUpcoming.length}
        />
        <StatTile
          icon={Clock3}
          label="Fără termen"
          note="nealocat în coloanele datate"
          value={formatMoney(series.undated.totalCents)}
        />
      </div>

      <div
        className="mb-3.25 flex flex-wrap items-center gap-x-4.5 gap-y-2.5 text-[0.76rem] text-muted"
        aria-label="Legendă flux de numerar"
        role="group"
      >
        {CASH_FLOW_SERIES.map(({ dotClassName, label }) => (
          <span className="inline-flex items-center gap-1.75" key={label}>
            <i
              className={cn(
                "inline-block size-2.25 rounded-full forced-colors:forced-color-adjust-none",
                dotClassName,
              )}
            />
            {label}
          </span>
        ))}
        <em className="text-[0.72rem] text-muted not-italic">
          Barele folosesc scara din stânga; linia cumulată, scara din dreapta.
        </em>
      </div>

      {series.flows.length > 0 ? (
        <CashFlowChart
          flows={series.flows}
          onSelect={setSelectedKey}
          selectedKey={selected?.periodKey ?? ""}
        />
      ) : (
        <p className="px-4 py-5 text-[0.86rem] text-muted">
          Nu sunt plăți datate pentru acest filtru.
        </p>
      )}

      {selected && (
        <section
          className="grid grid-cols-[minmax(150px,0.5fr)_minmax(0,2fr)] items-center gap-6 border-b border-line py-5.5 [&_dl>div]:border-l [&_dl>div]:border-line [&_dl>div]:px-3.5 [&_dl>div]:py-0.75"
          aria-live="polite"
        >
          <div>
            <p className={eyebrowStyles}>Detaliu perioadă</p>
            <h2>{selected.label}</h2>
          </div>
          <dl className="m-0 grid grid-cols-5 [&_dd]:mt-1.5 [&_dd]:text-[0.86rem] [&_dd]:font-[750] [&_dd]:tabular-nums [&_dt]:text-[0.68rem] [&_dt]:text-muted">
            {[
              ...CASH_FLOW_SERIES.map(({ label, cents }) => [label, cents(selected)] as const),
              ["Total", selected.totalCents] as const,
              ["Cumul până aici", selected.cumulativeCents] as const,
            ].map(([label, cents]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{formatMoney(cents)}</dd>
              </div>
            ))}
          </dl>
          <div className="col-span-full grid">
            {selected.allocations.length > 0 ? (
              selected.allocations.map((allocation) => (
                <button
                  aria-haspopup="dialog"
                  className={listButtonStyles}
                  key={allocation.id}
                  onClick={() => onOpenItem(allocation.itemId)}
                  type="button"
                >
                  <span className="min-w-0">
                    <b className="ml-0 flex items-center gap-1.5 text-[0.78rem] font-[750] tabular-nums">
                      <ItemIcon itemId={allocation.itemId} size={16} />
                      {itemLabels.get(allocation.itemId) ?? "Element"}
                      <ItemBrandIcon itemId={allocation.itemId} />
                    </b>
                    <small className="mt-0.5 block text-[0.68rem] text-muted">
                      {allocationLabel(allocation)}
                      {allocation.date ? ` · ${formatDate(allocation.date)}` : " · fără dată"}
                    </small>
                  </span>
                  <strong className="ml-4 flex-none font-[750] tabular-nums">
                    {formatMoney(allocation.amountCents)}
                  </strong>
                </button>
              ))
            ) : (
              <p className="text-[0.8rem] text-muted">Nu sunt alocări în această perioadă.</p>
            )}
          </div>
        </section>
      )}

      <Collapsible.Root
        className="group mt-4.5 border-b border-line pb-3.5 text-[0.78rem] text-muted [&_th:first-child]:text-left"
        defaultOpen={false}
      >
        <Collapsible.Trigger className="inline-flex cursor-pointer items-center gap-1.5 border-0 bg-transparent py-2 text-left font-bold hover:text-ink data-open:text-ink">
          <ChevronDown
            aria-hidden="true"
            className="transition-transform group-data-open:rotate-180 motion-reduce:transition-none"
            size={14}
          />
          Valori lunare exacte și cumul
        </Collapsible.Trigger>
        <Collapsible.Panel className="h-(--collapsible-panel-height) overflow-hidden transition-[height] duration-200 data-ending-style:h-0 data-starting-style:h-0 motion-reduce:transition-none">
          <div className="max-w-full overflow-x-auto">
            <table className="w-full min-w-170 border-collapse tabular-nums">
              <thead className="text-ink">
                <tr>
                  {EXACT_COLUMNS.map((column) => (
                    <th className={exactCellStyles} key={column} scope="col">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {monthSeries.flows.map((flow) => (
                  <tr key={flow.periodKey}>
                    <th className={exactCellStyles} scope="row">
                      {flow.label}
                    </th>
                    {[
                      ...CASH_FLOW_SERIES.map(({ cents }) => cents(flow)),
                      flow.totalCents,
                      flow.cumulativeCents,
                    ].map((cents, index) => (
                      <td className={exactCellStyles} key={EXACT_COLUMNS[index + 1]}>
                        {formatMoney(cents)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Collapsible.Panel>
      </Collapsible.Root>

      <div className="mt-4.5 grid grid-cols-[minmax(0,1.15fr)_minmax(260px,0.85fr)] gap-4.5">
        <section
          className="border-t-3 border-olive pt-3.25 [&_h2]:mb-2.25"
          aria-labelledby="upcoming-title"
        >
          <p className={eyebrowStyles}>Următoarele plăți</p>
          <h2 id="upcoming-title">De urmărit</h2>
          {upcoming.length > 0 ? (
            upcoming.map((payment) => (
              <button
                aria-haspopup="dialog"
                className={listButtonStyles}
                key={payment.allocationId}
                onClick={() => onOpenItem(payment.itemId)}
                type="button"
              >
                <span className="flex min-w-0 items-center gap-1.5">
                  <ItemIcon itemId={payment.itemId} size={16} />
                  <span>
                    {payment.itemLabel}
                    <small className="mt-0.5 block text-[0.68rem] text-muted">
                      {formatDate(payment.dueOn)}
                      {payment.overdue ? " · restant" : ""}
                    </small>
                  </span>
                  <ItemBrandIcon itemId={payment.itemId} />
                </span>
                <b className="ml-4 flex-none font-[750] tabular-nums">
                  {formatMoney(payment.amountCents)}
                  {payment.contingencyCents > 0 && (
                    <small className="mt-0.5 block text-right text-[0.68rem] font-medium text-muted">
                      + rezervă {formatMoney(payment.contingencyCents)}
                    </small>
                  )}
                </b>
              </button>
            ))
          ) : (
            <p className="text-[0.8rem] text-muted">Nu sunt plăți viitoare pentru acest filtru.</p>
          )}
        </section>
        <section
          className="border-t-3 border-reserve pt-3.25"
          aria-label="Sume fără termen sau nealocate"
        >
          <p className={eyebrowStyles}>În afara graficului</p>
          <h2>Fără termen / nealocat</h2>
          <strong className="mt-2.5 mb-1.5 block text-xl/[1.45] tabular-nums">
            {formatMoney(series.undated.totalCents)}
          </strong>
          <p className="text-[0.78rem] text-muted">
            Programarea acestor sume este necesară înainte de a le interpreta drept disponibilități
            lunare.
          </p>
        </section>
      </div>
    </section>
  );
}
