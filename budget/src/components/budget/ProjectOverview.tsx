import { CalendarClock, MapPin } from "lucide-react";

import type { BudgetDocument, BudgetView } from "../../domain/index.js";
import { formatDate, formatMoney } from "../../ui/format.js";
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
            din prognoza până la mutare de{" "}
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
        <div
          className="border-l-3 border-accent pl-5"
          aria-label="Date despre proiect"
          role="group"
        >
          <span className={cn(eyebrowStyles, "text-accent")}>Suprafață construită desfășurată</span>
          <strong className="block text-[1.7rem]/none font-[640] tracking-[-0.03em] tabular-nums">
            {project.builtAreaSqm} m²
          </strong>
          <p className={cn(iconLabelStyles, "mt-2 text-[0.8rem] text-muted")}>
            <MapPin aria-hidden="true" size={14} />
            {project.location}
          </p>
        </div>
      </div>

      <p className={cn(iconLabelStyles, "border-t border-line pt-3.5 text-[0.8rem] text-muted")}>
        <CalendarClock aria-hidden="true" size={14} />
        {nextPayment ? (
          <span>
            Următoarea plată:{" "}
            <strong className="font-[660] text-ink tabular-nums">
              {formatMoney(nextPayment.amountCents)}
            </strong>{" "}
            · {nextPayment.itemLabel} · {formatDate(nextPayment.dueOn)}
            {nextPayment.overdue ? " · restantă" : ""}
          </span>
        ) : (
          <span>Nicio plată programată.</span>
        )}
      </p>
    </section>
  );
}
