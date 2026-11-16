import type { z } from "zod";

import { formatValidationIssues } from "../domain/schema.js";
import {
  API_PATHS,
  apiErrorSchema,
  budgetSnapshotSchema,
  exchangeRateSchema,
  type BudgetSnapshot,
  type ExchangeRate,
} from "./contracts.js";

export class BudgetApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: string[];

  constructor(status: number, code: string, message: string, details: string[] = []) {
    super(message);
    this.name = "BudgetApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function decodeResponse(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new BudgetApiError(
      response.status,
      "INVALID_RESPONSE",
      "Serverul a răspuns cu un corp care nu este JSON valid.",
    );
  }
}

function throwApiError(response: Response, body: unknown): never {
  const parsed = apiErrorSchema.safeParse(body);
  if (!parsed.success) {
    throw new BudgetApiError(
      response.status,
      "INVALID_RESPONSE",
      `Serverul a răspuns cu eroarea HTTP ${response.status}, într-un format necunoscut.`,
    );
  }
  const { error } = parsed.data;
  throw new BudgetApiError(response.status, error.code, error.message, error.details ?? []);
}

async function fetchJson<T>(
  path: string,
  schema: z.ZodType<T>,
  invalidMessage: string,
  fetcher: typeof fetch,
): Promise<T> {
  const response = await fetcher(path, { headers: { Accept: "application/json" } });
  const body = await decodeResponse(response);
  if (!response.ok) throwApiError(response, body);
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    throw new BudgetApiError(
      response.status,
      "INVALID_RESPONSE",
      invalidMessage,
      formatValidationIssues(parsed.error),
    );
  }
  return parsed.data;
}

export function loadBudget(fetcher: typeof fetch = fetch): Promise<BudgetSnapshot> {
  return fetchJson(
    API_PATHS.budget,
    budgetSnapshotSchema,
    "Serverul a returnat un document de buget invalid.",
    fetcher,
  );
}

export function loadExchangeRate(fetcher: typeof fetch = fetch): Promise<ExchangeRate> {
  return fetchJson(
    API_PATHS.exchangeRate,
    exchangeRateSchema,
    "Serverul a returnat un curs de schimb invalid.",
    fetcher,
  );
}
