/** Sort sentinel that places undated entries after every dated one. */
const UNDATED_SORT_KEY = "9999-12-31";

export function monthKey(date: string): string {
  return date.slice(0, 7);
}

/** Earliest and latest ISO date or month, in one pass. */
export function dateSpan(dates: Iterable<string | undefined>): { start?: string; end?: string } {
  let start: string | undefined;
  let end: string | undefined;
  for (const date of dates) {
    if (date === undefined) continue;
    if (start === undefined || date < start) start = date;
    if (end === undefined || date > end) end = date;
  }
  return { ...(start === undefined ? {} : { start }), ...(end === undefined ? {} : { end }) };
}

/** Ascending date order with undated entries last. */
export function compareUndatedLast(left: string | undefined, right: string | undefined): number {
  return (left ?? UNDATED_SORT_KEY).localeCompare(right ?? UNDATED_SORT_KEY);
}
