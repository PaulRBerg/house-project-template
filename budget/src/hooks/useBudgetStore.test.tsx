import { act, renderHook, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";

import { makeUiDocument } from "../test/fixtures.js";
import { useBudgetStore } from "./useBudgetStore.js";

const revision = "a".repeat(64);
const nextRevision = "b".repeat(64);

function snapshot(document = makeUiDocument(), revisionValue = revision) {
  return { document, revision: revisionValue };
}

function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

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

describe("useBudgetStore", () => {
  it("previne salvările duplicate până când scrierea curentă se termină", async () => {
    const document = makeUiDocument();
    const save = deferred<Response>();
    const request = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === "/api/budget") {
        return request.mock.calls.filter(([url]) => String(url) === "/api/budget").length === 1
          ? Promise.resolve(jsonResponse(snapshot(document)))
          : save.promise;
      }
      return Promise.reject(new Error(`Cerere neașteptată: ${String(input)}`));
    });
    vi.stubGlobal("fetch", request);
    const { result } = renderHook(() => useBudgetStore());

    await waitFor(() => expect(result.current.loadState).toBe("ready"));
    let first: Promise<boolean> | undefined;
    let duplicate: Promise<boolean> | undefined;
    act(() => {
      first = result.current.persist(document);
      duplicate = result.current.persist(document);
    });

    await expect(duplicate).resolves.toBe(false);
    expect(result.current.saveState).toBe("saving");
    expect(request).toHaveBeenCalledTimes(2);

    save.resolve(jsonResponse(snapshot(document, nextRevision)));
    await expect(first).resolves.toBe(true);
    await waitFor(() => expect(result.current.saveState).toBe("saved"));
    expect(result.current.snapshot?.revision).toBe(nextRevision);
  });

  it("reține un document invalid fără a iniția o cerere de scriere", async () => {
    const request = vi.fn(() => Promise.resolve(jsonResponse(snapshot())));
    vi.stubGlobal("fetch", request);
    const { result } = renderHook(() => useBudgetStore());

    await waitFor(() => expect(result.current.loadState).toBe("ready"));
    const document = makeUiDocument();
    const invalid = {
      ...document,
      project: { ...document.project, annualGrowthBps: -1 },
    };

    await act(async () => expect(await result.current.persist(invalid)).toBe(false));

    expect(result.current.saveState).toBe("error");
    expect(result.current.unsavedDocument).toEqual(invalid);
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("ignoră încărcarea veche după reluarea efectului StrictMode", async () => {
    const stale = deferred<Response>();
    const current = snapshot(makeUiDocument(), nextRevision);
    let loads = 0;
    const request = vi.fn(() => {
      loads += 1;
      return loads === 1 ? stale.promise : Promise.resolve(jsonResponse(current));
    });
    vi.stubGlobal("fetch", request);
    const { result } = renderHook(() => useBudgetStore(), { wrapper: StrictMode });

    await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.snapshot).toEqual(current));
    await act(async () => {
      stale.resolve(jsonResponse(snapshot()));
      await stale.promise;
    });

    expect(result.current.snapshot).toEqual(current);
  });
});
