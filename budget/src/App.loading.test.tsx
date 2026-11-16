import { describe, expect, it } from "vitest";

import { App } from "./App.js";
import {
  installApiFetch as installFetch,
  jsonResponse,
  makeSnapshot as snapshot,
} from "./test/api.js";
import { render, screen, waitFor } from "./test/render.js";

describe("încărcarea aplicației", () => {
  it("arată eroarea de încărcare și reîncarcă documentul", async () => {
    let loads = 0;
    const request = installFetch(() => {
      loads += 1;
      return loads === 1
        ? jsonResponse({ error: { code: "READ_FAILED", message: "Fișier indisponibil." } }, 500)
        : jsonResponse(snapshot());
    });
    const { user } = render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Fișier indisponibil.");
    await user.click(screen.getByRole("button", { name: "Reîncearcă" }));

    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(request.mock.calls.filter(([url]) => String(url) === "/api/budget")).toHaveLength(2);
  });
});
