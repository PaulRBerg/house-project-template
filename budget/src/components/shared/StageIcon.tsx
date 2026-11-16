import { BrickWall, CalendarPlus, Hammer, KeyRound, PackageOpen } from "lucide-react";

import type { Milestone } from "../../domain/index.js";
import { cn } from "./styles.js";

const STAGE_ICONS = {
  "la-rosu": BrickWall,
  "la-gri": Hammer,
  "la-cheie": KeyRound,
  "la-mutat": PackageOpen,
  extra: CalendarPlus,
};

export function StageIcon({
  milestoneId,
  compact = false,
}: {
  milestoneId: Milestone["id"];
  compact?: boolean;
}) {
  const Icon = STAGE_ICONS[milestoneId];
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex flex-none items-center justify-center border border-stage/16 bg-stage-tint text-stage",
        compact ? "size-7.25 rounded-[7px]" : "size-10.75 rounded-[11px]",
      )}
      data-stage={milestoneId}
    >
      <Icon size={compact ? 16 : 23} strokeWidth={1.8} />
    </span>
  );
}
