/** Top-level catalogue category shown when the URL names none. */
export const DEFAULT_CATEGORY_ID = "construction";
export const EXTRAS_CATEGORY_ID = "extras";

/** Stages whose budget table defaults to grouping items by room. */
const ROOM_GROUPING_CATEGORY_IDS: ReadonlySet<string> = new Set([
  "finish",
  "move",
  EXTRAS_CATEGORY_ID,
]);

export function supportsRoomGrouping(categoryId: string): boolean {
  return ROOM_GROUPING_CATEGORY_IDS.has(categoryId);
}

export const BUDGET_GROUPINGS = ["rooms", "categories"] as const;
export type BudgetGrouping = (typeof BUDGET_GROUPINGS)[number];
