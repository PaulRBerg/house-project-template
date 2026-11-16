import { resolve } from "node:path";

import type { Plugin } from "vite";

import { createBudgetApiMiddleware } from "./api-middleware.js";
import { BudgetFileReader, CANONICAL_DOCUMENT_PATH } from "./budget-file-reader.js";
import { ExchangeRateCache } from "./exchange-rate.js";

export function createBudgetApiPlugin({ projectRoot }: { projectRoot: string }): Plugin {
  // Server-only override for isolated test instances. Never derive it from an HTTP request.
  const isolatedPath = process.env.BUDGET_DATA_FILE;
  const budgetFile = new BudgetFileReader({
    documentPath: isolatedPath ? resolve(projectRoot, isolatedPath) : CANONICAL_DOCUMENT_PATH,
  });
  // Not budget state: isolated BUDGET_DATA_FILE test instances share this cache.
  const exchangeRates = new ExchangeRateCache({
    cachePath: resolve(projectRoot, ".cache/exchange-rate.json"),
  });
  const middleware = createBudgetApiMiddleware(budgetFile, { exchangeRates });
  return {
    name: "house-project-template-budget-api",
    configureServer(server) {
      server.middlewares.use(middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware);
    },
  };
}
