import { describe, expect, it, vi } from "vitest";

import { render, screen } from "../../test/render.js";
import { AssumptionsDialog } from "./AssumptionsDialog.js";

describe("AssumptionsDialog", () => {
  it("shows the fixed contingency without any editable field", () => {
    render(<AssumptionsDialog onClose={vi.fn()} onExited={vi.fn()} open />);

    expect(screen.getByRole("dialog", { name: "Ipoteze de calcul" })).toBeVisible();
    expect(screen.getByTestId("contingency-rate")).toHaveTextContent("10 %");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /salvează/i })).not.toBeInTheDocument();
  });

  it("closes through the dialog close request", async () => {
    const onClose = vi.fn();
    const { user } = render(<AssumptionsDialog onClose={onClose} onExited={vi.fn()} open />);

    await user.click(screen.getByRole("button", { name: /închide/i }));

    expect(onClose).toHaveBeenCalledOnce();
  });
});
