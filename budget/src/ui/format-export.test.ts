import { describe, expect, it } from "vitest";

import { selectBudgetView } from "../domain/index.js";
import { makeDocument, makeInstalment, makePayment } from "../domain/test-fixtures.js";
import { budgetCsv, csvCell, protectCsvFormula } from "./export.js";
import {
  formatDate,
  formatMoney,
  formatMoneyRange,
  formatMonth,
  parseDateInput,
  parseEuroToCents,
} from "./format.js";

describe("intrări și exporturi monetare", () => {
  it("exports the estimate and forecast without a scenario column", () => {
    const document = makeDocument();
    const view = selectBudgetView(document, { scenario: "base", asOf: "2026-09-18" });
    const csv = budgetCsv(document, view);
    expect(csv).toContain('"Estimare EUR","Prognoză EUR"');
    expect(csv).toContain('"100.00","110.00"');
    expect(csv).not.toMatch(/Scenariu|Optimist|Prudent/);
  });

  it("afișează sumele cu virgulă ca separator pentru mii", () => {
    expect(formatMoney(4_247_300)).toBe("€42,473");
    expect(formatMoney(123_456, true)).toBe("€1,234.56");
  });

  it("unește estimarea și prognoza, dar nu repetă valori egale", () => {
    expect(formatMoneyRange(120_000, 136_500)).toBe("€1,200–€1,365");
    expect(formatMoneyRange(12_300, 12_300)).toBe("€123");
  });

  it("transformă EUR cu virgulă sau punct fără erori binare", () => {
    expect(parseEuroToCents("1 234,56")).toBe(123_456);
    expect(parseEuroToCents("0.7")).toBe(70);
    expect(parseEuroToCents("12,345")).toBeNull();
  });

  it("formatează datele calendaristice românești fără dependență de fusul orar", () => {
    expect(
      [
        "2027-01-01",
        "2027-02-01",
        "2027-03-01",
        "2027-04-01",
        "2027-05-01",
        "2027-06-01",
        "2027-07-01",
        "2027-08-01",
        "2027-09-01",
        "2027-10-01",
        "2027-11-01",
        "2027-12-01",
      ].map(formatDate),
    ).toEqual([
      "1 Ian 2027",
      "1 Feb 2027",
      "1 Mar 2027",
      "1 Apr 2027",
      "1 Mai 2027",
      "1 Iun 2027",
      "1 Iul 2027",
      "1 Aug 2027",
      "1 Sep 2027",
      "1 Oct 2027",
      "1 Noi 2027",
      "1 Dec 2027",
    ]);
    expect(formatDate("2028-02-29")).toBe("29 Feb 2028");
    expect(formatDate("2028-02")).toBe("Feb 2028");
    expect(formatMonth("2027-09")).toBe("Sep 2027");
  });

  it("acceptă numai date calendaristice editoriale valide", () => {
    expect(parseDateInput("29 Feb 2028")).toBe("2028-02-29");
    expect(parseDateInput("29 Feb 2027")).toBeNull();
    expect(parseDateInput("31 Apr 2027")).toBeNull();
    expect(parseDateInput("")).toBeNull();
  });

  it("păstrează cei patru digiți ai anului la conversia dus-întors", () => {
    expect(formatDate("0100-01-01")).toBe("1 Ian 0100");
    expect(formatMonth("0100-01")).toBe("Ian 0100");
    expect(parseDateInput(formatDate("0100-01-01"))).toBe("0100-01-01");
  });

  it("neutralizează formulele CSV inclusiv după spații sau tab", () => {
    expect(protectCsvFormula(" =2+2")).toBe("' =2+2");
    expect(protectCsvFormula("\tSUM(A1:A2)")).toBe("'\tSUM(A1:A2)");
    expect(csvCell('Mobilier "custom"')).toBe('"Mobilier ""custom"""');
  });

  it("exportă următorul termen neachitat, nu avansul deja plătit", () => {
    const document = makeDocument({
      instalments: [
        makeInstalment({ projectedCents: 5_000, dueOn: "2027-01" }),
        makeInstalment({ id: "transa-finala", projectedCents: 5_000, dueOn: "2027-03" }),
      ],
      payments: [makePayment({ amountCents: 5_000 })],
    });
    const view = selectBudgetView(document, { scenario: "base", asOf: "2027-01-02" });
    const csv = budgetCsv(document, view);
    expect(csv).toContain('"2027-03"');
    expect(csv).not.toContain('"2027-01"');
    expect(view.upcomingPayments[0]?.dueOn).toBe("2027-03");
  });
});
