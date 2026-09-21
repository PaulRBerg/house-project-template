import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

import { useAnimatedPresence } from "../../hooks/useAnimatedPresence.js";
import { cn, viewMotionStyles } from "./styles.js";

interface AnimatedViewProps<T> {
  value: T;
  children: (value: T) => ReactNode;
}

export function AnimatedView<T>({ value, children }: AnimatedViewProps<T>) {
  const [displayed, setDisplayed] = useState(value);
  const desiredRef = useRef(value);
  const shouldShowDisplayed = Object.is(value, displayed);
  const { ref, present, phase } = useAnimatedPresence<HTMLDivElement>(shouldShowDisplayed, {
    onExited: () => setDisplayed(desiredRef.current),
  });

  useLayoutEffect(() => {
    desiredRef.current = value;
  }, [value]);

  return (
    <div
      className={cn(
        viewMotionStyles({ phase }),
        (!present || phase === "exit") && "pointer-events-none",
        !present && "invisible",
      )}
      inert={!present || phase === "exit" || undefined}
      ref={ref}
    >
      {children(displayed)}
    </div>
  );
}
