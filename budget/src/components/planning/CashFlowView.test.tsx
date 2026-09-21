import { describe, expect, it, vi } from "vitest";

import { selectBudgetView } from "../../domain/index.js";
import { makeUiDocument, uiFixtureIds } from "../../test/fixtures.js";
import { render, screen, waitFor } from "../../test/render.js";
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
    document,
    onOpenItem: vi.fn(),
    view: selectBudgetView(document, { asOf: "2026-09-19", scenario: "base" }),
  };
}

describe("CashFlowView", () => {
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
    await user.keyboard("{Enter}");

    expect(screen.getByRole("heading", { name: "T2 2027" })).toBeVisible();
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
