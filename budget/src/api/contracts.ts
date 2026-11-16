import { z } from "zod";

import { budgetDocumentSchema, isoDateSchema } from "../domain/schema.js";

export const API_PATHS = {
  budget: "/api/budget",
  exchangeRate: "/api/exchange-rate",
} as const;

/** Human-readable BNR reference-rate page, also the header link while the rate loads. */
export const BNR_EXCHANGE_RATE_PAGE_URL = "https://www.bnr.ro/541-cursul-de-schimb";

export const revisionSchema = z.string().regex(/^[a-f0-9]{64}$/);

export const budgetSnapshotSchema = z
  .object({
    document: budgetDocumentSchema,
    revision: revisionSchema,
  })
  .strict();

export const apiErrorSchema = z
  .object({
    error: z
      .object({
        code: z.string(),
        message: z.string(),
        details: z.array(z.string()).optional(),
      })
      .strict(),
  })
  .strict();

export type BudgetSnapshot = z.infer<typeof budgetSnapshotSchema>;
export type ApiErrorBody = z.infer<typeof apiErrorSchema>;

export const exchangeRateSchema = z
  .object({
    ronPerEur: z.number().positive().finite(),
    rateDate: isoDateSchema,
    source: z.union([z.literal("BNR"), z.literal("ECB")]),
    sourceUrl: z.url(),
    fetchedAt: z.iso.datetime(),
    stale: z.boolean(),
  })
  .strict();

export type ExchangeRate = z.infer<typeof exchangeRateSchema>;
