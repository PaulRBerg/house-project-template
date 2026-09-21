import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { RefObject } from "react";

import type { AnimationPhase } from "../components/shared/styles.js";

type AnimatedPresenceOptions = {
  appear?: boolean;
  onExited?: () => void;
};

type AnimatedPresence<T extends HTMLElement> = {
  ref: RefObject<T | null>;
  present: boolean;
  phase: AnimationPhase;
};

type PresenceState = {
  present: boolean;
  phase: AnimationPhase;
};

export function useAnimatedPresence<T extends HTMLElement>(
  open: boolean,
  options: AnimatedPresenceOptions = {},
): AnimatedPresence<T> {
  const { appear = false, onExited } = options;
  const ref = useRef<T>(null);
  const desiredOpenRef = useRef(open);
  const previousOpenRef = useRef(open);
  const onExitedRef = useRef(onExited);
  const [state, setState] = useState<PresenceState>(() => ({
    present: open,
    phase: open && appear ? "enter" : "idle",
  }));

  useLayoutEffect(() => {
    desiredOpenRef.current = open;
    onExitedRef.current = onExited;
  }, [onExited, open]);

  useEffect(() => {
    if (open === previousOpenRef.current) return;

    previousOpenRef.current = open;
    setState((current) => {
      if (open) return { present: true, phase: "enter" };
      if (!current.present) return current;
      return { present: true, phase: "exit" };
    });
  }, [open]);

  useEffect(() => {
    if (!state.present || state.phase === "idle") return;

    let cancelled = false;
    const animations = ref.current?.getAnimations() ?? [];

    void Promise.allSettled(animations.map((animation) => animation.finished)).then(() => {
      if (cancelled) return;

      if (state.phase === "enter") {
        if (desiredOpenRef.current) setState({ present: true, phase: "idle" });
        return;
      }

      if (!desiredOpenRef.current) {
        setState({ present: false, phase: "idle" });
        onExitedRef.current?.();
      }
    });

    return () => {
      cancelled = true;
    };
  }, [state.phase, state.present]);

  return { ref, present: state.present, phase: state.phase };
}
