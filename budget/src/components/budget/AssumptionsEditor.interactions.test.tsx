import { describe, expect, it, vi } from "vitest";

import { makeUiDocument } from "../../test/fixtures.js";
import { fireEvent, render, screen, waitFor } from "../../test/render.js";
import { AssumptionsEditor } from "./AssumptionsEditor.js";

function editorProps(overrides: Partial<React.ComponentProps<typeof AssumptionsEditor>> = {}) {
  return {
    busy: false,
    document: makeUiDocument(),
    onClose: vi.fn(),
    onDirtyChange: vi.fn(),
    onExited: vi.fn(),
    onSave: vi.fn().mockResolvedValue(true),
    open: true,
    ...overrides,
  };
}

describe("AssumptionsEditor", () => {
  it.each([
    { annualGrowthBps: 510, contingencyBps: 0 },
    { annualGrowthBps: 0, contingencyBps: 710 },
  ])(
    "keeps save disabled for stored fractional percentages",
    ({ annualGrowthBps, contingencyBps }) => {
      const document = makeUiDocument({
        project: { ...makeUiDocument().project, annualGrowthBps, contingencyBps },
      });
      render(<AssumptionsEditor {...editorProps({ document })} />);

      expect(screen.getByRole("button", { name: "Salvează ipotezele" })).toBeDisabled();
    },
  );

  it("keeps save disabled until an assumption is changed and converts percent values to bps", async () => {
    const props = editorProps();
    const { user } = render(<AssumptionsEditor {...props} />);
    const save = screen.getByRole("button", { name: "Salvează ipotezele" });

    expect(save).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox", { name: /Creștere anuală/i }), {
      target: { value: "2.5" },
    });
    await user.click(save);

    await waitFor(() => expect(props.onSave).toHaveBeenCalledOnce());
    expect(props.onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        project: expect.objectContaining({ annualGrowthBps: 250 }),
      }),
    );
    expect(props.onClose).toHaveBeenCalledOnce();
  });

  it("rejects empty and out-of-range values without saving", async () => {
    const props = editorProps();
    const { user } = render(<AssumptionsEditor {...props} />);
    const growth = screen.getByRole("textbox", { name: /Creștere anuală/i });
    await user.clear(growth);
    await user.click(screen.getByRole("button", { name: "Salvează ipotezele" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("0–25%");
    expect(props.onSave).not.toHaveBeenCalled();

    await user.type(growth, "26");
    await user.click(screen.getByRole("button", { name: "Salvează ipotezele" }));
    expect(props.onSave).not.toHaveBeenCalled();
  });

  it("prevents save while busy and retains the draft when saving fails", async () => {
    const busy = editorProps({ busy: true });
    const busyView = render(<AssumptionsEditor {...busy} />);
    expect(screen.getByRole("button", { name: "Se salvează…" })).toBeDisabled();
    expect(busy.onSave).not.toHaveBeenCalled();
    busyView.unmount();

    const props = editorProps({ onSave: vi.fn().mockResolvedValue(false) });
    const { user } = render(<AssumptionsEditor {...props} />);
    fireEvent.change(screen.getByRole("textbox", { name: /Rezervă de risc/i }), {
      target: { value: "12" },
    });
    await user.click(screen.getByRole("button", { name: "Salvează ipotezele" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Salvarea locală a eșuat");
    expect(props.onClose).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: /Rezervă de risc/i })).toHaveValue("12");
  });

  it("asks before discarding a dirty draft and supports cancel, confirm, and retry", async () => {
    const props = editorProps();
    const { user } = render(<AssumptionsEditor {...props} />);
    fireEvent.change(screen.getByRole("textbox", { name: /Creștere anuală/i }), {
      target: { value: "3" },
    });

    await user.click(screen.getByRole("button", { name: "Renunță" }));
    expect(
      await screen.findByRole("alertdialog", { name: "Renunți la modificările nesalvate?" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Păstrează modificările" }));
    expect(props.onClose).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog", { name: "Ipoteze de calcul" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Renunță" }));
    await user.click(screen.getByRole("button", { name: "Renunță la modificări" }));
    expect(props.onClose).toHaveBeenCalledOnce();
  });
});
