import { z } from "zod";

import { budgetDocumentSchema } from "../domain/schema.js";

export const revisionSchema = z.string().regex(/^[a-f0-9]{64}$/);

export const budgetSnapshotSchema = z
  .object({
    document: budgetDocumentSchema,
    revision: revisionSchema,
  })
  .strict();

export const putBudgetRequestSchema = z
  .object({
    expectedRevision: revisionSchema,
    document: budgetDocumentSchema,
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
    latest: budgetSnapshotSchema.optional(),
  })
  .strict();

export type BudgetSnapshot = z.infer<typeof budgetSnapshotSchema>;
export type PutBudgetRequest = z.infer<typeof putBudgetRequestSchema>;
export type ApiErrorBody = z.infer<typeof apiErrorSchema>;

export const exchangeRateSchema = z
  .object({
    ronPerEur: z.number().positive().finite(),
    rateDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    source: z.union([z.literal("BNR"), z.literal("ECB")]),
    sourceUrl: z.url(),
    fetchedAt: z.iso.datetime(),
    stale: z.boolean(),
  })
  .strict();

export type ExchangeRate = z.infer<typeof exchangeRateSchema>;
