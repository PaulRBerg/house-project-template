import { readFile, readdir } from "node:fs/promises";

import { describe, expect, it } from "vitest";

import { hasCategoryIcon } from "../components/shared/CategoryIcon.js";
import { parseBudgetDocument } from "../domain/schema.js";
import { estimateCents } from "../domain/selectors.js";
import { CANONICAL_DOCUMENT_PATH } from "../server/budget-file-reader.js";

const briefUrl = new URL("../../../brief/", import.meta.url);

async function loadDocument() {
  return parseBudgetDocument(JSON.parse(await readFile(CANONICAL_DOCUMENT_PATH, "utf8")));
}

function markdownCells(line: string): string[] {
  return line
    .trim()
    .split("|")
    .slice(1, -1)
    .map((cell) => cell.trim());
}

async function briefDefinitionIds(): Promise<Set<string>> {
  const entries = await readdir(briefUrl, { withFileTypes: true });
  const markdown = await Promise.all(
    entries
      .filter((entry) => entry.isFile() && entry.name.endsWith(".md"))
      .map(async (entry) => ({
        file: entry.name,
        content: await readFile(new URL(entry.name, briefUrl), "utf8"),
      })),
  );
  const records = new Map<string, string>();

  for (const { file, content } of markdown) {
    const lines = content.split("\n");
    for (let index = 0; index < lines.length; index += 1) {
      if (markdownCells(lines[index] ?? "")[0] !== "ID") continue;
      index += 2;
      while ((lines[index] ?? "").trimStart().startsWith("|")) {
        const recordId = /^`([^`]+)`$/.exec(markdownCells(lines[index] ?? "")[0] ?? "")?.[1];
        if (recordId === undefined)
          throw new Error(`Tabelul cu definiții din ${file} are un ID invalid.`);
        const previousFile = records.get(recordId);
        if (previousFile !== undefined)
          throw new Error(`ID-ul brief ${recordId} este definit în ${previousFile} și ${file}.`);
        records.set(recordId, file);
        index += 1;
      }
      index -= 1;
    }
  }
  return new Set(records.keys());
}

// Structural invariants only: nothing here pins the catalogue's current contents.
describe("canonical budget document", () => {
  // The strict schema already enforces field shapes and in-document references.
  it("parses and round-trips", async () => {
    const raw = JSON.parse(await readFile(CANONICAL_DOCUMENT_PATH, "utf8"));
    expect(raw).toEqual(parseBudgetDocument(raw));
  });

  it("resolves every brief reference", async () => {
    const [document, definitionIds] = await Promise.all([loadDocument(), briefDefinitionIds()]);
    for (const item of document.items) {
      for (const reference of item.briefReferences)
        expect(definitionIds.has(reference.recordId), `${item.id}: ${reference.recordId}`).toBe(
          true,
        );
    }
  });

  it("keeps every item in a leaf category", async () => {
    const document = await loadDocument();
    const groupsWithChildren = new Set(
      document.groups.flatMap((group) => (group.parentId === null ? [] : [group.parentId])),
    );
    for (const item of document.items) {
      expect(groupsWithChildren.has(item.groupId), item.id).toBe(false);
    }
  });

  it("maps every category to its own icon", async () => {
    const document = await loadDocument();
    for (const group of document.groups) {
      expect(hasCategoryIcon(group.id), group.id).toBe(true);
    }
  });

  it("reconciles every planned included item with instalments to its base estimate", async () => {
    const document = await loadDocument();
    const scheduled = new Map<string, number>();
    for (const instalment of document.instalments) {
      scheduled.set(
        instalment.itemId,
        (scheduled.get(instalment.itemId) ?? 0) + instalment.projectedCents,
      );
    }

    const scheduledItems = document.items.filter(
      (item) => item.ownership === "planned" && item.included && scheduled.has(item.id),
    );
    for (const item of scheduledItems) {
      expect(scheduled.get(item.id), item.id).toBe(estimateCents(item.estimate));
    }
    expect(scheduledItems.length).toBeGreaterThan(0);
  });
});
