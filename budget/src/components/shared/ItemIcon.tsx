import {
  Armchair,
  BrickWall,
  Cable,
  CookingPot,
  Hammer,
  Package,
  PaintRoller,
  Pipette,
  Truck,
  type LucideIcon,
} from "lucide-react";
import { createElement } from "react";

// Stable demo catalogue IDs are explicit; labels remain editable content.
const ITEM_ICONS: Record<string, LucideIcon> = {
  foundation: Hammer,
  "wall-framing": BrickWall,
  "electrical-rough-in": Cable,
  "plumbing-rough-in": Pipette,
  "interior-finishes": PaintRoller,
  "kitchen-fixtures": CookingPot,
  "moving-services": Truck,
  "starter-furniture": Armchair,
};

export const ITEM_ICON_FALLBACK = Package;

function ownValue<T>(map: Record<string, T>, key: string): T | undefined {
  return Object.hasOwn(map, key) ? map[key] : undefined;
}

export function hasExplicitItemIcon(itemId: string): boolean {
  return ownValue(ITEM_ICONS, itemId) !== undefined;
}

export function ItemIcon({ itemId, size = 18 }: { itemId: string; size?: number }) {
  const Icon = ownValue(ITEM_ICONS, itemId) ?? ITEM_ICON_FALLBACK;
  return createElement(Icon, { "aria-hidden": true, className: "flex-none text-accent", size });
}
