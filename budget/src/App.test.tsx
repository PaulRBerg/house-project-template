import { describe, expect, it, vi } from "vitest";

import { App } from "./App.js";
import { installApiFetch, jsonResponse, makeSnapshot } from "./test/api.js";
import { makeGroup, makeInstalment, makeItem } from "./test/builders.js";
import { makeUiDocument } from "./test/fixtures.js";
import { act, fireEvent, render, screen, waitFor, within } from "./test/render.js";

async function selectOption(
  user: ReturnType<typeof render>["user"],
  label: string,
  option: string,
) {
  await user.click(screen.getByRole("combobox", { name: label }));
  await user.click(await screen.findByRole("option", { name: option }));
}

function installFetch(document = makeUiDocument()) {
  installApiFetch(() => jsonResponse(makeSnapshot(document)));
}

describe("App interactions", () => {
  it("opens Extra as the fifth stage with its own costs while retaining the initial headline", async () => {
    const baseline = makeUiDocument();
    const extraItem = makeItem({
      id: "crib",
      label: "Pătuț copil",
      groupId: "extra-furniture",
      milestoneId: "extra",
      areaId: "U-CHILD",
      costScope: "movable",
      costType: "movable-good",
      contingencyEligible: false,
      notes: "Pătuț temporar în dormitor.",
    });
    installFetch(
      makeUiDocument({
        groups: [
          ...baseline.groups,
          makeGroup({ id: "extras", label: "Extra", milestoneId: "extra", sortOrder: 5 }),
          makeGroup({
            id: "extra-furniture",
            label: "Mobilier",
            milestoneId: "extra",
            parentId: "extras",
          }),
        ],
        items: [...baseline.items, extraItem],
        instalments: [
          ...baseline.instalments,
          makeInstalment({ id: "crib-plan", itemId: "crib", dueOn: "2031-06" }),
        ],
      }),
    );
    const onUrlUpdate = vi.fn();
    const { user } = render(<App />, { onUrlUpdate });
    const extra = await screen.findByRole("tab", { name: "Extra" });
    const overview = screen.getByRole("region", { name: "Privire de ansamblu financiară" });
    expect(overview).toHaveTextContent("€320");
    expect(extra).toHaveTextContent("€100");
    expect(extra).toHaveTextContent("Iun 2029 – Iun 2031");
    await user.click(extra);
    expect(extra).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("button", { name: "Pătuț copil" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Pe camere" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(overview).toHaveTextContent("€320");
    expect(screen.getByText(/Buget separat, exclus din/)).toBeVisible();
    await waitFor(() =>
      expect(onUrlUpdate).toHaveBeenCalledWith(
        expect.objectContaining({ queryString: "?category=extras" }),
      ),
    );
    await user.click(screen.getByRole("button", { name: "Pătuț copil" }));
    expect(await screen.findByRole("dialog", { name: "Pătuț copil" })).toHaveTextContent(
      "Pătuț temporar în dormitor.",
    );
  });

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

  it("navigates to Beneficiari from the header nav and lists the bundles", async () => {
    installFetch();
    const onUrlUpdate = vi.fn();
    const { user } = render(<App />, { onUrlUpdate });
    await screen.findByRole("tab", { name: "La roșu" });

    onUrlUpdate.mockClear();
    await user.click(screen.getByRole("button", { name: "Beneficiari" }));
    expect(await screen.findByRole("heading", { name: "Beneficiari" })).toBeVisible();
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalledOnce());
    expect(onUrlUpdate.mock.calls[0]?.[0]).toMatchObject({
      options: expect.objectContaining({ history: "push" }),
      queryString: "?page=beneficiari",
    });
    expect(screen.getByRole("button", { name: "Constructor Exemplu" })).toBeVisible();
    expect(screen.getByRole("button", { name: "TBD" })).toBeVisible();
  });

  it("opens the beneficiary detail from the budget table without opening the item drawer", async () => {
    installFetch();
    const onUrlUpdate = vi.fn();
    const { user } = render(<App />, { onUrlUpdate });
    await screen.findByRole("button", { name: "Structură" });

    onUrlUpdate.mockClear();
    await user.click(screen.getByRole("button", { name: "Beneficiar: Constructor Exemplu" }));
    expect(await screen.findByRole("heading", { name: "Constructor Exemplu" })).toBeVisible();
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalledOnce());
    expect(onUrlUpdate.mock.calls[0]?.[0]).toMatchObject({
      options: expect.objectContaining({ history: "push" }),
      queryString: "?page=beneficiari&beneficiar=constructor-exemplu",
    });
    expect(screen.getByRole("button", { name: "Structură" })).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the item drawer from beneficiary detail and returns to the beneficiaries list", async () => {
    installFetch();
    const onUrlUpdate = vi.fn();
    const { user } = render(<App />, {
      onUrlUpdate,
      searchParams: "page=beneficiari&beneficiar=constructor-exemplu",
    });

    await user.click(await screen.findByRole("button", { name: "Structură" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Structură");
    await user.click(screen.getByRole("button", { name: "Închide" }));

    onUrlUpdate.mockClear();
    await user.click(screen.getByRole("button", { name: "Toți beneficiarii" }));
    expect(await screen.findByRole("heading", { name: "Beneficiari" })).toBeVisible();
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalledOnce());
    expect(onUrlUpdate.mock.calls[0]?.[0]).toMatchObject({
      options: expect.objectContaining({ history: "push" }),
      queryString: "?page=beneficiari",
    });
  });

  it("shows the TBD beneficiary detail with the unassigned fixture items", async () => {
    installFetch();
    render(<App />, { searchParams: "page=beneficiari&beneficiar=tbd" });

    expect(await screen.findByRole("heading", { name: "TBD" })).toBeVisible();
    expect(screen.getByText("Elemente fără beneficiar stabilit încă.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Arhitectură" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Placare opțională" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Canapea mobilă" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Scaun arhivat" })).toBeVisible();
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
    expect(screen.getByText(/La mutat · .* cu dată stabilită/)).toBeVisible();
    const cashFlowItem = screen
      .getAllByText("Canapea mobilă")
      .map((element) => element.closest("button"))
      .find((element) => element !== null);
    if (!cashFlowItem) throw new Error("Expected the cash-flow item to be actionable.");
    await user.click(cashFlowItem);
    expect(await screen.findByRole("dialog")).toHaveTextContent("Canapea mobilă");
  });

  it("refreshes overdue state when the tab regains focus on a later day", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date(2027, 8, 30, 23, 0) });
    try {
      installFetch();
      render(<App />);
      const nextPayment = (await screen.findByText(/Următoarea plată:/)).closest("p");
      expect(nextPayment).not.toHaveTextContent("restantă");

      vi.setSystemTime(new Date(2027, 9, 1, 8, 0));
      act(() => {
        fireEvent.focus(window);
      });
      expect(nextPayment).toHaveTextContent("restantă");
    } finally {
      vi.useRealTimers();
    }
  });
});
