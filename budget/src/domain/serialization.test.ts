import { describe, expect, it } from "vitest";

import { parseBudgetDocument } from "./schema.js";
import { serializeBudgetDocument } from "./serialization.js";
import { makeDocument, makeItem } from "./test-fixtures.js";

describe("serializeBudgetDocument", () => {
  it("round-trips normal JSON with one catalogue record per line", () => {
    const document = makeDocument({
      items: Array.from({ length: 100 }, (_, index) =>
        makeItem({
          id: `element-${index}`,
          label: `Element ${index}`,
          sortOrder: index,
          areaId: index === 0 ? "living-room" : undefined,
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
    expect(parsed.items[0]?.areaId).toBe("living-room");
  });
});
