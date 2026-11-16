import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { assert, describe, expect, it } from "vitest";

import { budgetDocumentSchema, selectBudgetView, type BudgetDocument } from "../../domain/index.js";
import { makeBeneficiary, makeDocument, makeItem, makeSource } from "../../test/builders.js";
import { render, screen, within } from "../../test/render.js";
import { ItemDetails } from "./ItemDetails.js";

function renderDetails(document: BudgetDocument, itemId = document.items[0]?.id) {
  const view = selectBudgetView(document, { asOf: "2026-09-19", scope: "all" });
  const entry = view.items.find((candidate) => candidate.item.id === itemId);
  assert(entry);
  return render(
    <ItemDetails
      document={document}
      entry={entry}
      onClose={() => undefined}
      onExited={() => undefined}
      open
    />,
  );
}

describe("ItemDetails", () => {
  it("exposes linked evidence and estimate context without item editing controls", () => {
    const source = makeSource({
      provenance: { currency: "RON", note: "Conversie documentată la data estimării." },
    });
    const item = makeItem({
      sourceIds: [source.id],
      notes: "Alocație pentru materiale și manoperă.",
      brand: "Constructor local",
      estimate: {
        kind: "quantity-rate",
        quantity: 260,
        quantityBasis: "built-area",
        unit: "m²",
        rates: { baseCents: 1_500 },
        pricedOn: "2026-09-18",
        fixed: false,
      },
    });
    renderDetails(
      makeDocument({
        items: [item],
        sources: [source, makeSource({ id: "unlinked", title: "Sursă fără legătură" })],
      }),
    );

    const dialog = screen.getByRole("dialog", { name: item.label });
    const sourceLink = within(dialog).getByRole("link", { name: source.title });
    expect(sourceLink).toHaveAttribute("href", "https://example.com/oferta");
    expect(sourceLink).toHaveAttribute("target", "_blank");
    expect(sourceLink).toHaveAttribute("rel", "noreferrer");
    for (const text of [
      source.title,
      source.scope,
      "Accesată 18 Sep 2026",
      "încredere medie",
      "TVA inclus (21 %)",
      "Moneda sursei: RON",
      "Conversie documentată la data estimării.",
      "Alocație pentru materiale și manoperă.",
      "Marcă",
      "Constructor local",
      "Beneficiar",
      "TBD",
      "budget-001",
      "€3,900",
      "260 m² × €15.00/m² · aria construită desfășurată",
    ]) {
      expect(dialog).toHaveTextContent(text);
    }
    expect(dialog).not.toHaveTextContent("Sursă fără legătură");
    expect(dialog).not.toHaveTextContent("€25.00");
    expect(dialog.querySelector("form, input, textarea, select")).not.toBeInTheDocument();
    expect(within(dialog).getAllByRole("button")).toHaveLength(1);
    expect(within(dialog).getByRole("button", { name: "Închide" })).toBeInTheDocument();
  });

  it("explains missing external evidence while preserving household notes and references", () => {
    const item = makeItem({ notes: "Alocație acceptată de gospodărie." });
    renderDetails(makeDocument({ items: [item] }));

    const dialog = screen.getByRole("dialog", { name: item.label });
    expect(dialog).toHaveTextContent("Nu există o sursă externă atașată acestui reper.");
    expect(dialog).toHaveTextContent("Alocație acceptată de gospodărie.");
    expect(dialog).toHaveTextContent("budget-001");
  });

  it("shows the assigned beneficiary's name", () => {
    const beneficiary = makeBeneficiary();
    const item = makeItem({ beneficiaryId: beneficiary.id });
    renderDetails(makeDocument({ beneficiaries: [beneficiary], items: [item] }));

    const dialog = screen.getByRole("dialog", { name: item.label });
    expect(dialog).toHaveTextContent("Beneficiar");
    expect(dialog).toHaveTextContent("Constructor Exemplu");
    expect(dialog).not.toHaveTextContent("TBD");
  });

  it("renders item notes as safe Markdown", () => {
    const item = makeItem({
      notes:
        "Paragraf cu **etichetă importantă**.\n\n- Material inclus\n- [Ofertă externă](https://example.com/oferta?currency=EUR)\n\n1. Prima etapă\n2. A doua etapă\n\n<script>window.alert('xss')</script>",
    });
    renderDetails(makeDocument({ items: [item] }));

    const dialog = screen.getByRole("dialog", { name: item.label });
    expect(within(dialog).getByText("etichetă importantă").tagName).toBe("STRONG");
    expect(dialog.querySelector("ul")).toBeInTheDocument();
    expect(dialog.querySelector("ol")).toBeInTheDocument();
    const noteLink = within(dialog).getByRole("link", { name: "Ofertă externă" });
    expect(noteLink).toHaveAttribute("href", "https://example.com/oferta?currency=EUR");
    expect(noteLink).toHaveAttribute("target", "_blank");
    expect(noteLink).toHaveAttribute("rel", "noreferrer");
    expect(dialog.querySelector("script")).not.toBeInTheDocument();
    expect(dialog).not.toHaveTextContent("window.alert");
  });

  it("shows owned historical prices without presenting them as future cash forecasts", () => {
    const item = makeItem({ ownership: "owned", completion: { complete: true } });
    renderDetails(makeDocument({ items: [item], instalments: [] }));

    const dialog = screen.getByRole("dialog", { name: item.label });
    expect(dialog).toHaveTextContent("Preț istoric");
    expect(dialog).toHaveTextContent("€100");
    expect(dialog).toHaveTextContent("Plătit");
    expect(dialog).not.toHaveTextContent("Deja cumpărat");
    expect(dialog).not.toHaveTextContent("Prognoză:");
  });

  it("identifies owned adjustable estimates as historical estimated values", () => {
    const item = makeItem({
      ownership: "owned",
      completion: { complete: true },
      estimate: {
        kind: "total",
        amounts: { baseCents: 10_000 },
        fixed: false,
        pricedOn: "2026-09-18",
      },
    });
    renderDetails(makeDocument({ items: [item], instalments: [] }));

    const dialog = screen.getByRole("dialog", { name: item.label });
    expect(dialog).toHaveTextContent("Valoare istorică estimată");
    expect(dialog).not.toHaveTextContent("Preț istoric");
  });

  it("makes every current catalogue item's linked sources accessible in its details", () => {
    const document = budgetDocumentSchema.parse(
      JSON.parse(readFileSync(resolve(process.cwd(), "data/project.json"), "utf8")),
    );

    for (const item of document.items) {
      const view = renderDetails(document, item.id);
      const dialog = screen.getByRole("dialog", { name: item.label });
      const linkedSources = document.sources.filter((source) => item.sourceIds.includes(source.id));
      const sourceLinks = [...dialog.querySelectorAll<HTMLAnchorElement>("article a")];

      expect(dialog.querySelectorAll("article"), item.id).toHaveLength(linkedSources.length);
      for (const source of linkedSources) {
        expect(
          sourceLinks.some((link) => link.href === source.url),
          `${item.id}: ${source.id}`,
        ).toBe(true);
      }
      view.unmount();
    }
  });
});
