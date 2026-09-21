import { createHash } from "node:crypto";
import { join, resolve } from "node:path";

import type { Plugin } from "vite";

import { createBudgetApiMiddleware } from "./api-middleware.js";
import { BudgetStore } from "./budget-store.js";
import { ExchangeRateCache } from "./exchange-rate.js";

export interface BudgetApiPluginOptions {
  projectRoot: string;
  /** Server-only override for isolated tests. Never derive this value from an HTTP request. */
  documentPath?: string;
}

export function resolveBudgetDocumentPath(options: BudgetApiPluginOptions): string {
  const configuredPath = options.documentPath ?? process.env.BUDGET_DATA_FILE;
  return configuredPath
    ? resolve(options.projectRoot, configuredPath)
    : resolve(options.projectRoot, "data/project.json");
}

export function resolveBudgetBackupDirectory(
  projectRoot: string,
  documentPath: string,
  isolated: boolean,
): string {
  const backupRoot = resolve(projectRoot, ".cache/budget-backups");
  if (!isolated) return backupRoot;
  const documentKey = createHash("sha256").update(documentPath).digest("hex").slice(0, 16);
  return join(backupRoot, `isolated-${documentKey}`);
}

export function createBudgetApiPlugin(options: BudgetApiPluginOptions): Plugin {
  const configuredPath = options.documentPath ?? process.env.BUDGET_DATA_FILE;
  const documentPath = resolveBudgetDocumentPath(options);
  const store = new BudgetStore({
    documentPath,
    backupDirectory: resolveBudgetBackupDirectory(
      options.projectRoot,
      documentPath,
      Boolean(configuredPath),
    ),
  });
  // Not budget state: isolated BUDGET_DATA_FILE test instances share this cache.
  const exchangeRates = new ExchangeRateCache({
    cachePath: resolve(options.projectRoot, ".cache/exchange-rate.json"),
  });
  const middleware = createBudgetApiMiddleware(store, { exchangeRates });
  return {
    name: "house-template-budget-api",
    configureServer(server) {
      server.middlewares.use(middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware);
    },
  };
}
