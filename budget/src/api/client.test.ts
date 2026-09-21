import { describe, expect, it, vi } from "vitest";

import { makeDocument } from "../domain/test-fixtures.js";
import { BudgetApiError, BudgetConflictError, loadBudget, saveBudget } from "./client.js";

const revision = "a".repeat(64);
const nextRevision = "b".repeat(64);

function snapshot(revisionValue = revision, name = "Demo House") {
  return {
    document: makeDocument({
      project: { ...makeDocument().project, name },
    }),
    revision: revisionValue,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, { status });
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

  it("trimite documentul și revizia așteptată prin contractul PUT", async () => {
    const document = makeDocument();
    const request = fetcher(jsonResponse(snapshot(nextRevision)));

    await expect(saveBudget(revision, document, request)).resolves.toEqual(snapshot(nextRevision));
    expect(request).toHaveBeenCalledWith("/api/budget", {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ expectedRevision: revision, document }),
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

  it("păstrează erorile API care nu sunt conflicte", async () => {
    const request = fetcher(
      jsonResponse(
        { error: { code: "WRITE_FAILED", message: "Discul nu poate fi scris.", details: ["EIO"] } },
        500,
      ),
    );

    await expect(saveBudget(revision, makeDocument(), request)).rejects.toMatchObject({
      status: 500,
      code: "WRITE_FAILED",
      details: ["EIO"],
    } satisfies Partial<BudgetApiError>);
  });

  it("decodează ultimul instantaneu dintr-un conflict de revizie", async () => {
    const latest = snapshot(nextRevision, "Versiunea de pe disc");
    const request = fetcher(
      jsonResponse(
        {
          error: { code: "REVISION_CONFLICT", message: "Documentul s-a schimbat." },
          latest,
        },
        409,
      ),
    );

    await expect(saveBudget(revision, makeDocument(), request)).rejects.toMatchObject({
      name: BudgetConflictError.name,
      latest,
    });
  });

  it("lasă vizibile eșecurile de transport", async () => {
    const request = vi.fn<typeof fetch>().mockRejectedValue(new TypeError("network down"));

    await expect(loadBudget(request)).rejects.toThrow("network down");
  });
});
