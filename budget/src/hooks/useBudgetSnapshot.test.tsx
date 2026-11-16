import { act, renderHook, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";

import { jsonResponse, makeSnapshot as snapshot } from "../test/api.js";
import { makeUiDocument } from "../test/fixtures.js";
import { useBudgetSnapshot } from "./useBudgetSnapshot.js";

function deferred<T>() {
  let complete: ((value: T) => void) | undefined;
  const promise = new Promise<T>((resolve) => {
    complete = resolve;
  });
  return {
    promise,
    resolve(value: T): void {
      complete?.(value);
    },
  };
}

describe("useBudgetSnapshot", () => {
  it("ignoră încărcarea veche după reluarea efectului StrictMode", async () => {
    const stale = deferred<Response>();
    const base = makeUiDocument();
    const current = snapshot({
      ...base,
      project: { ...base.project, location: "Locație curentă" },
    });
    let loads = 0;
    const request = vi.fn(() => {
      loads += 1;
      return loads === 1 ? stale.promise : Promise.resolve(jsonResponse(current));
    });
    vi.stubGlobal("fetch", request);
    const { result } = renderHook(() => useBudgetSnapshot(), { wrapper: StrictMode });

    await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.document).toEqual(current.document));
    await act(async () => {
      stale.resolve(jsonResponse(snapshot()));
      await stale.promise;
    });

    expect(result.current.document).toEqual(current.document);
  });
});
