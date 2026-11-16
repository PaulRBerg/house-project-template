import { describe, expect, it } from "vitest";

import { selectBudgetView } from "../domain/index.js";
import { makeDocument, makeItem } from "../test/builders.js";
import {
  formatBpsPercent,
  formatCount,
  formatDate,
  formatItemCost,
  formatMoney,
  formatMoneyRange,
  formatMonth,
  formatPercent,
} from "./format.js";

describe("formatare", () => {
  it("afișează sumele cu virgulă ca separator pentru mii", () => {
    expect(formatMoney(4_247_300)).toBe("€42,473");
    expect(formatMoney(123_456, true)).toBe("€1,234.56");
  });

  it("unește estimarea și prognoza, dar nu repetă valori egale", () => {
    expect(formatMoneyRange(260_000, 296_300)).toBe("€2,600–€2,963");
    expect(formatMoneyRange(8_250_000, 8_250_000)).toBe("€82,500");
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

  it("acordă numeralele românești, inclusiv «de» de la 20 în sus", () => {
    const forms = { one: "element", other: "elemente" };
    expect([1, 2, 19, 20, 101, 120].map((count) => formatCount(count, forms))).toEqual([
      "1 element",
      "2 elemente",
      "19 elemente",
      "20 de elemente",
      "101 elemente",
      "120 de elemente",
    ]);
  });

  it("păstrează cei patru digiți ai anului la conversia dus-întors", () => {
    expect(formatDate("0100-01-01")).toBe("1 Ian 0100");
    expect(formatMonth("0100-01")).toBe("Ian 0100");
  });

  it("shows the estimate, not a backwards range, for unpaid excluded or archived items", () => {
    const view = selectBudgetView(
      makeDocument({
        items: [
          makeItem({ id: "optional", included: false }),
          makeItem({ id: "archived", archived: true, sortOrder: 1 }),
        ],
        instalments: [],
      }),
      { asOf: "2026-09-18" },
    );
    expect(view.items.map(formatItemCost)).toEqual(["€100", "€100"]);
  });

  it("formats basis points and ratios as Romanian percentages", () => {
    expect(formatBpsPercent(1_000)).toBe("10\u00A0%");
    expect(formatPercent(0.352)).toBe("35,2\u00A0%");
  });
});
