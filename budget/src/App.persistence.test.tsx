import { describe, expect, it, vi } from "vitest";

vi.mock("./ui/export.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./ui/export.js")>();
  return { ...actual, downloadBudgetJson: vi.fn() };
});

import { App } from "./App.js";
import { makeUiDocument, uiFixtureIds } from "./test/fixtures.js";
import { fireEvent, render, screen, waitFor, within } from "./test/render.js";
import { downloadBudgetJson } from "./ui/export.js";

const revision = "a".repeat(64);
const nextRevision = "b".repeat(64);

function snapshot(document = makeUiDocument(), revisionValue = revision) {
  return { document, revision: revisionValue };
}

function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

function exchangeRateResponse(): Response {
  return jsonResponse({
    ronPerEur: 5.12,
    rateDate: "2026-09-18",
    source: "BNR",
    sourceUrl: "https://www.bnr.ro/",
    fetchedAt: "2026-09-18T12:00:00.000Z",
    stale: false,
  });
}

function installFetch(
  respondBudget: (request: RequestInit | undefined) => Response | Promise<Response>,
) {
  const request = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === "/api/exchange-rate") return Promise.resolve(exchangeRateResponse());
    if (String(input) === "/api/budget") return Promise.resolve(respondBudget(init));
    return Promise.reject(new Error(`Cerere neașteptată: ${String(input)}`));
  });
  vi.stubGlobal("fetch", request);
  return request;
}

async function openDirtyAssumptions(user: ReturnType<typeof render>["user"]) {
  await user.click(screen.getByRole("button", { name: "Ipoteze" }));
  const growth = screen.getByRole("textbox", { name: /creștere anuală/i });
  fireEvent.change(growth, { target: { value: "6.2" } });
  return growth;
}

function dispatchBeforeUnload(): BeforeUnloadEvent {
  const event = new Event("beforeunload", { cancelable: true }) as BeforeUnloadEvent;
  window.dispatchEvent(event);
  return event;
}

describe("persistența aplicației", () => {
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

  it("păstrează draftul după o salvare eșuată, îl retrimite și elimină avertismentul de ieșire", async () => {
    const draft = makeUiDocument({
      project: { ...makeUiDocument().project, annualGrowthBps: 620 },
    });
    let saves = 0;
    const request = installFetch((init) => {
      if (init?.method !== "PUT") return jsonResponse(snapshot());
      saves += 1;
      return saves === 1
        ? jsonResponse({ error: { code: "WRITE_FAILED", message: "Discul este plin." } }, 500)
        : jsonResponse(snapshot(draft, nextRevision));
    });
    const { user } = render(<App />);

    await screen.findByRole("button", { name: "Ipoteze" });
    await openDirtyAssumptions(user);
    await user.click(screen.getByRole("button", { name: "Salvează ipotezele" }));

    expect(await screen.findByText("Discul este plin.")).toBeInTheDocument();
    expect(screen.getByText(/Ipotezele rămân în editor/i)).toBeInTheDocument();
    expect(dispatchBeforeUnload().defaultPrevented).toBe(true);
    await user.click(screen.getByRole("button", { name: "Reîncearcă salvarea" }));

    await waitFor(() =>
      expect(screen.queryByText("Modificarea nu a fost scrisă pe disc.")).not.toBeInTheDocument(),
    );
    expect(dispatchBeforeUnload().defaultPrevented).toBe(false);
    const writes = request.mock.calls.filter(([, init]) => init?.method === "PUT");
    expect(writes).toHaveLength(2);
    expect(JSON.parse(String(writes[0]?.[1]?.body))).toEqual({
      expectedRevision: revision,
      document: draft,
    });
    expect(JSON.parse(String(writes[1]?.[1]?.body))).toEqual({
      expectedRevision: revision,
      document: draft,
    });
  });

  it("păstrează draftul la conflict, îl descarcă și acceptă instantaneul nou numai după confirmare", async () => {
    const draft = makeUiDocument({
      project: { ...makeUiDocument().project, annualGrowthBps: 620 },
    });
    const latest = makeUiDocument({
      items: makeUiDocument().items.map((item) =>
        item.id === uiFixtureIds.items.professionalCore
          ? { ...item, label: "Arhitectură actualizată" }
          : item,
      ),
    });
    const request = installFetch((init) => {
      if (init?.method !== "PUT") return jsonResponse(snapshot());
      return jsonResponse(
        {
          error: { code: "REVISION_CONFLICT", message: "Altă sesiune a salvat deja." },
          latest: snapshot(latest, nextRevision),
        },
        409,
      );
    });
    const { user } = render(<App />);

    await screen.findByRole("button", { name: "Ipoteze" });
    await openDirtyAssumptions(user);
    await user.click(screen.getByRole("button", { name: "Salvează ipotezele" }));

    expect(
      await screen.findByText("Bugetul a fost modificat de altă sesiune."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Renunță" }));
    await user.click(screen.getByRole("button", { name: "Renunță la modificări" }));
    await user.click(screen.getByRole("button", { name: "Descarcă draftul" }));
    expect(downloadBudgetJson).toHaveBeenCalledOnce();
    expect(downloadBudgetJson).toHaveBeenCalledWith(draft, "buget-draft-nesalvat.json");
    const loadLatest = screen.getByRole("button", { name: "Încarcă versiunea de pe disc" });
    await user.click(loadLatest);
    const confirmation = await screen.findByRole("alertdialog", {
      name: "Încarci versiunea de pe disc?",
    });
    expect(confirmation).toBeVisible();
    await user.click(within(confirmation).getByRole("button", { name: "Păstrează draftul" }));
    expect(screen.getByText("Bugetul a fost modificat de altă sesiune.")).toBeInTheDocument();
    expect(document.activeElement).toBe(loadLatest);

    await user.click(loadLatest);
    await user.click(
      within(
        await screen.findByRole("alertdialog", { name: "Încarci versiunea de pe disc?" }),
      ).getByRole("button", { name: "Încarcă versiunea de pe disc" }),
    );
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Arhitectură actualizată" })).toBeInTheDocument();
    expect(request.mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(1);
  });
});
