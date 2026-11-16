import { Circle, CircleCheck } from "lucide-react";

import { formatMoney } from "../../ui/format.js";
import { cn } from "./styles.js";

export function PaymentProgress({
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
