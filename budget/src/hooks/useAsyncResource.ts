import { useCallback, useEffect, useRef, useState } from "react";

export type LoadStatus = "loading" | "ready" | "error";

interface ResourceState<T> {
  status: LoadStatus;
  value?: T;
  error?: unknown;
}

/**
 * Loads a resource on mount and on `reload`, applying only the latest request's result so a
 * superseded or unmounted load never overwrites newer state. `load` must be a stable function.
 */
export function useAsyncResource<T>(load: () => Promise<T>) {
  const [state, setState] = useState<ResourceState<T>>({ status: "loading" });
  const latestRequest = useRef(0);

  const settle = useCallback(
    (request: number) =>
      load().then(
        (value) => {
          if (request === latestRequest.current) setState({ status: "ready", value });
        },
        (error: unknown) => {
          if (request === latestRequest.current) {
            setState((current) => ({ ...current, status: "error", error }));
          }
        },
      ),
    [load],
  );

  useEffect(() => {
    latestRequest.current += 1;
    void settle(latestRequest.current);
    return () => {
      latestRequest.current += 1;
    };
  }, [settle]);

  const reload = useCallback(async () => {
    latestRequest.current += 1;
    const request = latestRequest.current;
    setState(({ value }) =>
      value === undefined ? { status: "loading" } : { status: "loading", value },
    );
    await settle(request);
  }, [settle]);

  return { ...state, reload };
}
