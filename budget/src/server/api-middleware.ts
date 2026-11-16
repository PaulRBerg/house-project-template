import type { IncomingMessage, ServerResponse } from "node:http";

import { API_PATHS } from "../api/contracts.js";
import { BudgetFileReader, BudgetFileError } from "./budget-file-reader.js";
import type { ExchangeRateCache } from "./exchange-rate.js";

export type NextFunction = (error?: unknown) => void;
export type BudgetApiMiddleware = (
  request: IncomingMessage,
  response: ServerResponse,
  next: NextFunction,
) => void;

export interface BudgetApiOptions {
  exchangeRates?: ExchangeRateCache | undefined;
}

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");
  response.setHeader("Content-Length", Buffer.byteLength(payload));
  response.end(payload);
}

function sendError(
  response: ServerResponse,
  status: number,
  code: string,
  message: string,
  details?: string[],
): void {
  sendJson(response, status, {
    error: { code, message, ...(details && details.length > 0 ? { details } : {}) },
  });
}

function isLoopback(address: string | undefined): boolean {
  return (
    address === "127.0.0.1" || address === "::1" || address?.startsWith("::ffff:127.") === true
  );
}

function parseLoopbackOrigin(host: string | undefined): string | undefined {
  if (!host) return undefined;
  try {
    const parsed = new URL(`http://${host}`);
    const allowedHostnames = new Set(["localhost", "127.0.0.1", "[::1]"]);
    if (
      parsed.protocol !== "http:" ||
      !allowedHostnames.has(parsed.hostname) ||
      parsed.username !== "" ||
      parsed.password !== "" ||
      parsed.pathname !== "/" ||
      parsed.search !== "" ||
      parsed.hash !== ""
    ) {
      return undefined;
    }
    return parsed.origin;
  } catch {
    return undefined;
  }
}

function parsePathname(requestUrl: string | undefined): string | undefined {
  try {
    return new URL(requestUrl ?? "/", "http://localhost").pathname;
  } catch {
    return undefined;
  }
}

export function createBudgetApiMiddleware(
  budgetFile: BudgetFileReader,
  options: BudgetApiOptions = {},
): BudgetApiMiddleware {
  const exchangeRates = options.exchangeRates;
  return (request, response, next) => {
    void handleBudgetApiRequest(budgetFile, request, response, next, exchangeRates);
  };
}

async function handleBudgetApiRequest(
  budgetFile: BudgetFileReader,
  request: IncomingMessage,
  response: ServerResponse,
  next: NextFunction,
  exchangeRates: ExchangeRateCache | undefined,
): Promise<void> {
  const pathname = parsePathname(request.url);
  if (pathname === undefined) {
    sendError(response, 400, "INVALID_REQUEST_URL", "Adresa cererii nu este validă.");
    return;
  }
  if (pathname !== API_PATHS.budget && pathname !== API_PATHS.exchangeRate) {
    next();
    return;
  }
  const requestOrigin = parseLoopbackOrigin(request.headers.host);
  if (!requestOrigin) {
    sendError(
      response,
      403,
      "LOOPBACK_HOST_REQUIRED",
      "API-ul bugetului acceptă doar nume de gazdă loopback explicite.",
    );
    return;
  }
  if (!isLoopback(request.socket.remoteAddress)) {
    sendError(
      response,
      403,
      "LOOPBACK_REQUIRED",
      "API-ul bugetului acceptă doar conexiuni locale.",
    );
    return;
  }
  if (request.method !== "GET") {
    response.setHeader("Allow", "GET");
    sendError(response, 405, "METHOD_NOT_ALLOWED", "Este acceptat doar GET.");
    return;
  }
  if (pathname === API_PATHS.exchangeRate) {
    try {
      if (!exchangeRates) throw new Error("Cache-ul cursului nu este configurat.");
      sendJson(response, 200, await exchangeRates.read());
    } catch {
      sendError(
        response,
        503,
        "EXCHANGE_RATE_UNAVAILABLE",
        "Cursul de schimb nu este disponibil în acest moment.",
      );
    }
    return;
  }
  try {
    sendJson(response, 200, await budgetFile.read());
  } catch (error) {
    sendBudgetFileError(response, error);
  }
}

function sendBudgetFileError(response: ServerResponse, error: unknown): void {
  if (error instanceof BudgetFileError) {
    sendError(response, 500, error.code, error.message, error.details);
    return;
  }
  sendError(response, 500, "INTERNAL_ERROR", "Serverul nu a putut procesa bugetul.");
}
