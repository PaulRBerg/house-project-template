import { describe, expect, it, vi } from "vitest";

import { selectBudgetView } from "../../domain/index.js";
import { makeUiDocument, uiFixtureIds } from "../../test/fixtures.js";
import { fireEvent, render, screen, waitFor, within } from "../../test/render.js";
import { CashFlowView } from "./CashFlowView.js";

function flowProps() {
  const document = makeUiDocument({
    instalments: [
      {
        id: "jan",
        itemId: uiFixtureIds.items.professionalCore,
        label: "Arhitect",
        dueOn: "2027-01",
        projectedCents: 10_000,
      },
      {
        id: "apr",
        itemId: uiFixtureIds.items.constructionCore,
        label: "Structură",
        dueOn: "2027-04",
        projectedCents: 20_000,
      },
    ],
  });
  return {
    onOpenItem: vi.fn(),
    view: selectBudgetView(document, { asOf: "2026-09-19" }),
  };
}

describe("CashFlowView", () => {
  it("shows cumulative costs on hover, including empty months, without selecting the period", async () => {
    const props = flowProps();
    const { user } = render(<CashFlowView {...props} />);

    for (const [label, cumulative, periodCost] of [
      ["Feb 2027", "€110", "€0"],
      ["Apr 2027", "€330", "€220"],
    ] as const) {
      const bar = screen.getByRole("button", { name: new RegExp(`${label}: plătit`) });

      await user.hover(bar);
      const tooltip = await screen.findByRole("tooltip");
      expect(within(tooltip).getByText(label)).toBeVisible();
      expect(within(tooltip).getByText("Cumul până aici")).toBeVisible();
      expect(within(tooltip).getByText(cumulative)).toBeVisible();
      expect(within(tooltip).getByText(periodCost)).toBeVisible();
      expect(screen.getByRole("heading", { name: "Ian 2027" })).toBeVisible();

      await user.unhover(bar);
      await waitFor(() => expect(screen.queryByRole("tooltip")).not.toBeInTheDocument());
    }
  });

  it("selects monthly periods with mouse and opens the selected allocation", async () => {
    const props = flowProps();
    const { user } = render(<CashFlowView {...props} />);
    await user.click(screen.getByRole("button", { name: /Apr 2027: plătit/i }));
    expect(screen.getByRole("heading", { name: "Apr 2027" })).toBeVisible();

    const allocationButton = screen
      .getAllByText("Structură")
      .map((element) => element.closest("button"))
      .find((element) => element !== null);
    if (!allocationButton) throw new Error("Expected the selected allocation to be actionable.");
    await user.click(allocationButton);
    expect(props.onOpenItem).toHaveBeenCalledWith(uiFixtureIds.items.constructionCore);
  });

  it("switches to quarters and selects a period from the keyboard", async () => {
    const props = flowProps();
    const { user } = render(<CashFlowView {...props} />);
    await user.click(screen.getByRole("button", { name: "Trimestre" }));
    const quarter = screen.getByRole("button", { name: /T2 2027: plătit/i });
    quarter.focus();
    const tooltip = await screen.findByRole("tooltip");
    expect(within(tooltip).getByText("T2 2027")).toBeVisible();
    expect(within(tooltip).getByText("€330")).toBeVisible();
    expect(within(tooltip).getByText("€220")).toBeVisible();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("tooltip")).not.toBeInTheDocument());
    expect(quarter).toHaveFocus();
    expect(screen.getByRole("heading", { name: "T2 2027" })).toBeVisible();

    // Focus already selects T2, so activate a different bar to prove the key handler.
    fireEvent.keyDown(screen.getByRole("button", { name: /T1 2027: plătit/i }), { key: "Enter" });
    expect(screen.getByRole("heading", { name: "T1 2027" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Luni" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Trimestre" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(screen.getByRole("button", { name: "Trimestre" }));
    expect(screen.getByRole("button", { name: "Trimestre" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("expands and closes the exact monthly values", async () => {
    const { user } = render(<CashFlowView {...flowProps()} />);
    const trigger = screen.getByRole("button", { name: "Valori lunare exacte și cumul" });

    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();

    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("table")).toBeVisible();

    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await waitFor(() => expect(screen.queryByRole("table")).not.toBeInTheDocument());
  });
});
