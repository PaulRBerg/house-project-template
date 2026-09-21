import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

function unexpectedFetch(input: RequestInfo | URL): Promise<never> {
  return Promise.reject(new Error(`Unexpected fetch request: ${String(input)}`));
}

Object.defineProperty(HTMLElement.prototype, "getAnimations", {
  configurable: true,
  value(): Animation[] {
    return [];
  },
  writable: true,
});

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(unexpectedFetch));
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
