import { readFile, rename, rm, writeFile } from "node:fs/promises";
import { basename, dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

import {
  addCost,
  CostEditError,
  deleteCost,
  moveCost,
  parseEuroCents,
  renameCost,
  setCostPrice,
  splitCost,
} from "../domain/cost-edits.js";
import type { BudgetDocument, BudgetItem } from "../domain/schema.js";
import { serializeBudgetDocument } from "../domain/serialization.js";
import {
  BudgetFileError,
  BudgetFileReader,
  CANONICAL_DOCUMENT_PATH,
  revisionFor,
} from "./budget-file-reader.js";

export const COST_USAGE = `Usage: just cost <command> [args]

  add <id> <category-id> <label> <eur> [--due YYYY-MM]... [--with '<item JSON>'] [--priced-on YYYY-MM-DD]
  delete <id>
  move <id> <category-id>
  rename <id> <label>
  set-price <id> <eur> [--priced-on YYYY-MM-DD]   (quantity x rate items: <eur> is the unit rate)
  split <id> <new-id> <new-label> <eur> [--with '<item JSON>']

Amounts are euros with up to two decimals. --with merges item fields (notes, costType, sourceIds, ...).
Every command validates the whole document against the budget schema and writes it atomically.`;

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function parseFields(json: string | undefined): Partial<BudgetItem> | undefined {
  if (json === undefined) return undefined;
  const value: unknown = JSON.parse(json);
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new CostEditError("--with must be a JSON object of item fields.");
  }
  return value as Partial<BudgetItem>;
}

interface CommandOptions {
  due: string[];
  pricedOn: string;
  fields: Partial<BudgetItem> | undefined;
}

interface CostCommand {
  arity: number;
  run: (document: BudgetDocument, args: string[], options: CommandOptions) => CommandResult;
}

interface CommandResult {
  next: BudgetDocument;
  summary: string;
}

const COMMANDS: Record<string, CostCommand> = {
  add: {
    arity: 4,
    run: (document, [id = "", groupId = "", label = "", eur = ""], options) => ({
      next: addCost(document, {
        id,
        groupId,
        label,
        baseCents: parseEuroCents(eur),
        pricedOn: options.pricedOn,
        dueMonths: options.due,
        ...(options.fields ? { fields: options.fields } : {}),
      }),
      summary: `Added "${id}" to "${groupId}".`,
    }),
  },
  delete: {
    arity: 1,
    run: (document, [id = ""]) => ({
      next: deleteCost(document, id),
      summary: `Deleted "${id}" and its instalments.`,
    }),
  },
  move: {
    arity: 2,
    run: (document, [id = "", groupId = ""]) => ({
      next: moveCost(document, id, groupId),
      summary: `Moved "${id}" to "${groupId}".`,
    }),
  },
  rename: {
    arity: 2,
    run: (document, [id = "", label = ""]) => ({
      next: renameCost(document, id, label),
      summary: `Renamed "${id}" to "${label}".`,
    }),
  },
  "set-price": {
    arity: 2,
    run: (document, [id = "", eur = ""], options) => ({
      next: setCostPrice(document, id, parseEuroCents(eur), options.pricedOn),
      summary: `Set the price of "${id}" to ${eur} EUR and reallocated its instalments.`,
    }),
  },
  split: {
    arity: 4,
    run: (document, [id = "", newId = "", newLabel = "", eur = ""], options) => ({
      next: splitCost(document, {
        id,
        newId,
        newLabel,
        cents: parseEuroCents(eur),
        ...(options.fields ? { fields: options.fields } : {}),
      }),
      summary: `Split ${eur} EUR from "${id}" into "${newId}".`,
    }),
  },
};

function applyCommand(document: BudgetDocument, args: readonly string[]): CommandResult {
  const [name = "", ...rest] = args;
  const command = COMMANDS[name];
  if (!command) throw new CostEditError(COST_USAGE);
  const { values, positionals } = parseArgs({
    args: rest,
    allowPositionals: true,
    options: {
      due: { type: "string", multiple: true },
      "priced-on": { type: "string" },
      with: { type: "string" },
    },
  });
  if (positionals.length !== command.arity) {
    throw new CostEditError(
      `Expected ${command.arity} arguments, got ${positionals.length}.\n\n${COST_USAGE}`,
    );
  }
  return command.run(document, positionals, {
    due: values.due ?? [],
    pricedOn: values["priced-on"] ?? today(),
    fields: parseFields(values.with),
  });
}

/** Writes through a sibling temporary file and refuses to replace a file that changed since it was read. */
async function writeAtomically(
  documentPath: string,
  contents: string,
  revision: string,
): Promise<void> {
  const temporaryPath = join(
    dirname(documentPath),
    `.${basename(documentPath)}.${process.pid}.tmp`,
  );
  await writeFile(temporaryPath, contents, "utf8");
  try {
    if (revisionFor(await readFile(documentPath)) !== revision) {
      throw new CostEditError(
        `${documentPath} changed while the edit ran; nothing was written. Retry.`,
      );
    }
    await rename(temporaryPath, documentPath);
  } finally {
    await rm(temporaryPath, { force: true });
  }
}

/** Runs one cost command against a budget file and returns its summary line. */
export async function runCostCommand(
  args: readonly string[],
  documentPath: string = CANONICAL_DOCUMENT_PATH,
): Promise<string> {
  const { document, revision } = await new BudgetFileReader({ documentPath }).read();
  const { next, summary } = applyCommand(document, args);
  await writeAtomically(documentPath, serializeBudgetDocument(next), revision);
  return summary;
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    console.log(await runCostCommand(process.argv.slice(2)));
  } catch (error) {
    if (
      error instanceof CostEditError ||
      error instanceof BudgetFileError ||
      error instanceof TypeError ||
      error instanceof SyntaxError
    ) {
      console.error(error.message);
      if (error instanceof BudgetFileError) console.error(error.details.join("\n"));
      process.exitCode = 1;
    } else {
      throw error;
    }
  }
}
