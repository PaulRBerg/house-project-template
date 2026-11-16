import {
  AirVent,
  Bath,
  BrickWall,
  CalendarPlus,
  Building2,
  Cable,
  ClipboardCheck,
  CookingPot,
  Cpu,
  Droplets,
  Folder,
  Hammer,
  HardHat,
  House,
  Lightbulb,
  MonitorSmartphone,
  Network,
  Paintbrush,
  PanelsTopLeft,
  Refrigerator,
  Ruler,
  Settings2,
  Shovel,
  Sofa,
  SolarPanel,
  Sprout,
  Trees,
  Truck,
  UtilityPole,
  type LucideIcon,
} from "lucide-react";

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  "professional-site": Ruler,
  "professional-control": ClipboardCheck,
  construction: HardHat,
  "construction-connections": Network,
  "construction-ground": Shovel,
  "construction-structure": Building2,
  "construction-roof": House,
  "construction-works": Hammer,
  rough: Hammer,
  "rough-connections": Network,
  "rough-site-utilities": UtilityPole,
  "rough-windows-doors": PanelsTopLeft,
  "rough-facade": BrickWall,
  "rough-electrical": Cable,
  "rough-hvac": AirVent,
  "rough-sanitary": Droplets,
  "rough-interior": PanelsTopLeft,
  finish: Paintbrush,
  "finish-equipment": Settings2,
  "finish-energy": SolarPanel,
  "finish-electrical": Lightbulb,
  "finish-bathrooms": Bath,
  "finish-kitchen-storage": CookingPot,
  "finish-surfaces": Paintbrush,
  "finish-site": Trees,
  move: Truck,
  "move-furniture": Sofa,
  "move-appliances": Refrigerator,
  "move-assets": MonitorSmartphone,
  "move-garden": Sprout,
  extras: CalendarPlus,
  "extra-furniture": Sofa,
  "extra-surfaces": Paintbrush,
  "extra-lighting": Lightbulb,
  "extra-systems": Cpu,
};

/** Whether a catalogue group has its own icon rather than the generic fallback. */
export function hasCategoryIcon(categoryId: string): boolean {
  return Object.hasOwn(CATEGORY_ICONS, categoryId);
}

/** Category icon tinted by the nearest `data-stage` ancestor. */
export function CategoryIcon({ categoryId, size = 16 }: { categoryId: string; size?: number }) {
  const Icon = (hasCategoryIcon(categoryId) ? CATEGORY_ICONS[categoryId] : undefined) ?? Folder;
  return <Icon aria-hidden="true" className="flex-none text-stage" size={size} />;
}
