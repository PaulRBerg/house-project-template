import type { BudgetDocument, BudgetHierarchyGroup, BudgetView } from "../domain/index.js";
import { formatMoneyInput } from "./format.js";

export function protectCsvFormula(value: string): string {
  return /^[\t\r\n]/.test(value) || /^\s*[=+\-@]/.test(value) ? `'${value}` : value;
}

export function csvCell(value: string | number): string {
  const safe = protectCsvFormula(String(value));
  return `"${safe.replaceAll('"', '""')}"`;
}

function hierarchyPaths(groups: BudgetHierarchyGroup[]): Map<string, string> {
  const result = new Map<string, string>();
  const visit = (group: BudgetHierarchyGroup, parents: string[]): void => {
    const current = [...parents, group.label];
    for (const child of group.children) {
      if (child.kind === "item") result.set(child.id, current.join(" / "));
      else visit(child, current);
    }
  };
  groups.forEach((group) => visit(group, []));
  return result;
}

export function budgetCsv(document: BudgetDocument, view: BudgetView): string {
  const paths = hierarchyPaths(view.hierarchy);
  const milestones = new Map(document.milestones.map((entry) => [entry.id, entry.label]));
  const header = [
    "Element",
    "Categorie",
    "Etapă",
    "Estimare EUR",
    "Prognoză EUR",
    "Plătit EUR",
    "Rămas EUR",
    "Termen",
    "Stare",
    "Furnizor",
    "Note",
  ];
  const rows = view.items.map((entry) => {
    const dueOn = entry.instalments
      .filter((instalment) => instalment.active && instalment.remainingRawCents > 0)
      .flatMap((instalment) => (instalment.dueOn ? [instalment.dueOn] : []))
      .sort()[0];
    const state = entry.effectivelyArchived
      ? "Arhivat"
      : !entry.item.included
        ? "Opțional, neinclus"
        : entry.item.completion.complete
          ? "Finalizat"
          : entry.overdueCents > 0
            ? "Întârziat"
            : "Planificat";
    return [
      entry.item.label,
      paths.get(entry.item.id) ?? "",
      milestones.get(entry.item.milestoneId) ?? entry.item.milestoneId,
      formatMoneyInput(entry.estimateCents),
      formatMoneyInput(entry.forecastCents),
      formatMoneyInput(entry.actualPaidCents),
      formatMoneyInput(Math.max(0, entry.forecastCents - entry.actualPaidCents)),
      dueOn ?? "",
      state,
      entry.item.supplier ?? "",
      entry.item.notes ?? "",
    ];
  });
  return [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
}

export function downloadText(filename: string, contents: string, type: string): void {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

export function downloadBudgetJson(document: BudgetDocument, filename = "buget-casa.json"): void {
  downloadText(
    filename,
    `${JSON.stringify(document, null, 2)}\n`,
    "application/json;charset=utf-8",
  );
}
