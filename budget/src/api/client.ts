import type { BudgetDocument } from "../domain/schema.js";
import {
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

export class BudgetConflictError extends BudgetApiError {
  readonly latest: BudgetSnapshot;

  constructor(message: string, latest: BudgetSnapshot) {
    super(409, "REVISION_CONFLICT", message);
    this.name = "BudgetConflictError";
    this.latest = latest;
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
  const { error, latest } = parsed.data;
  if (response.status === 409 && latest) {
    throw new BudgetConflictError(error.message, latest);
  }
  throw new BudgetApiError(response.status, error.code, error.message, error.details ?? []);
}

export async function loadBudget(fetcher: typeof fetch = fetch): Promise<BudgetSnapshot> {
  const response = await fetcher("/api/budget", {
    headers: { Accept: "application/json" },
  });
  const body = await decodeResponse(response);
  if (!response.ok) throwApiError(response, body);
  const parsed = budgetSnapshotSchema.safeParse(body);
  if (!parsed.success) {
    throw new BudgetApiError(
      response.status,
      "INVALID_RESPONSE",
      "Serverul a returnat un document de buget invalid.",
      parsed.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`),
    );
  }
  return parsed.data;
}

export async function loadExchangeRate(fetcher: typeof fetch = fetch): Promise<ExchangeRate> {
  const response = await fetcher("/api/exchange-rate", {
    headers: { Accept: "application/json" },
  });
  const body = await decodeResponse(response);
  if (!response.ok) throwApiError(response, body);
  const parsed = exchangeRateSchema.safeParse(body);
  if (!parsed.success) {
    throw new BudgetApiError(
      response.status,
      "INVALID_RESPONSE",
      "Serverul a returnat un curs de schimb invalid.",
      parsed.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`),
    );
  }
  return parsed.data;
}

export async function saveBudget(
  expectedRevision: string,
  document: BudgetDocument,
  fetcher: typeof fetch = fetch,
): Promise<BudgetSnapshot> {
  const response = await fetcher("/api/budget", {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ expectedRevision, document }),
  });
  const body = await decodeResponse(response);
  if (!response.ok) throwApiError(response, body);
  const parsed = budgetSnapshotSchema.safeParse(body);
  if (!parsed.success) {
    throw new BudgetApiError(
      response.status,
      "INVALID_RESPONSE",
      "Serverul a returnat o revizie de buget invalidă după salvare.",
      parsed.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`),
    );
  }
  return parsed.data;
}
