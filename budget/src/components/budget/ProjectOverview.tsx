import { Tabs } from "@base-ui/react/tabs";
import { MapPin, Ruler } from "lucide-react";

import type { BudgetDocument, BudgetView } from "../../domain/index.js";
import { formatDate, formatMoney } from "../../ui/format.js";
import { StageIcon } from "../shared/StageIcon.js";
import { cn, eyebrowStyles, iconLabelStyles } from "../shared/styles.js";

export function ProjectOverview({
  view,
  project,
}: {
  view: BudgetView;
  project: BudgetDocument["project"];
}) {
  const summary = view.summary;
  const nextPayment = view.upcomingPayments[0];

  return (
    <section className="grid gap-4" aria-label="Privire de ansamblu financiară">
      <div className="grid grid-cols-[minmax(0,1.6fr)_minmax(280px,1fr)] items-end gap-x-10">
        <div>
          <span className={eyebrowStyles}>Rămas de plată</span>
          <strong className="block text-[3.6rem]/none font-[620] tracking-[-0.045em] tabular-nums">
            {formatMoney(summary.remainingCashForecastCents)}
          </strong>
          <p className="mt-3.5 text-[0.82rem] text-muted">
            din prognoza totală de{" "}
            <strong className="font-[660] text-ink tabular-nums">
              {formatMoney(summary.totalCashForecastCents)}
            </strong>
            {" · "}
            <strong className="font-[660] text-ink tabular-nums">
              {formatMoney(summary.actualPaidCents)}
            </strong>{" "}
            plătit până acum
          </p>
        </div>
        <div className="border-l-3 border-accent pl-5" aria-label="Următoarea plată">
          <span className={cn(eyebrowStyles, "text-accent")}>Următoarea plată</span>
          {nextPayment ? (
            <>
              <strong className="block text-[1.7rem]/none font-[640] tracking-[-0.03em] tabular-nums">
                {formatMoney(nextPayment.amountCents)}
              </strong>
              <p className="mt-2 text-[0.8rem] font-[640]">{nextPayment.itemLabel}</p>
              <p className="text-[0.74rem] text-muted">
                {formatDate(nextPayment.dueOn)}
                {nextPayment.overdue ? " · restantă" : ""}
              </p>
            </>
          ) : (
            <p className="mt-1 text-[0.8rem] text-muted">Nicio plată programată.</p>
          )}
        </div>
      </div>

      <dl
        className="m-0 flex flex-wrap gap-x-6 gap-y-1 border-t border-line pt-3.5 text-[0.8rem] text-muted"
        aria-label="Date despre proiect"
      >
        <div className={iconLabelStyles}>
          <MapPin aria-hidden="true" size={14} />
          <dt className="sr-only">Amplasament</dt>
          <dd className="m-0">{project.location}</dd>
        </div>
        <div className={iconLabelStyles}>
          <Ruler aria-hidden="true" size={14} />
          <dt className="sr-only">Suprafață construită desfășurată</dt>
          <dd className="m-0 tabular-nums">{project.builtAreaSqm} m² construiți desfășurați</dd>
        </div>
      </dl>
    </section>
  );
}

export function StageStrip({ view }: { view: BudgetView }) {
  const forecastTotal = view.timeline.reduce((sum, entry) => sum + entry.forecastCents, 0);
  const stages = view.timeline.map((entry) => ({
    entry,
    share: forecastTotal === 0 ? 1 / view.timeline.length : entry.forecastCents / forecastTotal,
    progress: entry.itemCount === 0 ? 0 : entry.completeItemCount / entry.itemCount,
  }));

  return (
    <section className="mt-7 grid gap-3.5" aria-label="Etapele proiectului">
      <div className="flex h-2.5 gap-1" aria-hidden="true">
        {stages.map(({ entry, share, progress }) => (
          <div
            className="min-w-10 overflow-hidden rounded-xs bg-stage-track"
            data-stage={entry.milestone.id}
            key={entry.milestone.id}
            style={{ flexGrow: share, flexBasis: 0 }}
          >
            <i className="block h-full bg-stage" style={{ width: `${progress * 100}%` }} />
          </div>
        ))}
      </div>
      <Tabs.List
        activateOnFocus
        aria-label="Etapele proiectului"
        className="grid grid-cols-4 gap-x-3"
        loopFocus
      >
        {view.hierarchy.map((group) => {
          const stage = stages.find(({ entry }) => entry.milestone.id === group.milestoneId);
          if (!stage) return null;
          const { entry, share } = stage;
          return (
            <Tabs.Tab
              aria-describedby={`stage-date-${group.id} stage-summary-${group.id}`}
              aria-label={group.label}
              className="grid min-w-0 grid-cols-[auto_1fr_auto] items-center gap-2.5 rounded-lg border border-transparent bg-transparent p-3 text-left hover:bg-stage-tint focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-stage data-active:border-stage/40 data-active:bg-stage-header"
              data-stage={entry.milestone.id}
              key={group.id}
              value={group.id}
            >
              <StageIcon milestoneId={entry.milestone.id} compact />
              <span className="min-w-0">
                <span className="block text-[0.8rem] font-[720]">{group.label}</span>
                <span className="block text-[0.7rem] text-muted" id={`stage-date-${group.id}`}>
                  până la {formatDate(entry.milestone.date)}
                </span>
              </span>
              <span className="text-right tabular-nums" id={`stage-summary-${group.id}`}>
                <strong className="block text-[0.84rem]">{formatMoney(entry.forecastCents)}</strong>
                <span className="text-[0.7rem] text-muted">
                  {entry.completeItemCount}/{entry.itemCount} gata · {Math.round(share * 100)}%
                </span>
              </span>
            </Tabs.Tab>
          );
        })}
      </Tabs.List>
    </section>
  );
}
