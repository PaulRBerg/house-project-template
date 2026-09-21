import { render as rtlRender, type RenderOptions, type RenderResult } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NuqsTestingAdapter, type OnUrlUpdateFunction } from "nuqs/adapters/testing";
import type { ReactNode } from "react";

export {
  act,
  fireEvent,
  screen,
  waitFor,
  waitForElementToBeRemoved,
  within,
} from "@testing-library/react";
export { userEvent };

interface RenderOptionsWithNuqs extends Omit<RenderOptions, "wrapper"> {
  onUrlUpdate?: OnUrlUpdateFunction;
  searchParams?: string | Record<string, string> | URLSearchParams;
}

export function render(
  ui: ReactNode,
  { onUrlUpdate, searchParams, ...options }: RenderOptionsWithNuqs = {},
): RenderResult & { user: ReturnType<typeof userEvent.setup> } {
  const user = userEvent.setup();
  const adapterProps = {
    hasMemory: true,
    ...(onUrlUpdate ? { onUrlUpdate } : {}),
    ...(searchParams === undefined ? {} : { searchParams }),
  };
  const result = rtlRender(ui, {
    ...options,
    wrapper: ({ children }) => (
      <NuqsTestingAdapter {...adapterProps}>{children}</NuqsTestingAdapter>
    ),
  });

  return { ...result, user };
}
