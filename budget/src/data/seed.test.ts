import { readFile } from "node:fs/promises";

import { describe, expect, it } from "vitest";

import { budgetDocumentSchema, selectBudgetView, type BudgetItem } from "../domain/index.js";

async function loadSeed() {
  const input = JSON.parse(
    await readFile(new URL("../../data/project.json", import.meta.url), "utf8"),
  );
  return budgetDocumentSchema.parse(input);
}

function baseEstimateCents(item: BudgetItem): number {
  return item.estimate.kind === "total"
    ? item.estimate.amounts.baseCents
    : Math.round(item.estimate.quantity * item.estimate.rates.baseCents);
}

describe("demo budget seed", () => {
  it("is a valid anonymous four-stage document", async () => {
    const document = await loadSeed();

    expect(document.project).toMatchObject({
      id: "demo-house",
      name: "Demo House",
      location: "Not specified",
      builtAreaSqm: 48,
    });
    expect(document.milestones).toEqual([
      { id: "la-rosu", label: "La roșu", date: "2030-03" },
      { id: "la-gri", label: "La gri", date: "2030-06" },
      { id: "la-cheie", label: "La cheie", date: "2030-09" },
      { id: "la-mutat", label: "La mutat", date: "2030-10" },
    ]);
    expect(document.groups.map((group) => group.id)).toEqual([
      "construction",
      "rough",
      "finish",
      "move",
    ]);
    expect(document.groups.map((group) => group.label)).toEqual([
      "La roșu",
      "La gri",
      "La cheie",
      "La mutat",
    ]);
  });

  it("contains two clearly fictional estimates per stage and no private evidence", async () => {
    const document = await loadSeed();

    expect(document.items).toHaveLength(8);
    for (const milestone of document.milestones) {
      expect(document.items.filter((item) => item.milestoneId === milestone.id)).toHaveLength(2);
    }
    for (const item of document.items) {
      expect(item.notes).toMatch(/Fictional/);
      expect(item.briefReferences).toEqual([]);
      expect(item.sourceIds).toEqual([]);
    }
    expect(document.sources).toEqual([]);
    expect(document.payments).toEqual([]);
  });

  it("matches every base estimate to one dated instalment and produces four cash-flow months", async () => {
    const document = await loadSeed();
    const instalmentsByItem = new Map(
      document.instalments.map((instalment) => [instalment.itemId, instalment]),
    );

    expect(document.instalments).toHaveLength(document.items.length);
    for (const item of document.items) {
      const instalment = instalmentsByItem.get(item.id);
      expect(instalment?.projectedCents).toBe(baseEstimateCents(item));
      expect(instalment?.dueOn).toBe(
        document.milestones.find((milestone) => milestone.id === item.milestoneId)?.date,
      );
    }

    const view = selectBudgetView(document, { scenario: "base", asOf: "2030-01-01" });
    expect(view.timeline.map((stage) => stage.itemCount)).toEqual([2, 2, 2, 2]);
    expect(view.monthlyCashFlow.months.map((month) => month.month)).toEqual([
      "2030-03",
      "2030-06",
      "2030-09",
      "2030-10",
    ]);
    expect(view.monthlyCashFlow.months.map((month) => month.scheduledCents)).toEqual([
      220_000, 170_000, 118_000, 80_000,
    ]);
  });
});
