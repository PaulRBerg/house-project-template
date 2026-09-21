export const BUDGET_AREAS = [
  { id: "whole-house", label: "Whole house" },
  { id: "living-room", label: "Living room" },
  { id: "kitchen", label: "Kitchen" },
  { id: "bedroom", label: "Bedroom" },
  { id: "bathroom", label: "Bathroom" },
  { id: "utility-room", label: "Utility room" },
  { id: "outdoor", label: "Outdoor" },
  { id: "unassigned", label: "To be assigned" },
] as const;

export type BudgetArea = (typeof BUDGET_AREAS)[number];
export type BudgetAreaId = BudgetArea["id"];

export const BUDGET_AREA_IDS = BUDGET_AREAS.map((area) => area.id) as unknown as readonly [
  BudgetAreaId,
  ...BudgetAreaId[],
];

export const FALLBACK_BUDGET_AREA_ID = "unassigned" satisfies BudgetAreaId;

export function isBudgetAreaId(value: string): value is BudgetAreaId {
  return BUDGET_AREAS.some((area) => area.id === value);
}
