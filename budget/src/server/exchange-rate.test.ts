import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ExchangeRateCache, ExchangeRateError } from "./exchange-rate.js";

function bnrXml(date: string, rate: string): string {
  return `<?xml version="1.0" encoding="utf-8"?>
<DataSet xmlns="http://www.bnr.ro/xsd">
  <Header><PublishingDate>${date}</PublishingDate></Header>
  <Body><Cube date="${date}"><Rate currency="EUR">${rate}</Rate></Cube></Body>
</DataSet>`;
}

function ecbXml(date: string, rate: string): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time='${date}'>
      <Cube currency='USD' rate='1.0865'/>
      <Cube currency='RON' rate='${rate}'/>
    </Cube>
  </Cube>
</gesmes:Envelope>`;
}

function xmlResponse(body: string): Response {
  return new Response(body, { status: 200, headers: { "Content-Type": "text/xml" } });
}

describe("ExchangeRateCache", () => {
  let directory: string;
  let cachePath: string;

  beforeEach(async () => {
    directory = await mkdtemp(join(tmpdir(), "house-template-exchange-rate-"));
    cachePath = join(directory, "exchange-rate.json");
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  it("returns a fresh cache hit without any network call", async () => {
    const fetchedAt = new Date("2026-09-15T08:00:00.000Z").toISOString();
    await writeFile(
      cachePath,
      JSON.stringify({
        ronPerEur: 5.26,
        rateDate: "2026-09-15",
        source: "BNR",
        sourceUrl: "https://www.bnr.ro/541-cursul-de-schimb",
        fetchedAt,
      }),
      "utf8",
    );
    const fetcher = vi.fn();
    const cache = new ExchangeRateCache({
      cachePath,
      fetcher,
      now: () => new Date("2026-09-16T08:00:00.000Z"),
    });
    const snapshot = await cache.read();
    expect(fetcher).not.toHaveBeenCalled();
    expect(snapshot).toMatchObject({ ronPerEur: 5.26, rateDate: "2026-09-15", stale: false });
  });

  it("refetches BNR once the cache has expired", async () => {
    await writeFile(
      cachePath,
      JSON.stringify({
        ronPerEur: 5.1,
        rateDate: "2026-09-01",
        source: "BNR",
        sourceUrl: "https://www.bnr.ro/541-cursul-de-schimb",
        fetchedAt: new Date("2026-09-01T08:00:00.000Z").toISOString(),
      }),
      "utf8",
    );
    const fetcher = vi.fn((url: string | URL | Request) => {
      expect(String(url)).toBe("https://curs.bnr.ro/nbrfxrates.xml");
      return Promise.resolve(xmlResponse(bnrXml("2026-09-18", "5.2644")));
    });
    const cache = new ExchangeRateCache({
      cachePath,
      fetcher,
      now: () => new Date("2026-09-18T08:00:00.000Z"),
    });
    const snapshot = await cache.read();
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(snapshot).toMatchObject({
      ronPerEur: 5.2644,
      rateDate: "2026-09-18",
      source: "BNR",
      stale: false,
    });
    const persisted = JSON.parse(await readFile(cachePath, "utf8")) as { ronPerEur: number };
    expect(persisted.ronPerEur).toBe(5.2644);
  });

  it("falls back to ECB when BNR fails", async () => {
    const fetcher = vi.fn((url: string | URL | Request) => {
      if (String(url).includes("bnr")) return Promise.reject(new Error("BNR unreachable"));
      return Promise.resolve(xmlResponse(ecbXml("2026-09-18", "5.2647")));
    });
    const cache = new ExchangeRateCache({
      cachePath,
      fetcher,
      now: () => new Date("2026-09-18T08:00:00.000Z"),
    });
    const snapshot = await cache.read();
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(snapshot).toMatchObject({
      ronPerEur: 5.2647,
      rateDate: "2026-09-18",
      source: "ECB",
      stale: false,
    });
  });

  it("returns the expired cache marked stale when both sources fail", async () => {
    await writeFile(
      cachePath,
      JSON.stringify({
        ronPerEur: 5.1,
        rateDate: "2026-09-01",
        source: "BNR",
        sourceUrl: "https://www.bnr.ro/541-cursul-de-schimb",
        fetchedAt: new Date("2026-09-01T08:00:00.000Z").toISOString(),
      }),
      "utf8",
    );
    const fetcher = vi.fn(() => Promise.reject(new Error("network down")));
    const cache = new ExchangeRateCache({
      cachePath,
      fetcher,
      now: () => new Date("2026-09-18T08:00:00.000Z"),
    });
    const snapshot = await cache.read();
    expect(snapshot).toMatchObject({ ronPerEur: 5.1, rateDate: "2026-09-01", stale: true });
  });

  it("throws ExchangeRateError when both sources fail and nothing is cached", async () => {
    const fetcher = vi.fn(() => Promise.reject(new Error("network down")));
    const cache = new ExchangeRateCache({ cachePath, fetcher, now: () => new Date() });
    await expect(cache.read()).rejects.toBeInstanceOf(ExchangeRateError);
  });

  it("shares one in-flight fetch across concurrent reads", async () => {
    let calls = 0;
    const fetcher = vi.fn(async (url: string | URL | Request) => {
      if (String(url).includes("bnr")) {
        calls += 1;
        await new Promise((resolve) => {
          setTimeout(resolve, 10);
        });
        return xmlResponse(bnrXml("2026-09-18", "5.2644"));
      }
      return xmlResponse(ecbXml("2026-09-18", "5.2647"));
    });
    const cache = new ExchangeRateCache({
      cachePath,
      fetcher,
      now: () => new Date("2026-09-18T08:00:00.000Z"),
    });
    const [first, second] = await Promise.all([cache.read(), cache.read()]);
    expect(calls).toBe(1);
    expect(first).toEqual(second);
  });

  it("treats a malformed cache file as absent", async () => {
    await mkdir(directory, { recursive: true });
    await writeFile(cachePath, JSON.stringify({ ronPerEur: "not-a-number" }), "utf8");
    const fetcher = vi.fn(() => Promise.resolve(xmlResponse(bnrXml("2026-09-18", "5.2644"))));
    const cache = new ExchangeRateCache({
      cachePath,
      fetcher,
      now: () => new Date("2026-09-18T08:00:00.000Z"),
    });
    const snapshot = await cache.read();
    expect(snapshot).toMatchObject({ ronPerEur: 5.2644, source: "BNR", stale: false });
  });
  it("keeps serving the stale value without retrying upstream right after a failure", async () => {
    await writeFile(
      cachePath,
      JSON.stringify({
        ronPerEur: 5.1,
        rateDate: "2026-09-01",
        source: "BNR",
        sourceUrl: "https://www.bnr.ro/541-cursul-de-schimb",
        fetchedAt: new Date("2026-09-01T08:00:00.000Z").toISOString(),
      }),
      "utf8",
    );
    const fetcher = vi.fn(() => Promise.reject(new Error("network down")));
    let clock = new Date("2026-09-18T08:00:00.000Z");
    const cache = new ExchangeRateCache({ cachePath, fetcher, now: () => clock });
    await cache.read();
    expect(fetcher).toHaveBeenCalledTimes(2);
    clock = new Date("2026-09-18T08:05:00.000Z");
    expect(await cache.read()).toMatchObject({ ronPerEur: 5.1, stale: true });
    expect(fetcher).toHaveBeenCalledTimes(2);
    clock = new Date("2026-09-18T08:20:00.000Z");
    await cache.read();
    expect(fetcher).toHaveBeenCalledTimes(4);
  });
});
