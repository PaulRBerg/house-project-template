import { describe, expect, it, vi } from "vitest";

import { App } from "./App.js";
import { makeUiDocument } from "./test/fixtures.js";
import { render, screen, waitFor, within } from "./test/render.js";

const revision = "a".repeat(64);

async function selectOption(
  user: ReturnType<typeof render>["user"],
  label: string,
  option: string,
) {
  await user.click(screen.getByRole("combobox", { name: label }));
  await user.click(await screen.findByRole("option", { name: option }));
}

function installFetch(document = makeUiDocument()) {
  vi.mocked(fetch).mockImplementation((input) => {
    if (String(input) === "/api/budget") {
      return Promise.resolve(Response.json({ document, revision }));
    }
    if (String(input) === "/api/exchange-rate") {
      return Promise.resolve(
        Response.json({
          fetchedAt: "2026-09-19T12:00:00.000Z",
          rateDate: "2026-09-19",
          ronPerEur: 5.1,
          source: "BNR",
          sourceUrl: "https://example.com/rate",
          stale: false,
        }),
      );
    }
    return Promise.reject(new Error(`Unexpected fetch request: ${String(input)}`));
  });
}

describe("App interactions", () => {
  it.each(["", "category=professional", "category=missing"])(
    "defaults to La roșu with one stage tab bar for query %s",
    async (searchParams) => {
      installFetch();
      render(<App />, { searchParams });
      const tabList = await screen.findByRole("tablist", { name: "Etapele proiectului" });
      expect(screen.getAllByRole("tablist")).toHaveLength(1);
      expect(
        within(tabList)
          .getAllByRole("tab")
          .map((tab) => tab.getAttribute("aria-label")),
      ).toEqual(["La roșu", "La gri", "La cheie", "La mutat"]);
      expect(screen.getByRole("tab", { name: "La roșu" })).toHaveAttribute("aria-selected", "true");
      expect(screen.getByRole("tabpanel", { name: "La roșu" })).toBeVisible();
      expect(screen.getByRole("button", { name: "Arhitectură" })).toBeVisible();
      expect(screen.getByRole("tab", { name: "La roșu" })).toHaveTextContent("până la");
      expect(screen.getByRole("tab", { name: "La roșu" })).toHaveTextContent("gata");
    },
  );

  it("keeps stage tabs mounted during keyboard navigation and reopens collapsed groups", async () => {
    installFetch();
    const { user } = render(<App />);
    const construction = await screen.findByRole("tab", { name: "La roșu" });
    const rough = screen.getByRole("tab", { name: "La gri" });
    const move = screen.getByRole("tab", { name: "La mutat" });
    await user.click(screen.getByRole("button", { name: "Restrânge Proiectare și consultanță" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Arhitectură" })).not.toBeInTheDocument(),
    );
    construction.focus();
    await user.keyboard("{ArrowRight}");
    expect(rough).toHaveFocus();
    expect(rough).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "La gri" })).toBeVisible();
    await user.keyboard("{End}");
    expect(move).toHaveFocus();
    expect(move).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowRight}");
    expect(construction).toHaveFocus();
    expect(construction).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("button", { name: "Arhitectură" })).toBeVisible();
    await user.keyboard("{ArrowLeft}");
    expect(move).toHaveFocus();
    await user.keyboard("{Home}");
    expect(construction).toHaveFocus();
  });

  it("honors initial query state and pushes budget, category, and grouping navigation", async () => {
    installFetch();
    const onUrlUpdate = vi.fn();
    const { user } = render(<App />, {
      onUrlUpdate,
      searchParams: "page=flux&category=move&grouping=categories",
    });

    expect(await screen.findByRole("heading", { name: "Fluxul de numerar" })).toBeVisible();
    onUrlUpdate.mockClear();
    await user.click(screen.getByRole("button", { name: "Buget" }));
    expect(await screen.findByRole("tab", { name: "La roșu" })).toBeVisible();
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalledOnce());
    expect(onUrlUpdate.mock.calls[0]?.[0]).toMatchObject({
      options: expect.objectContaining({ history: "push" }),
      queryString: "?category=move&grouping=categories",
    });

    onUrlUpdate.mockClear();
    await user.click(screen.getByRole("tab", { name: "La cheie" }));
    expect(document.activeElement).toBe(screen.getByRole("tab", { name: "La cheie" }));
    expect(screen.getByRole("tab", { name: "La cheie" })).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalledOnce());
    expect(onUrlUpdate.mock.calls[0]?.[0]).toMatchObject({
      options: expect.objectContaining({ history: "push" }),
      queryString: "?category=finish&grouping=categories",
    });
    expect(screen.getByRole("button", { name: "Pe categorii" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    onUrlUpdate.mockClear();
    await user.click(screen.getByRole("button", { name: "Pe camere" }));
    expect(screen.getByRole("button", { name: "Pe camere" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalledOnce());
    expect(onUrlUpdate.mock.calls[0]?.[0]).toMatchObject({
      options: expect.objectContaining({ history: "push" }),
      queryString: "?category=finish",
    });

    onUrlUpdate.mockClear();
    await user.click(screen.getByRole("button", { name: "Pe categorii" }));
    expect(screen.getByRole("button", { name: "Pe categorii" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalledOnce());
    expect(onUrlUpdate.mock.calls[0]?.[0]).toMatchObject({
      options: expect.objectContaining({ history: "push" }),
      queryString: "?category=finish&grouping=categories",
    });

    onUrlUpdate.mockClear();
    await user.click(screen.getByRole("tab", { name: "La roșu" }));
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalledOnce());
    expect(onUrlUpdate.mock.calls[0]?.[0]).toMatchObject({
      options: expect.objectContaining({ history: "push" }),
      queryString: "",
    });
  });

  it("filters the selected category by search, scope, and status, including its empty state", async () => {
    installFetch();
    const { user } = render(<App />);
    expect(await screen.findByRole("tab", { name: "La roșu" })).toBeVisible();
    await user.click(screen.getByRole("tab", { name: "La mutat" }));
    expect(screen.getByRole("button", { name: "Canapea mobilă" })).toBeVisible();

    await selectOption(user, "Tip de cost", "Buget de bază");
    expect(screen.getByText(/Niciun element din (categoria|etapa) La mutat/i)).toBeVisible();
    await selectOption(user, "Tip de cost", "Bunuri mobile");
    await selectOption(user, "Stare", "Arhivate");
    expect(screen.getByRole("button", { name: "Scaun arhivat" })).toBeVisible();

    await selectOption(user, "Stare", "Toate stările");
    await user.type(
      screen.getByRole("searchbox", { name: "Caută în categoria selectată" }),
      "fără rezultat",
    );
    expect(screen.getByText(/Niciun element din (categoria|etapa) La mutat/i)).toBeVisible();
  });

  it("opens budget evidence and changes the cash-flow milestone", async () => {
    installFetch();
    const { user } = render(<App />);
    expect(await screen.findByRole("button", { name: "Arhitectură" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Arhitectură" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Arhitectură");

    await user.click(screen.getByRole("button", { name: "Închide" }));
    await user.click(screen.getByRole("button", { name: "Flux" }));
    expect(await screen.findByRole("heading", { name: "Fluxul de numerar" })).toBeVisible();
    await selectOption(user, "Etapă", "La mutat");
    expect(screen.getByText(/Jalon filtrat/)).toBeVisible();
    const cashFlowItem = screen
      .getAllByText("Canapea mobilă")
      .map((element) => element.closest("button"))
      .find((element) => element !== null);
    if (!cashFlowItem) throw new Error("Expected the cash-flow item to be actionable.");
    await user.click(cashFlowItem);
    expect(await screen.findByRole("dialog")).toHaveTextContent("Canapea mobilă");
  });
});
