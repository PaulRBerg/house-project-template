import { useLayoutEffect, useRef } from "react";
import type { ComponentPropsWithoutRef, ReactNode, RefObject } from "react";

import { useAnimatedPresence } from "../../hooks/useAnimatedPresence.js";
import { cn, collapsibleCellStyles } from "../shared/styles.js";
import type { AnimationPhase } from "../shared/styles.js";

interface AnimatedBudgetRowProps extends Omit<ComponentPropsWithoutRef<"tr">, "children" | "ref"> {
  open: boolean;
  children: (phase: AnimationPhase, animationRef: RefObject<HTMLDivElement | null>) => ReactNode;
}

export function AnimatedBudgetRow({ children, open, ...props }: AnimatedBudgetRowProps) {
  const { phase, present, ref } = useAnimatedPresence<HTMLDivElement>(open);

  if (!present) return null;

  return (
    <tr {...props} aria-hidden={open ? undefined : true} inert={!open}>
      {children(phase, ref)}
    </tr>
  );
}

export function AnimatedCellContent({
  children,
  className,
  phase,
  ref: animationRef,
}: {
  children?: ReactNode;
  className?: string;
  phase: AnimationPhase;
  ref?: RefObject<HTMLDivElement | null>;
}) {
  const localRef = useRef<HTMLDivElement>(null);
  const ref = animationRef ?? localRef;

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element || phase === "idle") return;
    element.style.setProperty("--radix-collapsible-content-height", `${element.scrollHeight}px`);
  }, [phase, ref]);

  return (
    <div ref={ref} className={cn("overflow-hidden", collapsibleCellStyles({ phase }))}>
      <div className={cn("py-2.75", className)}>{children}</div>
    </div>
  );
}
