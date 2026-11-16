/** Locale for user-facing text, search and ordering. */
export const UI_LOCALE = "ro";

/** Sums integer cents, failing loudly instead of silently losing precision. */
export function sumCents(values: Iterable<number>): number {
  let total = 0;
  for (const value of values) {
    total += value;
    if (!Number.isSafeInteger(total)) {
      throw new RangeError("Totalul monetar depășește limita sigură pentru cenți întregi.");
    }
  }
  return total;
}

/** Groups values by key, preserving their input order within each group. */
export function groupBy<T, K>(values: Iterable<T>, key: (value: T) => K): Map<K, T[]> {
  const groups = new Map<K, T[]>();
  for (const value of values) {
    const groupKey = key(value);
    const siblings = groups.get(groupKey);
    if (siblings) siblings.push(value);
    else groups.set(groupKey, [value]);
  }
  return groups;
}
