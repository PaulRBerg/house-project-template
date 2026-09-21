const MILLISECONDS_PER_DAY = 86_400_000;

export function isoDateToEpochDay(date: string): number {
  const [year, month, day = 1] = date.split("-").map(Number);
  if (year === undefined || month === undefined || day === undefined) {
    throw new Error(`Dată sau lună ISO invalidă: ${date}`);
  }
  return Math.trunc(Date.UTC(year, month - 1, day) / MILLISECONDS_PER_DAY);
}

export function daysBetween(from: string, to: string): number {
  return isoDateToEpochDay(to) - isoDateToEpochDay(from);
}

export function monthKey(date: string): string {
  return date.slice(0, 7);
}
