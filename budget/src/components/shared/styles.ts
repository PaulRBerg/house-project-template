import { tv } from "tailwind-variants";

export { twMerge as cn } from "tailwind-merge";

export const buttonStyles =
  "inline-flex min-h-10.5 items-center justify-center gap-1.75 rounded-lg border border-line px-3.5 py-0 text-[0.76rem] font-[720]";

export const buttonVariants = tv({
  base: buttonStyles,
  variants: {
    intent: {
      primary: "border-ink bg-ink text-surface hover:bg-primary-hover",
      secondary: "bg-surface hover:border-olive",
    },
  },
  defaultVariants: {
    intent: "secondary",
  },
});

export type AnimationPhase = "enter" | "idle" | "exit";

export const viewMotionStyles = tv({
  base: "fill-mode-forwards motion-reduce:animate-none",
  variants: {
    phase: {
      enter: "animate-in animation-duration-200 fade-in slide-in-from-top-1",
      idle: "",
      exit: "animate-out animation-duration-150 fade-out",
    },
  },
});

export const collapsibleCellStyles = tv({
  base: "fill-mode-forwards motion-reduce:animate-none",
  variants: {
    phase: {
      enter: "animate-collapsible-down animation-duration-200",
      idle: "",
      exit: "animate-collapsible-up animation-duration-200",
    },
  },
});

export const fieldStyles =
  "flex min-w-0 flex-col items-stretch gap-1.5 text-[0.72rem] font-[680] [&_:is(input,select,textarea)]:min-h-11 [&_:is(input,select,textarea)]:w-full [&_:is(input,select,textarea)]:rounded-[7px] [&_:is(input,select,textarea)]:border [&_:is(input,select,textarea)]:border-line [&_:is(input,select,textarea)]:bg-surface [&_:is(input,select,textarea)]:px-2.75 [&_:is(input,select,textarea)]:py-2.25 [&_:is(input,select,textarea)]:text-[0.82rem] [&_:is(input,select,textarea)]:font-medium [&_input]:cursor-text [&_select]:cursor-pointer [&_small]:text-[0.64rem] [&_small]:font-medium [&_small]:text-muted [&_textarea]:cursor-text [&_textarea]:resize-y";

export const moneyCellStyles =
  "[&_small]:mt-0.75 [&_small]:flex [&_small]:gap-1 [&_small]:text-[0.66rem] [&_small]:text-muted [&_strong]:block [&_strong]:text-[0.78rem] [&_strong]:font-bold [&_strong]:whitespace-nowrap [&_strong]:tabular-nums";

export const iconButtonStyles =
  "inline-flex min-h-9 min-w-9 items-center justify-center rounded-[5px] border-0 bg-transparent p-0 hover:bg-line/60";

export const eyebrowStyles =
  "mb-2 text-[0.68rem] font-[780] tracking-[0.14em] text-olive uppercase";

export const iconLabelStyles =
  "inline-flex items-center gap-2 [&>svg]:flex-none [&>svg:not([data-stage])]:text-accent";

export const editorHeadingStyles =
  "mb-4.5 flex items-start justify-between [&_h3]:text-[0.95rem] [&_h3]:font-[740] [&_p]:mt-0.75 [&_p]:text-[0.7rem] [&_p]:text-muted";

export const editorFormStyles = "flex min-h-0 flex-1 flex-col";

export const editorFieldsetStyles = "m-0 flex min-h-0 min-w-0 flex-1 flex-col border-0 p-0";

export const editorActionsStyles =
  "sticky bottom-0 flex flex-none items-center justify-end gap-2 border-t border-line bg-editor-actions px-6 py-3.5";

export const moneyInputStyles =
  "relative flex items-center [&_b]:absolute [&_b]:right-2.75 [&_b]:text-[0.64rem] [&_b]:text-muted [&_input]:pr-12! [&_input]:tabular-nums";

export const segmentedGroupStyles =
  "inline-flex flex-none rounded-full border border-line bg-plan-control p-0.75 [&_button[aria-pressed=true]]:bg-ink [&_button[aria-pressed=true]]:text-surface";

export const segmentedToggleStyles =
  "min-h-8.5 cursor-pointer rounded-full border-0 bg-transparent px-3.5 py-0 text-[0.72rem] font-[750] text-muted hover:text-ink focus-visible:outline-offset-3 focus-visible:outline-accent";
