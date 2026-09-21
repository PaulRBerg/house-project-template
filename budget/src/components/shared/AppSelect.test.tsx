import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { render, screen } from "../../test/render.js";
import { AppSelect } from "./AppSelect.js";

const options = [
  { value: "all", label: "Casă + bunuri" },
  { value: "core", label: "Buget de bază" },
  { value: "movable", label: "Bunuri mobile" },
] as const;

type OptionValue = (typeof options)[number]["value"];

function ControlledSelect({
  onValueChange = vi.fn(),
}: {
  onValueChange?: (value: OptionValue) => void;
}) {
  const [value, setValue] = useState<OptionValue>("all");
  return (
    <AppSelect
      label="Tip de cost"
      name="budget-scope"
      onValueChange={(nextValue) => {
        onValueChange(nextValue);
        setValue(nextValue);
      }}
      options={options}
      value={value}
    />
  );
}

describe("AppSelect", () => {
  it("exposes select roles and updates the controlled value", async () => {
    const onValueChange = vi.fn();
    const { user } = render(<ControlledSelect onValueChange={onValueChange} />);
    const trigger = screen.getByRole("combobox", { name: "Tip de cost" });
    expect(trigger).toHaveTextContent("Casă + bunuri");

    await user.click(trigger);

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    const option = screen.getByRole("option", { name: "Bunuri mobile" });
    expect(option).toHaveAttribute("aria-selected", "false");
    await user.click(option);

    expect(onValueChange).toHaveBeenCalledWith("movable");
    expect(trigger).toHaveTextContent("Bunuri mobile");
  });

  it("opens and selects an option using only the keyboard", async () => {
    const onValueChange = vi.fn();
    const { user } = render(<ControlledSelect onValueChange={onValueChange} />);
    const trigger = screen.getByRole("combobox", { name: "Tip de cost" });
    trigger.focus();

    await user.keyboard("{ArrowDown}");

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.getAllByRole("option")).toHaveLength(options.length);
    await user.keyboard("bunuri{Enter}");

    expect(onValueChange).toHaveBeenCalledWith("movable");
    expect(trigger).toHaveTextContent("Bunuri mobile");
  });
});
