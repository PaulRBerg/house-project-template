import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { fireEvent, render, screen, waitFor } from "../../test/render.js";
import { Dialog } from "./Dialog.js";

type ControlledDialogProps = {
  onRequestClose?: () => void;
  onExited?: () => void;
};

function ControlledDialog({ onRequestClose = vi.fn(), onExited = vi.fn() }: ControlledDialogProps) {
  const [open, setOpen] = useState(false);
  const close = (): void => {
    onRequestClose();
    setOpen(false);
  };

  return (
    <>
      <button onClick={() => setOpen(true)} type="button">
        Declanșator
      </button>
      <button onClick={() => setOpen(false)} type="button">
        Închide controlat
      </button>
      <button type="button">Exterior</button>
      <Dialog onExited={onExited} onRequestClose={close} open={open} title="Detalii">
        <p>Conținutul panoului</p>
      </Dialog>
    </>
  );
}

function RejectingDialog({ onRequestClose }: { onRequestClose: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)} type="button">
        Deschide fără închidere
      </button>
      <Dialog onRequestClose={onRequestClose} open={open} title="Detalii păstrate">
        <p>Conținut păstrat</p>
      </Dialog>
    </>
  );
}

describe("Dialog", () => {
  it("moves focus into the drawer and closes from its accessible control", async () => {
    const onRequestClose = vi.fn();
    const { user } = render(<ControlledDialog onRequestClose={onRequestClose} />);
    const trigger = screen.getByRole("button", { name: "Declanșator" });

    await user.click(trigger);

    expect(screen.getByRole("dialog", { name: "Detalii" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Închide" })).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "Închide" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(onRequestClose).toHaveBeenCalledOnce();
    expect(trigger).toHaveFocus();
  });

  it("requests one controlled close on Escape and restores opener focus", async () => {
    const onRequestClose = vi.fn();
    const { user } = render(<ControlledDialog onRequestClose={onRequestClose} />);
    const trigger = screen.getByRole("button", { name: "Declanșator" });
    await user.click(trigger);

    await user.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(onRequestClose).toHaveBeenCalledOnce();
    expect(trigger).toHaveFocus();
  });

  it("requests one controlled close when focus and pointer move outside", async () => {
    const onRequestClose = vi.fn();
    const { user } = render(<ControlledDialog onRequestClose={onRequestClose} />);
    await user.click(screen.getByRole("button", { name: "Declanșator" }));

    await user.click(screen.getByRole("button", { name: "Exterior" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(onRequestClose).toHaveBeenCalledOnce();
  });

  it("delivers a later close request when the controlled consumer rejects the first", async () => {
    const onRequestClose = vi.fn();
    const { user } = render(<RejectingDialog onRequestClose={onRequestClose} />);
    await user.click(screen.getByRole("button", { name: "Deschide fără închidere" }));

    await user.click(screen.getByRole("button", { name: "Închide" }));

    expect(onRequestClose).toHaveBeenCalledOnce();
    expect(screen.getByRole("dialog", { name: "Detalii păstrate" })).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(onRequestClose).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("dialog", { name: "Detalii păstrate" })).toBeInTheDocument();
  });

  it("retains the drawer through its exit animation and reports completion", async () => {
    let finish: (() => void) | undefined;
    const animation = {
      finished: new Promise<Animation>((resolve) => {
        finish = () => resolve(animation as Animation);
      }),
      pending: false,
      playState: "running",
    } as Pick<Animation, "finished" | "pending" | "playState">;
    const onExited = vi.fn();
    const { user } = render(<ControlledDialog onExited={onExited} />);
    const trigger = screen.getByRole("button", { name: "Declanșator" });
    await user.click(trigger);
    await waitFor(() => expect(screen.getByRole("button", { name: "Închide" })).toHaveFocus());
    vi.spyOn(HTMLElement.prototype, "getAnimations").mockImplementation(function (
      this: HTMLElement,
    ) {
      return this.getAttribute("role") === "dialog" ? [animation as Animation] : [];
    });

    fireEvent.click(screen.getByRole("button", { name: "Închide controlat" }));

    expect(screen.getByText("Conținutul panoului")).toBeInTheDocument();
    expect(onExited).not.toHaveBeenCalled();
    finish?.();

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(onExited).toHaveBeenCalledOnce();
    expect(trigger).toHaveFocus();
  });
});
