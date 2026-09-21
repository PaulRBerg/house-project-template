const MONEY = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const MONEY_PRECISE = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const ROMANIAN_MONTHS = [
  "Ian",
  "Feb",
  "Mar",
  "Apr",
  "Mai",
  "Iun",
  "Iul",
  "Aug",
  "Sep",
  "Oct",
  "Noi",
  "Dec",
] as const;

export function formatMoney(cents: number, precise = false): string {
  return (precise ? MONEY_PRECISE : MONEY).format(cents / 100);
}

export function formatMoneyRange(estimateCents: number, forecastCents: number): string {
  const estimate = formatMoney(estimateCents);
  return estimateCents === forecastCents ? estimate : `${estimate}–${formatMoney(forecastCents)}`;
}

export function formatDate(value: string | undefined): string {
  if (!value) return "Fără termen";
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || month > 12) return value;
  if (day === undefined) return `${ROMANIAN_MONTHS[month - 1]} ${String(year).padStart(4, "0")}`;
  if (!day) return value;
  return `${day} ${ROMANIAN_MONTHS[month - 1]} ${String(year).padStart(4, "0")}`;
}

export function formatDateRange(start: string | undefined, end: string | undefined): string {
  if (start && end && start !== end) return `${formatDate(start)} → ${formatDate(end)}`;
  const date = start ?? end;
  return date ? formatDate(date) : "";
}

export function formatMonth(value: string): string {
  const [year, month] = value.split("-").map(Number);
  if (!year || !month || month > 12) return value;
  return `${ROMANIAN_MONTHS[month - 1]} ${String(year).padStart(4, "0")}`;
}

export function parseDateInput(value: string): string | null {
  const match = /^(\d{1,2}) (Ian|Feb|Mar|Apr|Mai|Iun|Iul|Aug|Sep|Oct|Noi|Dec) (\d{4})$/.exec(
    value.trim(),
  );
  if (!match) return null;
  const day = Number(match[1]);
  const month = ROMANIAN_MONTHS.indexOf(match[2] as (typeof ROMANIAN_MONTHS)[number]) + 1;
  const year = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function localCalendarDate(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseEuroToCents(value: string): number | null {
  const normalized = value.trim().replace(/[\s\u00A0\u202F]/g, "");
  if (!/^\d+(?:[.,]\d{1,2})?$/.test(normalized)) return null;
  const [whole = "0", fraction = ""] = normalized.replace(",", ".").split(".");
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  return Number.isSafeInteger(cents) ? cents : null;
}

export function formatMoneyInput(cents: number): string {
  return (cents / 100).toFixed(2);
}

export const BRIEF_STATUS_LABELS = {
  required: "obligatoriu",
  preferred: "preferat",
  phased: "etapizat",
  deferred: "amânat",
} as const;
