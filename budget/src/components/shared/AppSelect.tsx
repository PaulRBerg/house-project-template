import { Select } from "@base-ui/react/select";
import { Check, ChevronsUpDown } from "lucide-react";

import { cn } from "./styles.js";

export type AppSelectOption<Value extends string> = {
  value: Value;
  label: string;
};

type AppSelectProps<Value extends string> = {
  label: string;
  name: string;
  value: Value;
  options: readonly AppSelectOption<Value>[];
  onValueChange: (value: Value) => void;
  disabled?: boolean;
  className?: string;
  popupClassName?: string;
};

export function AppSelect<Value extends string>({
  label,
  name,
  value,
  options,
  onValueChange,
  disabled = false,
  className,
  popupClassName,
}: AppSelectProps<Value>) {
  return (
    <Select.Root
      disabled={disabled}
      items={options}
      name={name}
      onValueChange={(nextValue) => {
        if (nextValue !== null) onValueChange(nextValue);
      }}
      value={value}
    >
      <Select.Trigger
        aria-label={label}
        className={cn(
          "inline-flex min-h-10.5 items-center justify-between gap-2 rounded-[7px] border border-line bg-surface py-0 pr-2.5 pl-2.75 text-[0.72rem] text-ink outline-hidden data-disabled:cursor-not-allowed data-disabled:opacity-55",
          className,
        )}
      >
        <Select.Value />
        <Select.Icon className="flex-none text-muted">
          <ChevronsUpDown aria-hidden="true" size={14} strokeWidth={1.9} />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Positioner alignItemWithTrigger={false} className="z-(--z-dropdown)" sideOffset={4}>
          <Select.Popup
            className={cn(
              "min-w-(--anchor-width) origin-(--transform-origin) overflow-hidden rounded-[7px] border border-line bg-surface text-[0.72rem] text-ink shadow-panel transition-[transform,opacity] data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0 motion-reduce:transition-none",
              popupClassName,
            )}
          >
            <Select.List className="max-h-72 overflow-y-auto p-1">
              {options.map((option) => (
                <Select.Item
                  className="grid min-h-9 cursor-default grid-cols-[1rem_1fr] items-center gap-2 rounded-[5px] px-2.5 outline-hidden select-none data-disabled:opacity-55 data-highlighted:bg-line/60 data-selected:font-[680]"
                  key={option.value}
                  value={option.value}
                >
                  <Select.ItemIndicator className="text-accent">
                    <Check aria-hidden="true" size={13} strokeWidth={2.4} />
                  </Select.ItemIndicator>
                  <Select.ItemText className="col-start-2">{option.label}</Select.ItemText>
                </Select.Item>
              ))}
            </Select.List>
          </Select.Popup>
        </Select.Positioner>
      </Select.Portal>
    </Select.Root>
  );
}
