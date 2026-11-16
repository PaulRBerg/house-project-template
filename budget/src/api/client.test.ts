import { describe, expect, it, vi } from "vitest";

import { jsonResponse, makeSnapshot, TEST_REVISION as revision } from "../test/api.js";
import { makeDocument } from "../test/builders.js";
import { BudgetApiError, loadBudget } from "./client.js";

function snapshot() {
  return makeSnapshot(makeDocument());
}

function fetcher(response: Response): typeof fetch {
  return vi.fn<typeof fetch>().mockResolvedValue(response);
}

describe("clientul API pentru buget", () => {
  it("citește instantaneul prin contractul GET", async () => {
    const request = fetcher(jsonResponse(snapshot()));

    await expect(loadBudget(request)).resolves.toEqual(snapshot());
    expect(request).toHaveBeenCalledWith("/api/budget", {
      headers: { Accept: "application/json" },
    });
  });

  it("raportează corpuri JSON malformate", async () => {
    const request = fetcher(new Response("nu este json", { status: 200 }));

    await expect(loadBudget(request)).rejects.toMatchObject({
      code: "INVALID_RESPONSE",
      message: "Serverul a răspuns cu un corp care nu este JSON valid.",
    });
  });

  it("respinge un instantaneu de succes care nu respectă schema", async () => {
    const request = fetcher(jsonResponse({ document: {}, revision }));

    await expect(loadBudget(request)).rejects.toMatchObject({
      code: "INVALID_RESPONSE",
      message: "Serverul a returnat un document de buget invalid.",
    });
  });

  it("respinge un corp de eroare care nu respectă schema", async () => {
    const request = fetcher(jsonResponse({ message: "Lipsește contractul" }, 500));

    await expect(loadBudget(request)).rejects.toMatchObject({
      status: 500,
      code: "INVALID_RESPONSE",
    });
  });

  it("păstrează codul, mesajul și detaliile erorilor API", async () => {
    const request = fetcher(
      jsonResponse(
        {
          error: {
            code: "DATA_FILE_IO_ERROR",
            message: "Discul nu poate fi citit.",
            details: ["EIO"],
          },
        },
        500,
      ),
    );

    await expect(loadBudget(request)).rejects.toMatchObject({
      status: 500,
      code: "DATA_FILE_IO_ERROR",
      details: ["EIO"],
    } satisfies Partial<BudgetApiError>);
  });

  it("lasă vizibile eșecurile de transport", async () => {
    const request = vi.fn<typeof fetch>().mockRejectedValue(new TypeError("network down"));

    await expect(loadBudget(request)).rejects.toThrow("network down");
  });
});
