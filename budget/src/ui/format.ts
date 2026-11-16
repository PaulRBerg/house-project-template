import { UI_LOCALE } from "../domain/collections.js";
import { BPS_DENOMINATOR } from "../domain/schema.js";
import type { DerivedItem } from "../domain/selectors.js";

const PLURAL_RULES = new Intl.PluralRules(UI_LOCALE);
const PERCENT = new Intl.NumberFormat(UI_LOCALE, { style: "percent", maximumFractionDigits: 1 });

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
  if (day === undefined) return formatMonth(value);
  if (!day) return value;
  return `${day} ${formatMonth(value.slice(0, 7))}`;
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

export function localCalendarDate(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** Romanian noun form for a count: singular, plural, or "de" plural from 20 upwards. */
export function pluralNoun(count: number, forms: { one: string; other: string }): string {
  const rule = PLURAL_RULES.select(count);
  if (rule === "one") return forms.one;
  return rule === "few" ? forms.other : `de ${forms.other}`;
}

export function formatCount(count: number, forms: { one: string; other: string }): string {
  return `${count} ${pluralNoun(count, forms)}`;
}

/** Romanian percentage of a ratio, e.g. 0.1 → "10 %". */
export function formatPercent(ratio: number): string {
  return PERCENT.format(ratio);
}

export function formatBpsPercent(bps: number): string {
  return formatPercent(bps / BPS_DENOMINATOR);
}

/** Case-insensitive search query; empty when there is nothing to match. */
export function normalizeSearch(value: string): string {
  return value.trim().toLocaleLowerCase(UI_LOCALE);
}

/** Whether a label contains an already normalized, non-empty query. */
export function labelMatches(label: string, query: string): boolean {
  return query !== "" && label.toLocaleLowerCase(UI_LOCALE).includes(query);
}

/**
 * Item cost as shown in tables: the price actually paid once an owned or fully paid item is
 * settled, the estimate for an unpaid excluded or archived item, otherwise the
 * estimate-to-forecast range.
 */
export function formatItemCost(entry: DerivedItem): string {
  const paidPrice =
    entry.item.ownership === "owned"
      ? entry.active
        ? entry.totalCents
        : entry.estimateCents
      : entry.actualPaidCents > 0 && entry.remainingForecastCents === 0
        ? entry.actualPaidCents
        : undefined;
  if (paidPrice !== undefined) return formatMoney(paidPrice);
  return entry.active
    ? formatMoneyRange(entry.estimateCents, entry.forecastCents)
    : formatMoney(entry.estimateCents);
}
