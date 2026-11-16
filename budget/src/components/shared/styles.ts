import { tv } from "tailwind-variants";

export { twMerge as cn } from "tailwind-merge";

export const buttonVariants = tv({
  base: "inline-flex min-h-10.5 items-center justify-center gap-1.75 rounded-lg border border-line px-3.5 py-0 text-[0.76rem] font-[720]",
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

export const moneyCellStyles =
  "[&_small]:mt-0.75 [&_small]:flex [&_small]:gap-1 [&_small]:text-[0.66rem] [&_small]:text-muted [&_strong]:block [&_strong]:text-[0.78rem] [&_strong]:font-bold [&_strong]:whitespace-nowrap [&_strong]:tabular-nums";

export const iconButtonStyles =
  "inline-flex min-h-9 min-w-9 items-center justify-center rounded-[5px] border-0 bg-transparent p-0 hover:bg-line/60";

export const eyebrowStyles =
  "mb-2 text-[0.68rem] font-[780] tracking-[0.14em] text-olive uppercase";

export const iconLabelStyles =
  "inline-flex items-center gap-2 [&>svg]:flex-none [&>svg:not([data-stage])]:text-accent";

export const segmentedGroupStyles =
  "inline-flex flex-none rounded-full border border-line bg-plan-control p-0.75 [&_button[aria-pressed=true]]:bg-ink [&_button[aria-pressed=true]]:text-surface";

export const segmentedToggleStyles =
  "min-h-8.5 cursor-pointer rounded-full border-0 bg-transparent px-3.5 py-0 text-[0.72rem] font-[750] text-muted hover:text-ink focus-visible:outline-offset-3 focus-visible:outline-accent";

export const tableCellStyles = "px-3.5 text-left align-middle select-text";

export const tableHeaderStyles =
  "sticky top-0 z-(--z-sticky) bg-table-head px-3.5 py-3 text-left text-[0.65rem] font-[760] tracking-[0.08em] text-muted uppercase";

export const pageHeadingStyles =
  "text-[clamp(1.55rem,2vw,2.25rem)]/none font-[650] tracking-[-0.04em]";

export const emptyStateStyles = "px-5 py-13 text-center text-muted";

export const emptyStatePanelStyles = `rounded-xl border border-line bg-surface ${emptyStateStyles}`;

/** Keyboard-focusable horizontal scroller around a data table. */
export const tableScrollerStyles =
  "max-w-full overflow-auto rounded-xl border border-line bg-surface focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus";

export const linkButtonStyles =
  "cursor-pointer border-0 bg-transparent p-0 text-left hover:underline hover:underline-offset-3";

export const definitionListStyles = "grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 [&_dt]:text-muted";

export const accentLinkStyles =
  "inline-flex gap-1.5 font-bold text-accent underline-offset-3 hover:underline";

/** Budget table column widths; room headers mirror them so subtotals align with the table. */
export const BUDGET_TABLE_COLUMNS = {
  beneficiary: "w-[15%]",
  cost: "w-[16%]",
  payments: "w-[20%]",
  schedule: "w-[18%]",
  areaGrid: "grid-cols-[minmax(0,1fr)_15%_16%_20%_18%]",
} as const;
