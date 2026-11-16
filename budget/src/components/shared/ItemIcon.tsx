import {
  AirVent,
  Archive,
  Armchair,
  Bath,
  Bed,
  BedDouble,
  BatteryCharging,
  Blocks,
  Building2,
  BrickWall,
  Cable,
  CarFront,
  ClipboardCheck,
  CookingPot,
  DoorClosed,
  DoorOpen,
  DoorStairwell,
  DraftingCompass,
  Drill,
  Fence,
  Footprints,
  GlassWater,
  Gauge,
  Hammer,
  Heater,
  House,
  LandPlot,
  Layers,
  MapPinned,
  Package,
  PaintRoller,
  Paintbrush,
  PanelsTopLeft,
  Pipette,
  PlugZap,
  Sofa,
  Sprout,
  SolarPanel,
  Table,
  Table2,
  ThermometerSnowflake,
  ThermometerSun,
  Umbrella,
  Wind,
  WashingMachine,
  type LucideIcon,
} from "lucide-react";
import { createElement } from "react";
import { siBosch } from "simple-icons";

import { cn } from "./styles.js";

// Keep this stable-ID map explicit: catalogue labels are prose, not UI identifiers.
const ITEM_ICONS: Record<string, LucideIcon> = {
  "topographic-survey": MapPinned,
  "geotechnical-study": Drill,
  "architecture-project": DraftingCompass,
  "structural-engineering": Building2,
  "mep-design": Cable,
  "permit-and-utility-admin": ClipboardCheck,
  "utility-connections": PlugZap,
  "foundation-concrete": LandPlot,
  "structural-frame": Blocks,
  "masonry-exterior": BrickWall,
  "construction-labour": Hammer,
  "roof-slab": Layers,
  "roof-covering": House,
  "windows-performance": PanelsTopLeft,
  "external-doors": DoorOpen,
  "facade-insulation": ThermometerSnowflake,
  "electrical-rough-in": Cable,
  "ventilation-ductwork": Wind,
  "underfloor-heating": Heater,
  "rough-plumbing": Pipette,
  "wet-room-waterproofing": Umbrella,
  "internal-plaster": PaintRoller,
  "floor-screeds": Layers,
  "heat-pump-system": ThermometerSun,
  "hrv-unit": AirVent,
  "solar-pv": SolarPanel,
  "commissioning-and-tests": Gauge,
  "bathroom-ground": Bath,
  "bathroom-upper": Bath,
  "kitchen-cabinetry": CookingPot,
  "fixed-wardrobes": Archive,
  "floor-finishes": PanelsTopLeft,
  "interior-paint": Paintbrush,
  "interior-doors": DoorClosed,
  "stair-finish": DoorStairwell,
  "terrace-paving": Footprints,
  "access-and-parking": CarFront,
  "perimeter-fence": Fence,
  "asset-sofa": Sofa,
  "dining-table": Table2,
  "master-bed": BedDouble,
  "child-bed-desk": Bed,
  "office-desk-sofa": Table,
  "oven-and-hob": CookingPot,
  dishwasher: GlassWater,
  "washing-machine": WashingMachine,
  "garden-lawn": Sprout,
  "garden-walkway": Footprints,
  "terrace-furniture": Armchair,
  "future-battery": BatteryCharging,
};

const ITEM_BRANDS: Record<string, typeof siBosch> = {
  dishwasher: siBosch,
};

/** Named fallback for catalogue items added before their icon mapping. */
const ITEM_ICON_FALLBACK = Package;

function ownValue<T>(map: Record<string, T>, key: string): T | undefined {
  return Object.hasOwn(map, key) ? map[key] : undefined;
}

export function ItemIcon({ itemId, size = 18 }: { itemId: string; size?: number }) {
  const Icon = ownValue(ITEM_ICONS, itemId) ?? ITEM_ICON_FALLBACK;
  return createElement(Icon, { "aria-hidden": true, className: "flex-none text-accent", size });
}

export function ItemBrandIcon({ itemId, size = 13 }: { itemId: string; size?: number }) {
  const brand = ownValue(ITEM_BRANDS, itemId);
  if (!brand) return null;
  return (
    <svg
      aria-hidden="true"
      className={cn("flex-none text-muted", "fill-current")}
      height={size}
      viewBox="0 0 24 24"
      width={size}
    >
      <path d={brand.path} />
    </svg>
  );
}
