import type { BudgetItem } from "../../domain/index.js";
import { cn } from "./styles.js";

export function itemStatusLabel(item: Pick<BudgetItem, "ownership" | "completion">): string {
  if (item.ownership === "owned") return "Deja cumpărat";
  return item.completion.complete ? "Finalizat" : "Planificat";
}

/** Planned is the default state and stays quiet; owned and finished items earn a badge. */
export function ItemStatus({ item }: { item: Pick<BudgetItem, "ownership" | "completion"> }) {
  const owned = item.ownership === "owned";
  const complete = !owned && item.completion.complete;
  return (
    <span
      className={cn(
        "text-[0.62rem] leading-none font-[730] whitespace-nowrap",
        owned && "rounded-full bg-olive/14 px-1.75 py-0.5 text-olive",
        complete && "rounded-full bg-ink/8 px-1.75 py-0.5 text-ink",
        !owned && !complete && "text-muted",
      )}
    >
      {itemStatusLabel(item)}
    </span>
  );
}
