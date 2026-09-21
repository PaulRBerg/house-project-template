import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { createServer, request as httpRequest, type Server } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { BudgetConflictError, loadBudget, saveBudget } from "../api/client.js";
import { serializeBudgetDocument } from "../domain/serialization.js";
import { makeDocument } from "../domain/test-fixtures.js";
import { createBudgetApiMiddleware } from "./api-middleware.js";
import { BudgetStore } from "./budget-store.js";
import { ExchangeRateCache } from "./exchange-rate.js";

describe("budget API middleware", () => {
  let directory: string;
  let documentPath: string;
  let server: Server;
  let baseUrl: string;

  beforeEach(async () => {
    directory = await mkdtemp(join(tmpdir(), "house-template-budget-api-"));
    documentPath = join(directory, "project.json");
    await writeFile(documentPath, serializeBudgetDocument(makeDocument()), "utf8");
    const middleware = createBudgetApiMiddleware(
      new BudgetStore({ documentPath, backupDirectory: join(directory, "backups") }),
      { maxBodyBytes: 100_000 },
    );
    server = createServer((request, response) => {
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
    baseUrl = `http://127.0.0.1:${address.port}`;
  });

  afterEach(async () => {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
    await rm(directory, { recursive: true, force: true });
  });

  const apiFetch: typeof fetch = (input, init) => {
    const requestedUrl =
      typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(requestedUrl, baseUrl);
    const headers = new Headers(init?.headers);
    if (init?.method === "PUT") headers.set("Origin", baseUrl);
    return fetch(url, { ...init, headers });
  };

  function requestApi(
    headers: Record<string, string>,
    payload?: string,
  ): Promise<{ status: number; body: string }> {
    return new Promise((resolve, reject) => {
      const request = httpRequest(`${baseUrl}/api/budget`, {
        method: payload === undefined ? "GET" : "PUT",
        headers: {
          ...(payload === undefined
            ? {}
            : {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(payload),
              }),
          ...headers,
        },
      });
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
      request.end(payload);
    });
  }

  it("loads and saves through the typed client", async () => {
    const initial = await loadBudget(apiFetch);
    const saved = await saveBudget(
      initial.revision,
      { ...initial.document, project: { ...initial.document.project, name: "Prin API" } },
      apiFetch,
    );
    expect(saved.document.project.name).toBe("Prin API");
    expect(saved.revision).not.toBe(initial.revision);
  });

  it.each([
    undefined,
    "http://house.localhost",
    "https://house.localhost:8443",
    "https://other.localhost",
    "https://house.localhost.attacker.example",
    "http://localhost",
  ])("rejects writes through a custom host from origin %s", async (origin) => {
    const initial = await loadBudget(apiFetch);
    const before = await readFile(documentPath, "utf8");
    const headers: Record<string, string> = { Host: "house.localhost" };
    if (origin !== undefined) headers.Origin = origin;
    const response = await requestApi(
      headers,
      JSON.stringify({ expectedRevision: initial.revision, document: initial.document }),
    );
    expect(response.status).toBe(403);
    expect(JSON.parse(response.body)).toMatchObject({
      error: { code: "LOOPBACK_HOST_REQUIRED" },
    });
    expect(await readFile(documentPath, "utf8")).toBe(before);
  });

  it("returns the latest document on revision conflict", async () => {
    const initial = await loadBudget(apiFetch);
    await saveBudget(
      initial.revision,
      { ...initial.document, project: { ...initial.document.project, name: "Nou" } },
      apiFetch,
    );
    let conflict: BudgetConflictError | undefined;
    try {
      await saveBudget(initial.revision, initial.document, apiFetch);
    } catch (error) {
      if (error instanceof BudgetConflictError) conflict = error;
      else throw error;
    }
    expect(conflict?.latest.document.project.name).toBe("Nou");
  });

  it("rejects cross-origin writes without changing the file", async () => {
    const initial = await loadBudget(apiFetch);
    const before = await readFile(documentPath, "utf8");
    const response = await fetch(`${baseUrl}/api/budget`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Origin: "http://evil.example" },
      body: JSON.stringify({ expectedRevision: initial.revision, document: initial.document }),
    });
    expect(response.status).toBe(403);
    expect(await readFile(documentPath, "utf8")).toBe(before);
  });

  it.each([
    "attacker.example",
    "other.localhost",
    "house.localhost.attacker.example",
    "house.localhost:8443",
  ])("rejects unapproved Host %s even with proxy headers", async (host) => {
    const initial = await loadBudget(apiFetch);
    const before = await readFile(documentPath, "utf8");
    const payload = JSON.stringify({
      expectedRevision: initial.revision,
      document: initial.document,
    });
    const response = await requestApi(
      {
        Host: host,
        Origin: `http://${host}`,
        "X-Forwarded-Host": "house.localhost",
        "X-Forwarded-Proto": "https",
      },
      payload,
    );
    const body = JSON.parse(response.body) as { error: { code: string } };
    expect(response.status).toBe(403);
    expect(body.error.code).toBe("LOOPBACK_HOST_REQUIRED");
    expect(await readFile(documentPath, "utf8")).toBe(before);
  });

  it("rejects oversized and invalid documents without corruption", async () => {
    const initial = await loadBudget(apiFetch);
    const before = await readFile(documentPath, "utf8");
    const oversized = await fetch(`${baseUrl}/api/budget`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Origin: baseUrl },
      body: JSON.stringify({ noise: "x".repeat(100_001) }),
    });
    expect(oversized.status).toBe(413);

    const invalid = await fetch(`${baseUrl}/api/budget`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Origin: baseUrl },
      body: JSON.stringify({
        expectedRevision: initial.revision,
        document: { ...initial.document, milestones: [] },
      }),
    });
    expect(invalid.status).toBe(400);
    expect(await readFile(documentPath, "utf8")).toBe(before);
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
  let directory: string;
  let server: Server;
  let baseUrl: string;

  async function start(buildExchangeRates?: (dir: string) => ExchangeRateCache): Promise<void> {
    directory = await mkdtemp(join(tmpdir(), "house-template-budget-fx-"));
    const documentPath = join(directory, "project.json");
    await writeFile(documentPath, serializeBudgetDocument(makeDocument()), "utf8");
    const middleware = createBudgetApiMiddleware(
      new BudgetStore({ documentPath, backupDirectory: join(directory, "backups") }),
      { exchangeRates: buildExchangeRates?.(directory) },
    );
    server = createServer((request, response) => {
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
    baseUrl = `http://127.0.0.1:${address.port}`;
  }

  afterEach(async () => {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
    await rm(directory, { recursive: true, force: true });
  });

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
