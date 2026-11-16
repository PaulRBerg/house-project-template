import { describe, expect, it } from "vitest";

import { makeBeneficiary, makeDocument, makeItem } from "../test/builders.js";
import { parseBudgetDocument } from "./schema.js";
import { serializeBudgetDocument } from "./serialization.js";

describe("serializeBudgetDocument", () => {
  it("round-trips normal JSON with one catalogue record per line", () => {
    const document = makeDocument({
      items: Array.from({ length: 100 }, (_, index) =>
        makeItem({
          id: `element-${index}`,
          label: `Element ${index}`,
          sortOrder: index,
          areaId: index === 0 ? "G-LIV" : undefined,
          paymentMode: index % 2 === 0 ? "one-off" : "partial-progress",
        }),
      ),
      instalments: [],
    });
    const serialized = serializeBudgetDocument(document);
    expect(serialized.split("\n").length).toBeLessThan(150);
    const parsed = parseBudgetDocument(JSON.parse(serialized));
    expect(parsed).toEqual(document);
    expect(new Set(parsed.items.map((item) => item.paymentMode))).toEqual(
      new Set(["one-off", "partial-progress"]),
    );
    expect(parsed.items[0]?.areaId).toBe("G-LIV");
  });

  it("round-trips beneficiaries and an item's beneficiaryId", () => {
    const beneficiary = makeBeneficiary({ id: "constructor-exemplu", name: "Constructor Exemplu" });
    const document = makeDocument({
      beneficiaries: [beneficiary],
      items: [makeItem({ beneficiaryId: "constructor-exemplu" })],
    });
    const serialized = serializeBudgetDocument(document);
    const parsed = parseBudgetDocument(JSON.parse(serialized));
    expect(parsed).toEqual(document);
    expect(parsed.beneficiaries).toEqual([beneficiary]);
    expect(parsed.items[0]?.beneficiaryId).toBe("constructor-exemplu");
  });
});
