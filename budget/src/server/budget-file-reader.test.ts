import { readFile, rm, writeFile } from "node:fs/promises";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { serializeBudgetDocument } from "../domain/serialization.js";
import { createTempBudgetFile } from "../test/budget-file.js";
import { makeDocument } from "../test/builders.js";
import { BudgetFileReader, BudgetFileError } from "./budget-file-reader.js";

describe("BudgetFileReader", () => {
  let directory: string;
  let documentPath: string;

  beforeEach(async () => {
    ({ directory, documentPath } = await createTempBudgetFile(
      "house-project-template-budget-file-",
    ));
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  it("reads the document with a revision derived from the file bytes", async () => {
    const reader = new BudgetFileReader({ documentPath });
    const initial = await reader.read();
    expect(initial.document).toEqual(makeDocument());
    expect(initial.revision).toMatch(/^[a-f0-9]{64}$/);

    await writeFile(
      documentPath,
      serializeBudgetDocument({
        ...initial.document,
        project: { ...initial.document.project, name: "Casa actualizată" },
      }),
      "utf8",
    );
    const changed = await reader.read();
    expect(changed.document.project.name).toBe("Casa actualizată");
    expect(changed.revision).not.toBe(initial.revision);
  });

  it("reports malformed, oversized, and missing files without touching them", async () => {
    const malformed = "{ invalid";
    await writeFile(documentPath, malformed, "utf8");
    const reader = new BudgetFileReader({ documentPath });
    await expect(reader.read()).rejects.toMatchObject<Partial<BudgetFileError>>({
      code: "DATA_FILE_INVALID_JSON",
    });
    expect(await readFile(documentPath, "utf8")).toBe(malformed);

    await expect(
      new BudgetFileReader({ documentPath, maxFileBytes: 4 }).read(),
    ).rejects.toMatchObject<Partial<BudgetFileError>>({ code: "DATA_FILE_TOO_LARGE" });

    await rm(documentPath);
    await expect(reader.read()).rejects.toMatchObject<Partial<BudgetFileError>>({
      code: "DATA_FILE_MISSING",
    });
  });
});
