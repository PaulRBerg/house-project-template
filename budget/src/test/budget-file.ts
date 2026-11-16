import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type { BudgetDocument } from "../domain/schema.js";
import { serializeBudgetDocument } from "../domain/serialization.js";
import { makeDocument } from "./builders.js";

/** Writes a canonical budget file into a fresh temporary directory for server tests. */
export async function createTempBudgetFile(
  prefix: string,
  document: BudgetDocument = makeDocument(),
): Promise<{ directory: string; documentPath: string }> {
  const directory = await mkdtemp(join(tmpdir(), prefix));
  const documentPath = join(directory, "project.json");
  await writeFile(documentPath, serializeBudgetDocument(document), "utf8");
  return { directory, documentPath };
}
