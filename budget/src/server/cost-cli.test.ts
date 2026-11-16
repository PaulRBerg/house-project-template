import { copyFile, mkdtemp, readdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { parseBudgetDocument, type BudgetDocument } from "../domain/schema.js";
import { estimateCents } from "../domain/selectors.js";
import { serializeBudgetDocument } from "../domain/serialization.js";
import { CANONICAL_DOCUMENT_PATH } from "./budget-file-reader.js";
import { runCostCommand } from "./cost-cli.js";

let directory: string;
let documentPath: string;

async function load(): Promise<BudgetDocument> {
  return parseBudgetDocument(JSON.parse(await readFile(documentPath, "utf8")));
}

function instalmentCents(document: BudgetDocument, itemId: string): number[] {
  return document.instalments
    .filter((row) => row.itemId === itemId)
    .map((row) => row.projectedCents);
}

function sum(values: readonly number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

/** A total-estimate item with two or more instalments and no payments, taken from the real catalogue copy. */
function splittableItem(document: BudgetDocument): BudgetDocument["items"][number] {
  const item = document.items.find(
    (candidate) =>
      candidate.estimate.kind === "total" &&
      instalmentCents(document, candidate.id).length >= 2 &&
      !document.payments.some((payment) => payment.itemId === candidate.id),
  );
  if (!item) throw new Error("The catalogue copy has no splittable item.");
  return item;
}

beforeEach(async () => {
  directory = await mkdtemp(join(tmpdir(), "budget-cost-cli-"));
  documentPath = join(directory, "project.json");
  await copyFile(CANONICAL_DOCUMENT_PATH, documentPath);
});

afterEach(async () => {
  await rm(directory, { recursive: true, force: true });
});

describe("cost CLI on a copy of the canonical catalogue", () => {
  it("adds an item at the end of a leaf category with derived milestone and instalments", async () => {
    const before = await load();
    const leaf = before.groups.find(
      (group) =>
        group.parentId !== null && !before.groups.some((child) => child.parentId === group.id),
    );
    if (!leaf) throw new Error("No leaf category.");
    await runCostCommand(
      [
        "add",
        "test-new-cost",
        leaf.id,
        "Cost nou",
        "1000.01",
        "--due",
        "2027-10",
        "--due",
        "2027-11",
        "--with",
        '{"notes":"Test."}',
      ],
      documentPath,
    );
    const after = await load();
    const item = after.items.find((candidate) => candidate.id === "test-new-cost");
    expect(item?.milestoneId).toBe(leaf.milestoneId);
    expect(item?.notes).toBe("Test.");
    expect(instalmentCents(after, "test-new-cost")).toEqual([50_001, 50_000]);
  });

  it("deletes an item with its instalments", async () => {
    const target = splittableItem(await load());
    await runCostCommand(["delete", target.id], documentPath);
    const after = await load();
    expect(after.items.some((item) => item.id === target.id)).toBe(false);
    expect(instalmentCents(after, target.id)).toEqual([]);
  });

  it("moves an item and takes the target category's milestone", async () => {
    const before = await load();
    const target = splittableItem(before);
    const leaf = before.groups.find(
      (group) =>
        group.milestoneId !== target.milestoneId &&
        group.parentId !== null &&
        !before.groups.some((child) => child.parentId === group.id),
    );
    if (!leaf) throw new Error("No other leaf category.");
    await runCostCommand(["move", target.id, leaf.id], documentPath);
    const moved = (await load()).items.find((item) => item.id === target.id);
    expect(moved?.groupId).toBe(leaf.id);
    expect(moved?.milestoneId).toBe(leaf.milestoneId);
  });

  it("renames an item", async () => {
    const target = splittableItem(await load());
    await runCostCommand(["rename", target.id, "Etichetă nouă"], documentPath);
    expect((await load()).items.find((item) => item.id === target.id)?.label).toBe("Etichetă nouă");
  });

  it("sets a price and reallocates instalments exactly to the cent", async () => {
    const target = splittableItem(await load());
    await runCostCommand(
      ["set-price", target.id, "1234.57", "--priced-on", "2026-10-08"],
      documentPath,
    );
    const after = await load();
    const item = after.items.find((candidate) => candidate.id === target.id);
    expect(item && estimateCents(item.estimate)).toBe(123_457);
    expect(item?.estimate.pricedOn).toBe("2026-10-08");
    expect(sum(instalmentCents(after, target.id))).toBe(123_457);
  });

  it("splits an item and keeps the combined total and instalment dates", async () => {
    const before = await load();
    const target = splittableItem(before);
    const total = estimateCents(target.estimate);
    await runCostCommand(
      ["split", target.id, "test-split-part", "Parte separată", "100"],
      documentPath,
    );
    const after = await load();
    expect(sum(instalmentCents(after, "test-split-part"))).toBe(10_000);
    expect(sum(instalmentCents(after, target.id))).toBe(total - 10_000);
    expect(instalmentCents(after, "test-split-part")).toHaveLength(
      instalmentCents(before, target.id).length,
    );
  });

  it("rejects an invalid edit and leaves the file byte-identical without a temporary file", async () => {
    const original = await readFile(documentPath, "utf8");
    const target = splittableItem(await load());
    await expect(runCostCommand(["move", target.id, "construction"], documentPath)).rejects.toThrow(
      /leaf categories/,
    );
    await expect(runCostCommand(["set-price", target.id, "12.345"], documentPath)).rejects.toThrow(
      /two decimals/,
    );
    expect(await readFile(documentPath, "utf8")).toBe(original);
    expect(await readdir(directory)).toEqual(["project.json"]);
  });

  it("writes canonical serialization", async () => {
    const target = splittableItem(await load());
    await runCostCommand(["rename", target.id, "Alt nume"], documentPath);
    const raw = await readFile(documentPath, "utf8");
    expect(raw).toBe(serializeBudgetDocument(parseBudgetDocument(JSON.parse(raw))));
  });
});
