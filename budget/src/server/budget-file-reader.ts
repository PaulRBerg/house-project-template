import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import type { BudgetSnapshot } from "../api/contracts.js";
import { formatValidationIssues, parseBudgetDocument } from "../domain/index.js";

export type BudgetFileErrorCode =
  | "DATA_FILE_MISSING"
  | "DATA_FILE_TOO_LARGE"
  | "DATA_FILE_INVALID_JSON"
  | "DATA_FILE_INVALID_DOCUMENT"
  | "DATA_FILE_IO_ERROR";

export class BudgetFileError extends Error {
  readonly code: BudgetFileErrorCode;
  readonly details: string[];

  constructor(code: BudgetFileErrorCode, message: string, details: string[] = [], cause?: unknown) {
    super(message, cause === undefined ? undefined : { cause });
    this.name = "BudgetFileError";
    this.code = code;
    this.details = details;
  }
}

export interface BudgetFileReaderOptions {
  documentPath: string;
  maxFileBytes?: number;
}

/** The checked-in budget document that the app serves and the cost CLI edits. */
export const CANONICAL_DOCUMENT_PATH = fileURLToPath(
  new URL("../../data/project.json", import.meta.url),
);

const DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024;

/** Snapshot revision: the SHA-256 of the file bytes. */
export function revisionFor(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

/** Read-only access to the canonical budget file; the app never writes it. */
export class BudgetFileReader {
  readonly documentPath: string;
  readonly maxFileBytes: number;

  constructor(options: BudgetFileReaderOptions) {
    this.documentPath = options.documentPath;
    this.maxFileBytes = options.maxFileBytes ?? DEFAULT_MAX_FILE_BYTES;
  }

  private tooLarge(): BudgetFileError {
    return new BudgetFileError(
      "DATA_FILE_TOO_LARGE",
      `Fișierul de buget depășește limita de ${this.maxFileBytes} octeți.`,
    );
  }

  async read(): Promise<BudgetSnapshot> {
    let fileStat;
    try {
      fileStat = await stat(this.documentPath);
    } catch (error) {
      if (isNodeError(error) && error.code === "ENOENT") {
        throw new BudgetFileError(
          "DATA_FILE_MISSING",
          `Fișierul de buget lipsește: ${this.documentPath}. Creează-l explicit; serverul nu generează și nu suprascrie date inițiale.`,
        );
      }
      throw new BudgetFileError(
        "DATA_FILE_IO_ERROR",
        `Fișierul de buget nu poate fi verificat: ${this.documentPath}.`,
        [],
        error,
      );
    }
    if (!fileStat.isFile()) {
      throw new BudgetFileError(
        "DATA_FILE_IO_ERROR",
        `Calea bugetului nu este un fișier: ${this.documentPath}.`,
      );
    }
    if (fileStat.size > this.maxFileBytes) throw this.tooLarge();

    let bytes: Buffer;
    try {
      bytes = await readFile(this.documentPath);
    } catch (error) {
      throw new BudgetFileError(
        "DATA_FILE_IO_ERROR",
        `Fișierul de buget nu poate fi citit: ${this.documentPath}.`,
        [],
        error,
      );
    }
    if (bytes.byteLength > this.maxFileBytes) throw this.tooLarge();
    let input: unknown;
    try {
      input = JSON.parse(bytes.toString("utf8"));
    } catch (error) {
      throw new BudgetFileError(
        "DATA_FILE_INVALID_JSON",
        `Fișierul de buget conține JSON invalid: ${this.documentPath}. Corectează fișierul sau recuperează versiunea din Git.`,
        [],
        error,
      );
    }
    try {
      return { document: parseBudgetDocument(input), revision: revisionFor(bytes) };
    } catch (error) {
      if (error && typeof error === "object" && "issues" in error) {
        throw new BudgetFileError(
          "DATA_FILE_INVALID_DOCUMENT",
          `Fișierul de buget nu respectă schema: ${this.documentPath}.`,
          formatValidationIssues(error as Parameters<typeof formatValidationIssues>[0]),
          error,
        );
      }
      throw error;
    }
  }
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && "code" in error;
}
