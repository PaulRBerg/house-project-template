import { vi } from "vitest";

import { API_PATHS, type BudgetSnapshot, type ExchangeRate } from "../api/contracts.js";
import type { BudgetDocument } from "../domain/schema.js";
import { makeUiDocument } from "./fixtures.js";

export const TEST_REVISION = "a".repeat(64);

export function makeSnapshot(
  document: BudgetDocument = makeUiDocument(),
  revision = TEST_REVISION,
): BudgetSnapshot {
  return { document, revision };
}

export function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

export function makeExchangeRate(): ExchangeRate {
  return {
    ronPerEur: 5.12,
    rateDate: "2026-09-18",
    source: "BNR",
    sourceUrl: "https://www.bnr.ro/",
    fetchedAt: "2026-09-18T12:00:00.000Z",
    stale: false,
  };
}

/** Stubs `fetch` with the budget and exchange-rate endpoints; other URLs reject. */
export function installApiFetch(
  respondBudget: (init: RequestInit | undefined) => Response | Promise<Response> = () =>
    jsonResponse(makeSnapshot()),
) {
  const request = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === API_PATHS.exchangeRate) {
      return Promise.resolve(jsonResponse(makeExchangeRate()));
    }
    if (String(input) === API_PATHS.budget) return Promise.resolve(respondBudget(init));
    return Promise.reject(new Error(`Unexpected fetch request: ${String(input)}`));
  });
  vi.stubGlobal("fetch", request);
  return request;
}
