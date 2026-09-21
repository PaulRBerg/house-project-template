import { createHash, randomUUID } from "node:crypto";
import { mkdir, open, readFile, readdir, rename, stat, unlink, writeFile } from "node:fs/promises";
import { basename, dirname, join } from "node:path";

import type { BudgetSnapshot } from "../api/contracts.js";
import {
  formatValidationIssues,
  parseBudgetDocument,
  serializeBudgetDocument,
  type BudgetDocument,
} from "../domain/index.js";

export type BudgetStoreErrorCode =
  | "DATA_FILE_MISSING"
  | "DATA_FILE_TOO_LARGE"
  | "DATA_FILE_INVALID_JSON"
  | "DATA_FILE_INVALID_DOCUMENT"
  | "DATA_FILE_IO_ERROR"
  | "BACKUP_FAILED"
  | "WRITE_FAILED";

export class BudgetStoreError extends Error {
  readonly code: BudgetStoreErrorCode;
  readonly details: string[];

  constructor(
    code: BudgetStoreErrorCode,
    message: string,
    details: string[] = [],
    cause?: unknown,
  ) {
    super(message, cause === undefined ? undefined : { cause });
    this.name = "BudgetStoreError";
    this.code = code;
    this.details = details;
  }
}

export interface BudgetStoreOptions {
  documentPath: string;
  backupDirectory: string;
  maxBackups?: number;
  maxFileBytes?: number;
}

export type SaveBudgetResult =
  | { ok: true; snapshot: BudgetSnapshot }
  | { ok: false; conflict: true; latest: BudgetSnapshot };

const DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024;

function revisionFor(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

export class BudgetStore {
  readonly documentPath: string;
  readonly backupDirectory: string;
  readonly maxBackups: number;
  readonly maxFileBytes: number;
  private writeTail: Promise<void> = Promise.resolve();

  constructor(options: BudgetStoreOptions) {
    this.documentPath = options.documentPath;
    this.backupDirectory = options.backupDirectory;
    this.maxBackups = Math.max(1, options.maxBackups ?? 8);
    this.maxFileBytes = options.maxFileBytes ?? DEFAULT_MAX_FILE_BYTES;
  }

  async read(): Promise<BudgetSnapshot> {
    return (await this.readCurrent()).snapshot;
  }

  private async readCurrent(): Promise<{ snapshot: BudgetSnapshot; bytes: Buffer }> {
    let fileStat;
    try {
      fileStat = await stat(this.documentPath);
    } catch (error) {
      if (isNodeError(error) && error.code === "ENOENT") {
        throw new BudgetStoreError(
          "DATA_FILE_MISSING",
          `Fișierul de buget lipsește: ${this.documentPath}. Creează-l explicit; serverul nu generează și nu suprascrie date inițiale.`,
        );
      }
      throw new BudgetStoreError(
        "DATA_FILE_IO_ERROR",
        `Fișierul de buget nu poate fi verificat: ${this.documentPath}.`,
        [],
        error,
      );
    }
    if (!fileStat.isFile()) {
      throw new BudgetStoreError(
        "DATA_FILE_IO_ERROR",
        `Calea bugetului nu este un fișier: ${this.documentPath}.`,
      );
    }
    if (fileStat.size > this.maxFileBytes) {
      throw new BudgetStoreError(
        "DATA_FILE_TOO_LARGE",
        `Fișierul de buget depășește limita de ${this.maxFileBytes} octeți.`,
      );
    }

    let bytes: Buffer;
    try {
      bytes = await readFile(this.documentPath);
    } catch (error) {
      throw new BudgetStoreError(
        "DATA_FILE_IO_ERROR",
        `Fișierul de buget nu poate fi citit: ${this.documentPath}.`,
        [],
        error,
      );
    }
    if (bytes.byteLength > this.maxFileBytes) {
      throw new BudgetStoreError(
        "DATA_FILE_TOO_LARGE",
        `Fișierul de buget depășește limita de ${this.maxFileBytes} octeți.`,
      );
    }
    let input: unknown;
    try {
      input = JSON.parse(bytes.toString("utf8"));
    } catch (error) {
      throw new BudgetStoreError(
        "DATA_FILE_INVALID_JSON",
        `Fișierul de buget conține JSON invalid: ${this.documentPath}. Corectează fișierul sau recuperează o copie din ${this.backupDirectory}.`,
        [],
        error,
      );
    }
    try {
      return {
        snapshot: { document: parseBudgetDocument(input), revision: revisionFor(bytes) },
        bytes,
      };
    } catch (error) {
      if (error && typeof error === "object" && "issues" in error) {
        throw new BudgetStoreError(
          "DATA_FILE_INVALID_DOCUMENT",
          `Fișierul de buget nu respectă schema: ${this.documentPath}.`,
          formatValidationIssues(error as Parameters<typeof formatValidationIssues>[0]),
          error,
        );
      }
      throw error;
    }
  }

  save(expectedRevision: string, document: BudgetDocument): Promise<SaveBudgetResult> {
    const validated = parseBudgetDocument(document);
    const operation = this.writeTail.then(() => this.saveSerial(expectedRevision, validated));
    this.writeTail = operation.then(
      () => undefined,
      () => undefined,
    );
    return operation;
  }

  private async saveSerial(
    expectedRevision: string,
    document: BudgetDocument,
  ): Promise<SaveBudgetResult> {
    const current = await this.readCurrent();
    const latest = current.snapshot;
    if (latest.revision !== expectedRevision) {
      return { ok: false, conflict: true, latest };
    }

    const bytes = Buffer.from(serializeBudgetDocument(document), "utf8");
    if (bytes.byteLength > this.maxFileBytes) {
      throw new BudgetStoreError(
        "DATA_FILE_TOO_LARGE",
        `Documentul nou depășește limita de ${this.maxFileBytes} octeți.`,
      );
    }
    await this.backUpCurrent(latest.revision, current.bytes);
    await this.atomicWrite(bytes);
    return {
      ok: true,
      snapshot: { document, revision: revisionFor(bytes) },
    };
  }

  private async backUpCurrent(revision: string, currentBytes: Uint8Array): Promise<void> {
    try {
      await mkdir(this.backupDirectory, { recursive: true });
      await writeFile(
        join(this.backupDirectory, `${Date.now()}-${revision.slice(0, 12)}-${randomUUID()}.json`),
        currentBytes,
        { flag: "wx", flush: true },
      );
      await this.pruneBackups();
    } catch (error) {
      throw new BudgetStoreError(
        "BACKUP_FAILED",
        `Nu s-a putut crea o copie de siguranță în ${this.backupDirectory}; fișierul original a rămas neschimbat.`,
        [],
        error,
      );
    }
  }

  private async pruneBackups(): Promise<void> {
    const prefix = `${basename(this.documentPath, ".json")}-`;
    const entries = (await readdir(this.backupDirectory))
      .filter((entry) => entry.endsWith(".json"))
      .sort()
      .reverse();
    const matchingEntries = entries.filter(
      (entry) => entry.includes(prefix) || /^[0-9]+-[a-f0-9]+-/.test(entry),
    );
    await Promise.all(
      matchingEntries
        .slice(this.maxBackups)
        .map((entry) => unlink(join(this.backupDirectory, entry))),
    );
  }

  private async atomicWrite(bytes: Uint8Array): Promise<void> {
    const temporaryPath = join(
      dirname(this.documentPath),
      `.${basename(this.documentPath)}.${process.pid}.${randomUUID()}.tmp`,
    );
    let handle;
    try {
      handle = await open(temporaryPath, "wx", 0o600);
      await handle.writeFile(bytes);
      await handle.sync();
      await handle.close();
      handle = undefined;
      await rename(temporaryPath, this.documentPath);
    } catch (error) {
      await handle?.close().catch(() => undefined);
      await unlink(temporaryPath).catch(() => undefined);
      throw new BudgetStoreError(
        "WRITE_FAILED",
        `Bugetul nu a putut fi salvat atomic în ${this.documentPath}; fișierul anterior rămâne sursa de adevăr.`,
        [],
        error,
      );
    }
  }
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && "code" in error;
}
