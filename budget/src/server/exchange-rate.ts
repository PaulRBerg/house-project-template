import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

import type { z } from "zod";

import { exchangeRateSchema, type ExchangeRate } from "../api/contracts.js";

const cachedRateSchema = exchangeRateSchema.omit({ stale: true });
type CachedRate = z.infer<typeof cachedRateSchema>;

export class ExchangeRateError extends Error {
  readonly code = "UNAVAILABLE";

  constructor(message: string) {
    super(message);
    this.name = "ExchangeRateError";
  }
}

export interface ExchangeRateCacheOptions {
  cachePath: string;
  maxAgeMs?: number;
  fetcher?: typeof fetch;
  now?: () => Date;
}

const DEFAULT_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
// After both feeds fail, keep serving the stale value instead of retrying on every request.
const RETRY_DELAY_MS = 15 * 60 * 1000;
const FETCH_TIMEOUT_MS = 10_000;

const BNR_XML_URL = "https://curs.bnr.ro/nbrfxrates.xml";
const BNR_PAGE_URL = "https://www.bnr.ro/541-cursul-de-schimb";
const ECB_XML_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml";
const ECB_PAGE_URL =
  "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html";

function isIsoCalendarDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function parsePositiveRate(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

/**
 * Fetches BNR's or ECB's daily-rate XML and shares one in-flight refresh across concurrent
 * readers, so the app never hits either upstream more than once every `maxAgeMs`.
 */
export class ExchangeRateCache {
  private readonly cachePath: string;
  private readonly maxAgeMs: number;
  private readonly fetcher: typeof fetch;
  private readonly now: () => Date;
  private inFlight: Promise<ExchangeRate> | undefined;
  private retryNotBefore = 0;

  constructor({
    cachePath,
    maxAgeMs = DEFAULT_MAX_AGE_MS,
    fetcher = fetch,
    now = () => new Date(),
  }: ExchangeRateCacheOptions) {
    this.cachePath = cachePath;
    this.maxAgeMs = maxAgeMs;
    this.fetcher = fetcher;
    this.now = now;
  }

  read(): Promise<ExchangeRate> {
    if (this.inFlight) return this.inFlight;
    const operation = this.readInternal().finally(() => {
      this.inFlight = undefined;
    });
    this.inFlight = operation;
    return operation;
  }

  private async readInternal(): Promise<ExchangeRate> {
    const cached = await this.readCache();
    const nowMs = this.now().getTime();
    if (cached && nowMs - Date.parse(cached.fetchedAt) < this.maxAgeMs) {
      return { ...cached, stale: false };
    }
    if (cached && nowMs < this.retryNotBefore) return { ...cached, stale: true };
    return this.refresh(cached);
  }

  private async refresh(cached: CachedRate | undefined): Promise<ExchangeRate> {
    const fetched = (await this.fetchFromBnr()) ?? (await this.fetchFromEcb());
    if (fetched) {
      await this.writeCache(fetched);
      return { ...fetched, stale: false };
    }
    this.retryNotBefore = this.now().getTime() + RETRY_DELAY_MS;
    if (cached) return { ...cached, stale: true };
    throw new ExchangeRateError(
      "Cursul de schimb BNR/BCE nu a putut fi obținut, iar în cache nu există nicio valoare anterioară.",
    );
  }

  private async fetchFromBnr(): Promise<CachedRate | undefined> {
    const xml = await this.fetchXml(BNR_XML_URL);
    if (!xml) return undefined;
    const dateMatch = /<Cube date=["'](\d{4}-\d{2}-\d{2})["']/.exec(xml);
    const rateMatch = /<Rate currency=["']EUR["']>([\d.]+)<\/Rate>/.exec(xml);
    return this.buildSnapshot(dateMatch?.[1], rateMatch?.[1], "BNR", BNR_PAGE_URL);
  }

  private async fetchFromEcb(): Promise<CachedRate | undefined> {
    const xml = await this.fetchXml(ECB_XML_URL);
    if (!xml) return undefined;
    const dateMatch = /<Cube time=["'](\d{4}-\d{2}-\d{2})["']/.exec(xml);
    const rateMatch = /<Cube currency=["']RON["'] rate=["']([\d.]+)["']/.exec(xml);
    return this.buildSnapshot(dateMatch?.[1], rateMatch?.[1], "ECB", ECB_PAGE_URL);
  }

  private buildSnapshot(
    rateDate: string | undefined,
    rateValue: string | undefined,
    source: ExchangeRate["source"],
    sourceUrl: string,
  ): CachedRate | undefined {
    const ronPerEur = parsePositiveRate(rateValue);
    if (!rateDate || !isIsoCalendarDate(rateDate) || ronPerEur === undefined) return undefined;
    return { ronPerEur, rateDate, source, sourceUrl, fetchedAt: this.now().toISOString() };
  }

  private async fetchXml(url: string): Promise<string | undefined> {
    try {
      const response = await this.fetcher(url, { signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) });
      if (!response.ok) return undefined;
      return await response.text();
    } catch {
      return undefined;
    }
  }

  private async readCache(): Promise<CachedRate | undefined> {
    try {
      const result = cachedRateSchema.safeParse(JSON.parse(await readFile(this.cachePath, "utf8")));
      return result.success ? result.data : undefined;
    } catch {
      return undefined;
    }
  }

  private async writeCache(rate: CachedRate): Promise<void> {
    await mkdir(dirname(this.cachePath), { recursive: true });
    const temporaryPath = `${this.cachePath}.${process.pid}.${randomUUID()}.tmp`;
    await writeFile(temporaryPath, JSON.stringify(rate), "utf8");
    await rename(temporaryPath, this.cachePath);
  }
}
