import { Folder, HardHat, Hammer, Paintbrush, Truck, type LucideIcon } from "lucide-react";

import { cn } from "./styles.js";

const CATEGORY_STAGES: Record<string, string> = {
  construction: "la-rosu",
  rough: "la-gri",
  finish: "la-cheie",
  move: "la-mutat",
};

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  construction: HardHat,
  rough: Hammer,
  finish: Paintbrush,
  move: Truck,
};

/** Stage token that colors a top-level category, for `data-stage` on its tab and summary. */
export function categoryStage(categoryId: string): string | undefined {
  return CATEGORY_STAGES[categoryId];
}

export function CategoryIcon({ categoryId, size = 16 }: { categoryId: string; size?: number }) {
  const Icon = CATEGORY_ICONS[categoryId] ?? Folder;
  const stage = categoryStage(categoryId);
  return (
    <Icon
      aria-hidden="true"
      className={cn("flex-none", stage ? "text-stage" : "text-accent")}
      data-stage={stage}
      size={size}
    />
  );
}
