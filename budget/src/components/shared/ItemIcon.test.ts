import { readFileSync } from "node:fs";

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { budgetDocumentSchema } from "../../domain/index.js";
import { ItemIcon, hasExplicitItemIcon } from "./ItemIcon.js";

describe("ItemIcon", () => {
  it("covers every item in the demo catalogue", () => {
    const document = budgetDocumentSchema.parse(
      JSON.parse(readFileSync(new URL("../../../data/project.json", import.meta.url), "utf8")),
    );
    for (const item of document.items) {
      expect(hasExplicitItemIcon(item.id), item.id).toBe(true);
      expect(
        renderToStaticMarkup(createElement(ItemIcon, { itemId: item.id })),
        item.id,
      ).not.toContain("lucide-package flex-none");
    }
  });

  it("uses a neutral fallback for later catalogue items", () => {
    expect(hasExplicitItemIcon("future-item")).toBe(false);
    expect(renderToStaticMarkup(createElement(ItemIcon, { itemId: "future-item" }))).toContain(
      "lucide-package flex-none",
    );
  });
});
