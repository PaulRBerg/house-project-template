import { Collapsible } from "@base-ui/react/collapsible";
import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import {
  CalendarClock,
  ChartColumnIncreasing,
  ChevronDown,
  Clock3,
  TrendingUp,
} from "lucide-react";
import { useMemo, useState } from "react";

import type { CashFlowAllocation } from "../../domain/selectors.js";
import { formatDate, formatMoney } from "../../ui/format.js";
import { ItemIcon } from "../shared/ItemIcon.js";
import {
  cn,
  iconLabelStyles,
  segmentedGroupStyles,
  segmentedToggleStyles,
} from "../shared/styles.js";
import {
  aggregatePlanningFlows,
  makePlanningPeriods,
  planningMonthRange,
  type PeriodGranularity,
  type PlanningFlow,
} from "./planning-data.js";
import type { PlanningViewProps } from "./types.js";

function allocationLabel(allocation: CashFlowAllocation): string {
  if (allocation.kind === "actual") return "Plătit";
  if (allocation.kind === "contingency") return "Rezervă";
  if (allocation.kind === "unallocated") return "Nealocat";
  return "Planificat";
}

function Chart({
  flows,
  selectedKey,
  onSelect,
}: {
  flows: PlanningFlow[];
  selectedKey: string;
  onSelect: (key: string) => void;
}) {
  const width = Math.max(680, flows.length * 58 + 36);
  const height = 250;
  const baseline = 196;
  const top = 28;
  const max = Math.max(1, ...flows.map((flow) => flow.totalCents));
  const points = flows.map((flow, index) => ({
    x: 38 + index * 58 + 21,
    cumulative: flows.slice(0, index + 1).reduce((sum, entry) => sum + entry.totalCents, 0),
    flow,
  }));
  const maxCumulative = Math.max(1, ...points.map((point) => point.cumulative));
  const line = points
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"}${point.x} ${baseline - (point.cumulative / maxCumulative) * (baseline - top)}`,
    )
    .join(" ");
  const first = points[0];
  const last = points.at(-1);
  const area = first && last ? `${line} L${last.x} ${baseline} L${first.x} ${baseline} Z` : "";

  return (
    <div
      className="max-w-full overflow-x-auto border-b border-line [overscroll-behavior-inline:contain]"
      aria-label="Grafic de flux de numerar, derulabil pe orizontală"
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
        <text className="fill-muted font-planning text-[10px] tabular-nums" x="2" y={top + 5}>
          {formatMoney(max)}
        </text>
        <text className="fill-muted font-planning text-[10px] tabular-nums" x="2" y={baseline + 4}>
          0 EUR
        </text>
        <text
          className="fill-ink font-planning text-[10px] font-bold tabular-nums"
          textAnchor="end"
          x={width - 2}
          y={top + 5}
        >
          {formatMoney(maxCumulative)}
        </text>
        <text
          className="fill-ink font-planning text-[10px] font-bold tabular-nums"
          textAnchor="end"
          x={width - 2}
          y={baseline + 4}
        >
          0 EUR
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
        {flows.map((flow, index) => {
          const x = 38 + index * 58;
          const stacks = [
            [flow.actualCents, "actual"],
            [flow.scheduledCents + flow.unallocatedCents, "planned"],
            [flow.contingencyCents, "reserve"],
          ] as const;
          let y = baseline;
          return (
            <g className="group/chart" data-selected={flow.month === selectedKey} key={flow.month}>
              <title>{`${flow.label}: ${formatMoney(flow.totalCents)}`}</title>
              {stacks.map(([amount, kind]) => {
                const barHeight = (amount / max) * (baseline - top);
                y -= barHeight;
                return amount > 0 ? (
                  <rect
                    className={cn(
                      "transition-opacity duration-140 ease-[ease] group-focus-within/chart:opacity-80 group-hover/chart:opacity-80 motion-reduce:transition-none forced-colors:forced-color-adjust-none",
                      { actual: "fill-accent", planned: "fill-olive", reserve: "fill-reserve" }[
                        kind
                      ],
                    )}
                    height={barHeight}
                    key={kind}
                    rx="2"
                    width="42"
                    x={x}
                    y={y}
                  />
                ) : null;
              })}
              <rect
                aria-label={`${flow.label}: plătit ${formatMoney(flow.actualCents)}, obligație de bază ${formatMoney(flow.scheduledCents + flow.unallocatedCents)}, rezervă ${formatMoney(flow.contingencyCents)}`}
                className="cursor-pointer fill-transparent outline-none focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-accent"
                height="220"
                onClick={() => onSelect(flow.month)}
                onFocus={() => onSelect(flow.month)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(flow.month);
                  }
                }}
                role="button"
                rx="5"
                tabIndex={0}
                width="48"
                x={x - 3}
                y="8"
              >
                <title>{`${flow.label}. Plătit ${formatMoney(flow.actualCents)}. Planificat ${formatMoney(flow.scheduledCents + flow.unallocatedCents)}. Rezervă ${formatMoney(flow.contingencyCents)}.`}</title>
              </rect>
              <text
                className="fill-muted font-planning text-[10px] font-[650] group-data-[selected=true]/chart:fill-ink"
                textAnchor="middle"
                x={x + 21}
                y="220"
              >
                {flow.label}
              </text>
              {flow.month === selectedKey && (
                <rect className="fill-accent" height="3" rx="1.5" width="28" x={x + 7} y="226" />
              )}
            </g>
          );
        })}
        {points.length > 0 && (
          <path
            className="fill-none stroke-ink stroke-[2.25] [stroke-linecap:round] [stroke-linejoin:round]"
            d={line}
          />
        )}
        {points.map((point) => (
          <circle
            className="fill-surface stroke-ink stroke-2"
            cx={point.x}
            cy={baseline - (point.cumulative / maxCumulative) * (baseline - top)}
            key={point.flow.month}
            r="3.5"
          />
        ))}
      </svg>
    </div>
  );
}

export function CashFlowView({
  document,
  view,
  milestoneId = "all",
  onOpenItem,
}: PlanningViewProps) {
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
      ...view.allocations.flatMap((allocation) => (allocation.date ? [allocation.date] : [])),
      ...document.milestones.map((milestone) => milestone.date),
    ],
    [document.milestones, view.allocations],
  );
  const range = useMemo(() => planningMonthRange(dates), [dates]);
  const monthPeriods = useMemo(
    () => makePlanningPeriods(range.startMonth, range.endMonth, "month"),
    [range.endMonth, range.startMonth],
  );
  const periods = useMemo(
    () => makePlanningPeriods(range.startMonth, range.endMonth, granularity),
    [granularity, range.endMonth, range.startMonth],
  );
  const monthSeries = useMemo(
    () => aggregatePlanningFlows(view.allocations, monthPeriods, visibleItemIds),
    [monthPeriods, view.allocations, visibleItemIds],
  );
  const series = useMemo(
    () => aggregatePlanningFlows(view.allocations, periods, visibleItemIds),
    [periods, view.allocations, visibleItemIds],
  );
  const [selectedKey, setSelectedKey] = useState<string | undefined>();
  const selected =
    series.flows.find((flow) => flow.month === selectedKey) ??
    series.flows.find((flow) => flow.totalCents > 0) ??
    series.flows[0];
  const largestMonth = [...monthSeries.flows].sort(
    (left, right) => right.totalCents - left.totalCents,
  )[0];
  const selectedIndex = selected
    ? series.flows.findIndex((flow) => flow.month === selected.month)
    : -1;
  const selectedCumulative = series.flows
    .slice(0, selectedIndex + 1)
    .reduce((sum, flow) => sum + flow.totalCents, 0);
  const datedTotal = series.flows.reduce((sum, flow) => sum + flow.totalCents, 0);
  const allUpcoming = view.upcomingPayments.filter((payment) => visibleItemIds.has(payment.itemId));
  const upcoming = allUpcoming.slice(0, 4);

  return (
    <section
      className="max-w-full font-planning text-ink [&_h2]:text-[clamp(1.55rem,2vw,2.25rem)]/none [&_h2]:font-[650] [&_h2]:tracking-[-0.04em] [&_h3]:text-base/[1.45] [&_h3]:font-[650]"
      aria-labelledby="cashflow-title"
    >
      <header className="mb-5 flex items-end justify-between gap-6">
        <div>
          <p className="mb-1.75 text-[0.68rem] font-[760] tracking-[0.13em] text-olive uppercase">
            Ritm de finanțare
          </p>
          <h2 id="cashflow-title" className={iconLabelStyles}>
            <ChartColumnIncreasing aria-hidden="true" size={25} /> Fluxul de numerar
          </h2>
          <p className="mt-2.5 text-[0.9rem] text-muted">
            {milestoneId === "all" ? "Toate jaloanele" : "Jalon filtrat"} ·{" "}
            {formatMoney(datedTotal)} cu dată stabilită
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
      >
        <div className="flex min-h-24 flex-col px-4.5 py-3.5">
          <span className={cn("text-[0.71rem] text-muted", iconLabelStyles)}>
            <TrendingUp aria-hidden="true" size={16} /> Vârf de numerar
          </span>
          <strong className="mt-1.5 mb-0.5 text-[1.45rem] tracking-[-0.04em] tabular-nums">
            {largestMonth ? formatMoney(largestMonth.totalCents) : formatMoney(0)}
          </strong>
          <small className="text-[0.71rem] text-muted">
            {largestMonth?.label ?? "Fără plăți datate"}
          </small>
        </div>
        <div className="flex min-h-24 flex-col px-4.5 py-3.5">
          <span className={cn("text-[0.71rem] text-muted", iconLabelStyles)}>
            <CalendarClock aria-hidden="true" size={16} /> Plăți viitoare
          </span>
          <strong className="mt-1.5 mb-0.5 text-[1.45rem] tracking-[-0.04em] tabular-nums">
            {allUpcoming.length}
          </strong>
          <small className="text-[0.71rem] text-muted">
            {allUpcoming.length === 1 ? "element în filtru" : "elemente în filtru"}
          </small>
        </div>
        <div className="flex min-h-24 flex-col px-4.5 py-3.5">
          <span className={cn("text-[0.71rem] text-muted", iconLabelStyles)}>
            <Clock3 aria-hidden="true" size={16} /> Fără termen
          </span>
          <strong className="mt-1.5 mb-0.5 text-[1.45rem] tracking-[-0.04em] tabular-nums">
            {formatMoney(series.undated.totalCents)}
          </strong>
          <small className="text-[0.71rem] text-muted">nealocat în coloanele datate</small>
        </div>
      </div>

      <div
        className="mb-3.25 flex flex-wrap items-center gap-x-4.5 gap-y-2.5 text-[0.76rem] text-muted"
        aria-label="Legendă flux de numerar"
      >
        <span className="inline-flex items-center gap-1.75">
          <i className="inline-block size-2.25 rounded-full bg-accent forced-colors:forced-color-adjust-none" />
          Plătit
        </span>
        <span className="inline-flex items-center gap-1.75">
          <i className="inline-block size-2.25 rounded-full bg-olive forced-colors:forced-color-adjust-none" />
          Obligație de bază
        </span>
        <span className="inline-flex items-center gap-1.75">
          <i className="inline-block size-2.25 rounded-full bg-reserve forced-colors:forced-color-adjust-none" />
          Rezervă
        </span>
        <em className="text-[0.72rem] text-muted not-italic">
          Barele folosesc scara din stânga; linia cumulată, scara din dreapta.
        </em>
      </div>

      {series.flows.length > 0 ? (
        <Chart flows={series.flows} onSelect={setSelectedKey} selectedKey={selected?.month ?? ""} />
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
            <p className="mb-1.75 text-[0.68rem] font-[760] tracking-[0.13em] text-olive uppercase">
              Detaliu perioadă
            </p>
            <h3>{selected.label}</h3>
          </div>
          <dl className="m-0 grid grid-cols-5">
            <div>
              <dt className="text-[0.68rem] text-muted">Plătit</dt>
              <dd className="mt-1.5 text-[0.86rem] font-[750] tabular-nums">
                {formatMoney(selected.actualCents)}
              </dd>
            </div>
            <div>
              <dt className="text-[0.68rem] text-muted">Obligație de bază</dt>
              <dd className="mt-1.5 text-[0.86rem] font-[750] tabular-nums">
                {formatMoney(selected.scheduledCents + selected.unallocatedCents)}
              </dd>
            </div>
            <div>
              <dt className="text-[0.68rem] text-muted">Rezervă</dt>
              <dd className="mt-1.5 text-[0.86rem] font-[750] tabular-nums">
                {formatMoney(selected.contingencyCents)}
              </dd>
            </div>
            <div>
              <dt className="text-[0.68rem] text-muted">Total</dt>
              <dd className="mt-1.5 text-[0.86rem] font-[750] tabular-nums">
                {formatMoney(selected.totalCents)}
              </dd>
            </div>
            <div>
              <dt className="text-[0.68rem] text-muted">Cumul până aici</dt>
              <dd className="mt-1.5 text-[0.86rem] font-[750] tabular-nums">
                {formatMoney(selectedCumulative)}
              </dd>
            </div>
          </dl>
          <div className="col-span-full grid">
            {selected.allocations.length > 0 ? (
              selected.allocations.map((allocation) => (
                <button
                  aria-haspopup="dialog"
                  className="flex min-h-11 w-full cursor-pointer items-center justify-between border-0 border-t border-line bg-transparent px-0 py-1.75 text-left text-[0.8rem] hover:bg-canvas/55"
                  key={allocation.id}
                  onClick={() => onOpenItem(allocation.itemId)}
                  type="button"
                >
                  <span className="min-w-0">
                    <b className="ml-0 flex items-center gap-1.5 text-[0.78rem] font-[750] tabular-nums">
                      <ItemIcon itemId={allocation.itemId} size={16} />
                      {view.items.find((entry) => entry.item.id === allocation.itemId)?.item
                        .label ?? "Element"}
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
                  <th
                    className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap"
                    scope="col"
                  >
                    Lună
                  </th>
                  <th
                    className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap"
                    scope="col"
                  >
                    Plătit
                  </th>
                  <th
                    className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap"
                    scope="col"
                  >
                    Obligație
                  </th>
                  <th
                    className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap"
                    scope="col"
                  >
                    Rezervă
                  </th>
                  <th
                    className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap"
                    scope="col"
                  >
                    Total
                  </th>
                  <th
                    className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap"
                    scope="col"
                  >
                    Cumul
                  </th>
                </tr>
              </thead>
              <tbody>
                {monthSeries.flows.map((flow, index) => {
                  const cumulative = monthSeries.flows
                    .slice(0, index + 1)
                    .reduce((sum, entry) => sum + entry.totalCents, 0);
                  return (
                    <tr key={flow.month}>
                      <th
                        className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap"
                        scope="row"
                      >
                        {flow.label}
                      </th>
                      <td className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap">
                        {formatMoney(flow.actualCents)}
                      </td>
                      <td className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap">
                        {formatMoney(flow.scheduledCents + flow.unallocatedCents)}
                      </td>
                      <td className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap">
                        {formatMoney(flow.contingencyCents)}
                      </td>
                      <td className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap">
                        {formatMoney(flow.totalCents)}
                      </td>
                      <td className="border-b border-line px-2.5 py-2 text-right whitespace-nowrap">
                        {formatMoney(cumulative)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Collapsible.Panel>
      </Collapsible.Root>

      <div className="mt-4.5 grid grid-cols-[minmax(0,1.15fr)_minmax(260px,0.85fr)] gap-4.5">
        <section
          className="border-t-3 border-olive pt-3.25 [&_h3]:mb-2.25"
          aria-labelledby="upcoming-title"
        >
          <p className="mb-1.75 text-[0.68rem] font-[760] tracking-[0.13em] text-olive uppercase">
            Următoarele plăți
          </p>
          <h3 id="upcoming-title">De urmărit</h3>
          {upcoming.length > 0 ? (
            upcoming.map((payment) => (
              <button
                aria-haspopup="dialog"
                className="flex min-h-11 w-full cursor-pointer items-center justify-between border-0 border-t border-line bg-transparent px-0 py-1.75 text-left text-[0.8rem] hover:bg-canvas/55"
                key={payment.allocationId}
                onClick={() => onOpenItem(payment.itemId)}
                type="button"
              >
                <span className="flex min-w-0 items-center gap-1.5">
                  <ItemIcon itemId={payment.itemId} size={16} />
                  <span>
                    {payment.itemLabel}
                    <small className="mt-0.5 block text-[0.68rem] text-muted">
                      {payment.dueOn ? formatDate(payment.dueOn) : "Fără termen"}
                      {payment.overdue ? " · restant" : ""}
                    </small>
                  </span>
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
          <p className="mb-1.75 text-[0.68rem] font-[760] tracking-[0.13em] text-olive uppercase">
            În afara graficului
          </p>
          <h3>Fără termen / nealocat</h3>
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
