import { Tabs } from "@base-ui/react/tabs";

import { EXTRA_MILESTONE_ID, sumCents, type BudgetView } from "../../domain/index.js";
import { formatDate, formatMoney, formatPercent } from "../../ui/format.js";
import { StageIcon } from "../shared/StageIcon.js";
import { cn } from "../shared/styles.js";

export function StageStrip({ view }: { view: BudgetView }) {
  const initialStages = view.timeline.filter((entry) => entry.milestone.id !== EXTRA_MILESTONE_ID);
  const forecastTotal = sumCents(initialStages.map((entry) => entry.forecastCents));
  const stages = view.timeline.map((entry) => ({
    entry,
    share: forecastTotal === 0 ? 1 / initialStages.length : entry.forecastCents / forecastTotal,
    progress: entry.itemCount === 0 ? 0 : entry.completeItemCount / entry.itemCount,
  }));

  return (
    <section className="mt-7 grid gap-3.5" aria-label="Etapele proiectului">
      <div className="flex h-2.5 gap-1" aria-hidden="true">
        {stages
          .filter(({ entry }) => entry.milestone.id !== EXTRA_MILESTONE_ID)
          .map(({ entry, share, progress }) => (
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
        className="grid auto-cols-fr grid-flow-col gap-x-3"
        loopFocus
      >
        {view.hierarchy.map((group) => {
          const stage = stages.find(({ entry }) => entry.milestone.id === group.milestoneId);
          if (!stage) return null;
          const { entry, share } = stage;
          const isExtra = entry.milestone.id === EXTRA_MILESTONE_ID;
          return (
            <Tabs.Tab
              aria-describedby={`stage-date-${group.id} stage-summary-${group.id}`}
              aria-label={group.label}
              className={cn(
                "grid min-w-0 grid-cols-[auto_1fr] items-center gap-x-2.5 gap-y-2 rounded-lg border border-transparent bg-transparent p-3 text-left hover:bg-stage-tint focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-stage data-active:border-stage/40 data-active:bg-stage-header",
                isExtra && "border-dashed border-stage/30",
              )}
              data-stage={entry.milestone.id}
              key={group.id}
              value={group.id}
            >
              <StageIcon milestoneId={entry.milestone.id} compact />
              <span className="min-w-0">
                <span className="block text-[0.8rem] font-[720]">{group.label}</span>
                <span className="block text-[0.7rem] text-muted" id={`stage-date-${group.id}`}>
                  {entry.milestone.startDate
                    ? `${formatDate(entry.milestone.startDate)} – `
                    : "până la "}
                  {formatDate(entry.milestone.date)}
                </span>
              </span>
              <span className="col-start-2 tabular-nums" id={`stage-summary-${group.id}`}>
                <strong className="block text-[0.84rem]">{formatMoney(entry.forecastCents)}</strong>
                <span className="text-[0.7rem] text-muted">
                  {entry.completeItemCount}/{entry.itemCount} gata ·{" "}
                  {isExtra ? "buget separat" : formatPercent(Math.round(share * 100) / 100)}
                </span>
              </span>
            </Tabs.Tab>
          );
        })}
      </Tabs.List>
    </section>
  );
}
