export const BUDGET_AREAS = [
  { id: "whole-house", label: "Întreaga casă" },
  { id: "G-HALL", label: "Hol de intrare" },
  { id: "G-LIV", label: "Living și dining" },
  { id: "G-KIT", label: "Bucătărie" },
  { id: "G-OFF", label: "Birou / cameră de oaspeți" },
  { id: "G-BATH", label: "Baie parter" },
  { id: "G-TECH", label: "Cameră tehnică și spălătorie" },
  { id: "G-STAIR", label: "Scară" },
  { id: "bathrooms-common", label: "Băi — comun" },
  { id: "U-LOBBY", label: "Hol etaj" },
  { id: "U-MBED", label: "Dormitor matrimonial" },
  { id: "U-CHILD", label: "Camera copilului" },
  { id: "U-BATH", label: "Baie etaj" },
  { id: "bedrooms-common", label: "Dormitoare — comun" },
  { id: "outdoor-terrace", label: "Terasă" },
  { id: "outdoor-garden", label: "Grădină" },
  { id: "outdoor-access", label: "Acces auto și servicii exterioare" },
  { id: "outdoor-common", label: "Exterior — comun" },
  { id: "unassigned", label: "Amplasare de stabilit" },
] as const;

export type BudgetArea = (typeof BUDGET_AREAS)[number];
export type BudgetAreaId = BudgetArea["id"];

export const BUDGET_AREA_IDS = BUDGET_AREAS.map((area) => area.id) as unknown as readonly [
  BudgetAreaId,
  ...BudgetAreaId[],
];

export const FALLBACK_BUDGET_AREA_ID = "unassigned" satisfies BudgetAreaId;

/** Presentation area of an item; items without one belong to the fallback area. */
export function itemAreaId(item: { areaId?: BudgetAreaId | undefined }): BudgetAreaId {
  return item.areaId ?? FALLBACK_BUDGET_AREA_ID;
}
