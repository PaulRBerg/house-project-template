import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { render, screen, waitFor } from "../../test/render.js";
import { ConfirmDialog } from "./ConfirmDialog.js";

function ControlledConfirmDialog({ onConfirm = vi.fn() }: { onConfirm?: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)} type="button">
        Șterge elementul
      </button>
      <ConfirmDialog
        cancelLabel="Renunță"
        confirmLabel="Șterge"
        description="Această acțiune nu poate fi anulată."
        intent="destructive"
        onConfirm={onConfirm}
        onOpenChange={setOpen}
        open={open}
        title="Confirmă ștergerea"
      />
    </>
  );
}

describe("ConfirmDialog", () => {
  it("focuses the safe action, cancels, and restores opener focus", async () => {
    const { user } = render(<ControlledConfirmDialog />);
    const trigger = screen.getByRole("button", { name: "Șterge elementul" });
    await user.click(trigger);

    expect(screen.getByRole("alertdialog", { name: "Confirmă ștergerea" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Renunță" })).toHaveFocus());
    await user.click(screen.getByRole("button", { name: "Renunță" }));

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("closes on Escape and restores opener focus", async () => {
    const { user } = render(<ControlledConfirmDialog />);
    const trigger = screen.getByRole("button", { name: "Șterge elementul" });
    await user.click(trigger);

    await user.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("confirms once and closes the alert dialog", async () => {
    const onConfirm = vi.fn();
    const { user } = render(<ControlledConfirmDialog onConfirm={onConfirm} />);
    await user.click(screen.getByRole("button", { name: "Șterge elementul" }));

    await user.dblClick(screen.getByRole("button", { name: "Șterge" }));

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
