import { rm } from "node:fs/promises";
import { createServer, request as httpRequest } from "node:http";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { loadBudget } from "../api/client.js";
import { createTempBudgetFile } from "../test/budget-file.js";
import { makeDocument } from "../test/builders.js";
import { createBudgetApiMiddleware } from "./api-middleware.js";
import { BudgetFileReader } from "./budget-file-reader.js";
import { ExchangeRateCache } from "./exchange-rate.js";

interface TestApiServer {
  documentPath: string;
  baseUrl: string;
  close: () => Promise<void>;
}

/** Serves the API middleware over a temporary budget file on an ephemeral loopback port. */
async function startApiServer(
  prefix: string,
  buildExchangeRates?: (directory: string) => ExchangeRateCache,
): Promise<TestApiServer> {
  const { directory, documentPath } = await createTempBudgetFile(prefix);
  const middleware = createBudgetApiMiddleware(new BudgetFileReader({ documentPath }), {
    exchangeRates: buildExchangeRates?.(directory),
  });
  const server = createServer((request, response) => {
    middleware(request, response, () => {
      response.statusCode = 404;
      response.end();
    });
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Adresa de test lipsește");
  return {
    documentPath,
    baseUrl: `http://127.0.0.1:${address.port}`,
    async close() {
      await new Promise<void>((resolve, reject) => {
        server.close((error) => (error ? reject(error) : resolve()));
      });
      await rm(directory, { recursive: true, force: true });
    },
  };
}

describe("budget API middleware", () => {
  let api: TestApiServer;
  let documentPath: string;
  let baseUrl: string;

  beforeEach(async () => {
    api = await startApiServer("house-project-template-budget-api-");
    ({ documentPath, baseUrl } = api);
  });

  afterEach(() => api.close());

  const apiFetch: typeof fetch = (input, init) => {
    const requestedUrl =
      typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(requestedUrl, baseUrl);
    return fetch(url, init);
  };

  function requestApi(headers: Record<string, string>): Promise<{ status: number; body: string }> {
    return new Promise((resolve, reject) => {
      const request = httpRequest(`${baseUrl}/api/budget`, { method: "GET", headers });
      request.once("error", reject);
      request.once("response", (incoming) => {
        const chunks: Buffer[] = [];
        incoming.on("data", (chunk: Buffer) => chunks.push(chunk));
        incoming.once("end", () =>
          resolve({
            status: incoming.statusCode ?? 0,
            body: Buffer.concat(chunks).toString("utf8"),
          }),
        );
      });
      request.end();
    });
  }

  it("loads through the typed client", async () => {
    const snapshot = await loadBudget(apiFetch);
    expect(snapshot.document).toEqual(makeDocument());
    expect(snapshot.revision).toMatch(/^[a-f0-9]{64}$/);
  });

  it.each([
    "attacker.example",
    "other.localhost",
    "budget.localhost",
    "localhost.attacker.example",
  ])("rejects unapproved Host %s even with proxy headers", async (host) => {
    const response = await requestApi({
      Host: host,
      "X-Forwarded-Host": "localhost",
      "X-Forwarded-Proto": "https",
    });
    const body = JSON.parse(response.body) as { error: { code: string } };
    expect(response.status).toBe(403);
    expect(body.error.code).toBe("LOOPBACK_HOST_REQUIRED");
  });

  it("refuses writes because the API is read-only", async () => {
    const initial = await loadBudget(apiFetch);
    const response = await fetch(`${baseUrl}/api/budget`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Origin: baseUrl },
      body: JSON.stringify({ expectedRevision: initial.revision, document: initial.document }),
    });
    expect(response.status).toBe(405);
    expect(response.headers.get("Allow")).toBe("GET");
  });

  it("gives an actionable error for a missing canonical file", async () => {
    await rm(documentPath);
    const response = await fetch(`${baseUrl}/api/budget`);
    const body = (await response.json()) as { error: { code: string; message: string } };
    expect(response.status).toBe(500);
    expect(body.error.code).toBe("DATA_FILE_MISSING");
    expect(body.error.message).toContain("nu generează");
  });
});

describe("exchange rate API", () => {
  let api: TestApiServer;
  let baseUrl: string;

  async function start(buildExchangeRates?: (dir: string) => ExchangeRateCache): Promise<void> {
    api = await startApiServer("house-project-template-budget-fx-", buildExchangeRates);
    ({ baseUrl } = api);
  }

  afterEach(() => api.close());

  it("returns 200 with the cached exchange rate snapshot", async () => {
    await start(
      (dir) =>
        new ExchangeRateCache({
          cachePath: join(dir, "exchange-rate.json"),
          now: () => new Date("2026-09-18T12:00:00.000Z"),
          fetcher: () =>
            Promise.resolve(
              new Response(
                `<DataSet><Body><Cube date="2026-09-18"><Rate currency="EUR">5.2644</Rate></Cube></Body></DataSet>`,
                { status: 200 },
              ),
            ),
        }),
    );
    const response = await fetch(`${baseUrl}/api/exchange-rate`);
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      ronPerEur: 5.2644,
      rateDate: "2026-09-18",
      source: "BNR",
      stale: false,
    });
  });

  it("returns 503 when no exchange rate cache is configured", async () => {
    await start();
    const response = await fetch(`${baseUrl}/api/exchange-rate`);
    const body = (await response.json()) as { error: { code: string } };
    expect(response.status).toBe(503);
    expect(body.error.code).toBe("EXCHANGE_RATE_UNAVAILABLE");
  });
});
