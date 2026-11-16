import { RECORD_COLLECTION_KEYS, type BudgetDocument } from "./schema.js";

/**
 * Keeps the canonical JSON readable while guaranteeing one array record per line.
 * This avoids turning a useful ~100-item catalogue into a file over 1,000 lines.
 */
export function serializeBudgetDocument(document: BudgetDocument): string {
  const lines = ["{"];
  lines.push(`  "schemaVersion": ${JSON.stringify(document.schemaVersion)},`);
  lines.push(`  "project": ${JSON.stringify(document.project)},`);
  RECORD_COLLECTION_KEYS.forEach((key, keyIndex) => {
    lines.push(`  "${key}": [`);
    const records = document[key] as ReadonlyArray<unknown>;
    records.forEach((record, recordIndex) => {
      const comma = recordIndex < records.length - 1 ? "," : "";
      lines.push(`    ${JSON.stringify(record)}${comma}`);
    });
    const comma = keyIndex < RECORD_COLLECTION_KEYS.length - 1 ? "," : "";
    lines.push(`  ]${comma}`);
  });
  lines.push("}");
  return `${lines.join("\n")}\n`;
}
