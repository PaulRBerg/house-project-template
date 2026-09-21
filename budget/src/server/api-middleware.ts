import type { IncomingMessage, ServerResponse } from "node:http";

import { putBudgetRequestSchema } from "../api/contracts.js";
import { formatValidationIssues } from "../domain/schema.js";
import { BudgetStore, BudgetStoreError } from "./budget-store.js";
import type { ExchangeRateCache } from "./exchange-rate.js";

export type NextFunction = (error?: unknown) => void;
export type BudgetApiMiddleware = (
  request: IncomingMessage,
  response: ServerResponse,
  next: NextFunction,
) => void;

export interface BudgetApiOptions {
  maxBodyBytes?: number;
  exchangeRates?: ExchangeRateCache | undefined;
}

const DEFAULT_MAX_BODY_BYTES = 2 * 1024 * 1024;

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
  latest?: unknown,
): void {
  sendJson(response, status, {
    error: { code, message, ...(details && details.length > 0 ? { details } : {}) },
    ...(latest === undefined ? {} : { latest }),
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

function hasSameOrigin(request: IncomingMessage, expectedOrigin: string): boolean {
  const origin = request.headers.origin;
  if (!origin) return false;
  try {
    const parsed = new URL(origin);
    return (
      parsed.origin === expectedOrigin &&
      parsed.username === "" &&
      parsed.password === "" &&
      parsed.pathname === "/" &&
      parsed.search === "" &&
      parsed.hash === ""
    );
  } catch {
    return false;
  }
}

function parsePathname(requestUrl: string | undefined): string | undefined {
  try {
    return new URL(requestUrl ?? "/", "http://localhost").pathname;
  } catch {
    return undefined;
  }
}

async function readJsonBody(request: IncomingMessage, maxBodyBytes: number): Promise<unknown> {
  const contentLength = Number(request.headers["content-length"] ?? 0);
  if (Number.isFinite(contentLength) && contentLength > maxBodyBytes) {
    throw new RequestError(
      413,
      "BODY_TOO_LARGE",
      `Corpul cererii depășește ${maxBodyBytes} octeți.`,
    );
  }
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.byteLength;
    if (size > maxBodyBytes) {
      throw new RequestError(
        413,
        "BODY_TOO_LARGE",
        `Corpul cererii depășește ${maxBodyBytes} octeți.`,
      );
    }
    chunks.push(buffer);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new RequestError(400, "INVALID_JSON", "Corpul cererii nu este JSON valid.");
  }
}

class RequestError extends Error {
  name = "RequestError";

  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export function createBudgetApiMiddleware(
  store: BudgetStore,
  options: BudgetApiOptions = {},
): BudgetApiMiddleware {
  const maxBodyBytes = options.maxBodyBytes ?? DEFAULT_MAX_BODY_BYTES;
  const exchangeRates = options.exchangeRates;
  return (request, response, next) => {
    void handleBudgetApiRequest(store, request, response, next, maxBodyBytes, exchangeRates);
  };
}

async function handleBudgetApiRequest(
  store: BudgetStore,
  request: IncomingMessage,
  response: ServerResponse,
  next: NextFunction,
  maxBodyBytes: number,
  exchangeRates: ExchangeRateCache | undefined,
): Promise<void> {
  const pathname = parsePathname(request.url);
  if (pathname === undefined) {
    sendError(response, 400, "INVALID_REQUEST_URL", "Adresa cererii nu este validă.");
    return;
  }
  if (pathname !== "/api/budget" && pathname !== "/api/exchange-rate") {
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
  if (pathname === "/api/exchange-rate") {
    if (request.method !== "GET") {
      response.setHeader("Allow", "GET");
      sendError(response, 405, "METHOD_NOT_ALLOWED", "Este acceptat doar GET.");
      return;
    }
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
  if (request.method === "GET") {
    try {
      sendJson(response, 200, await store.read());
    } catch (error) {
      sendStoreError(response, error);
    }
    return;
  }
  if (request.method !== "PUT") {
    response.setHeader("Allow", "GET, PUT");
    sendError(response, 405, "METHOD_NOT_ALLOWED", "Sunt acceptate doar GET și PUT.");
    return;
  }
  if (!hasSameOrigin(request, requestOrigin)) {
    sendError(
      response,
      403,
      "SAME_ORIGIN_REQUIRED",
      "Salvarea este permisă doar din aplicația deschisă la aceeași origine.",
    );
    return;
  }
  if (!request.headers["content-type"]?.toLowerCase().startsWith("application/json")) {
    sendError(response, 415, "JSON_REQUIRED", "Salvarea necesită Content-Type application/json.");
    return;
  }

  try {
    const body = await readJsonBody(request, maxBodyBytes);
    const parsed = putBudgetRequestSchema.safeParse(body);
    if (!parsed.success) {
      sendError(
        response,
        400,
        "INVALID_DOCUMENT",
        "Documentul trimis nu respectă contractul bugetului.",
        formatValidationIssues(parsed.error),
      );
      return;
    }
    const result = await store.save(parsed.data.expectedRevision, parsed.data.document);
    if (!result.ok) {
      sendError(
        response,
        409,
        "REVISION_CONFLICT",
        "Bugetul s-a schimbat pe disc. Reîncarcă ultima revizie și reconciliază modificările.",
        undefined,
        result.latest,
      );
      return;
    }
    sendJson(response, 200, result.snapshot);
  } catch (error) {
    if (error instanceof RequestError) {
      sendError(response, error.status, error.code, error.message);
      return;
    }
    sendStoreError(response, error);
  }
}

function sendStoreError(response: ServerResponse, error: unknown): void {
  if (error instanceof BudgetStoreError) {
    sendError(response, 500, error.code, error.message, error.details);
    return;
  }
  sendError(response, 500, "INTERNAL_ERROR", "Serverul nu a putut procesa bugetul.");
}
