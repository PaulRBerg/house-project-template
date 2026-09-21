import { describe, expect, it } from "vitest";

import { selectBudgetView } from "../domain/selectors.js";
import {
  makeDocument,
  makeGroup,
  makeInstalment,
  makeItem,
  makePayment,
} from "../domain/test-fixtures.js";
import {
  isGroupEffectivelyArchived,
  reconcileItemCompletion,
  setGroupArchived,
  updateGroupPlacement,
} from "./document-actions.js";

function complete(document: ReturnType<typeof makeDocument>, completedOn = "2027-03-15") {
  return {
    ...document,
    items: document.items.map((item) => ({
      ...item,
      completion: { complete: true as const, completedOn },
    })),
  };
}

describe("operații de editare a documentului", () => {
  it("mută un arbore întreg în alt jalon și păstrează elementele sincronizate", () => {
    const document = makeDocument({
      groups: [makeGroup({ id: "root" }), makeGroup({ id: "child", parentId: "root" })],
      items: [makeItem({ groupId: "child" })],
    });
    const root = document.groups[0];
    if (!root) throw new Error("Fixture fără grup");
    const moved = updateGroupPlacement(document, root.id, null, "la-cheie");
    const groupIds = new Set([
      root.id,
      ...moved.groups.filter((group) => group.parentId === root.id).map((group) => group.id),
    ]);
    expect(
      moved.groups
        .filter((group) => groupIds.has(group.id))
        .every((group) => group.milestoneId === "la-cheie"),
    ).toBe(true);
    expect(
      moved.items
        .filter((item) => groupIds.has(item.groupId))
        .every((item) => item.milestoneId === "la-cheie"),
    ).toBe(true);
  });

  it("respinge mutarea unei categorii sub un descendent", () => {
    const document = makeDocument({
      groups: [makeGroup({ id: "root" }), makeGroup({ id: "child", parentId: "root" })],
      items: [makeItem({ groupId: "child" })],
    });
    const parent = document.groups.find((group) =>
      document.groups.some((candidate) => candidate.parentId === group.id),
    );
    const child = document.groups.find((group) => group.parentId === parent?.id);
    if (!parent || !child) throw new Error("Fixture fără ierarhie");
    expect(() => updateGroupPlacement(document, parent.id, child.id, parent.milestoneId)).toThrow(
      /subgrupurile/,
    );
  });

  it("arhivează fără să atingă istoricul plăților", () => {
    const document = makeDocument({ payments: [makePayment()] });
    const group = document.groups[0];
    if (!group) throw new Error("Fixture fără grup");
    const payments = structuredClone(document.payments);
    const archived = setGroupArchived(document, group.id, true);
    expect(archived.payments).toEqual(payments);
  });

  it("tratează descendenții unei categorii arhivate ca ținte arhivate", () => {
    const document = makeDocument({
      groups: [
        makeGroup({ id: "root", archived: true }),
        makeGroup({ id: "child", parentId: "root" }),
      ],
    });
    expect(isGroupEffectivelyArchived(document, "child")).toBe(true);
  });

  it("înregistrează integral un cost unic fără tranșă la prima finalizare", () => {
    const previous = makeDocument({ instalments: [], payments: [] });
    const result = reconcileItemCompletion(previous, complete(previous), "structura");

    expect(result.items[0]?.estimate.fixed).toBe(true);
    expect(result.instalments).toHaveLength(1);
    expect(result.instalments[0]).toMatchObject({
      itemId: "structura",
      dueOn: "2027-03",
      projectedCents: 10_000,
    });
    expect(result.payments).toEqual([
      expect.objectContaining({
        itemId: "structura",
        instalmentId: result.instalments[0]?.id,
        paidOn: "2027-03-15",
        amountCents: 10_000,
      }),
    ]);
    for (const scenario of ["base", "high"] as const) {
      expect(selectBudgetView(result, { scenario, asOf: "2027-03-16" }).items[0]).toMatchObject({
        scheduledRemainingRawCents: 0,
        unallocatedFutureCents: 0,
        contingencyCents: 0,
      });
    }
  });

  it("păstrează tranșa și plata manuală, apoi achită numai soldul țintei maxime", () => {
    const previous = makeDocument({
      instalments: [makeInstalment({ projectedCents: 12_000, dueOn: "2027-06" })],
      payments: [makePayment({ amountCents: 3_500 })],
    });
    const result = reconcileItemCompletion(previous, complete(previous), "structura");

    expect(result.instalments).toEqual([
      expect.objectContaining({
        id: "transa-structura",
        dueOn: "2027-06",
        projectedCents: 12_000,
      }),
    ]);
    expect(result.payments[0]).toEqual(previous.payments[0]);
    expect(result.payments[1]).toEqual(
      expect.objectContaining({
        instalmentId: "transa-structura",
        paidOn: "2027-03-15",
        amountCents: 8_500,
      }),
    );
  });

  it("nu dublează o achiziție deja achitată și repetarea este idempotentă", () => {
    const previous = makeDocument({ payments: [makePayment({ amountCents: 10_000 })] });
    const first = reconcileItemCompletion(previous, complete(previous), "structura");
    const repeated = reconcileItemCompletion(previous, first, "structura");

    expect(first.payments).toEqual(previous.payments);
    expect(repeated).toEqual(first);
  });

  it("nu inserează tranșe sau plăți zero la finalizarea unui reper fără cost", () => {
    const zeroCost = makeItem({
      included: false,
      estimate: {
        kind: "total",
        amounts: { baseCents: 0, highCents: 0 },
        fixed: false,
        pricedOn: "2027-01-01",
      },
    });
    const previous = makeDocument({ items: [zeroCost], instalments: [], payments: [] });
    const result = reconcileItemCompletion(previous, complete(previous), "structura");

    expect(result.items[0]?.estimate.fixed).toBe(true);
    expect(result.instalments).toEqual([]);
    expect(result.payments).toEqual([]);
  });

  it("debifarea păstrează istoricul și prețul fix dobândit", () => {
    const previous = makeDocument({ instalments: [], payments: [] });
    const acquired = reconcileItemCompletion(previous, complete(previous), "structura");
    const unchecked = {
      ...acquired,
      items: acquired.items.map((item) => ({
        ...item,
        completion: { complete: false as const },
      })),
    };
    const result = reconcileItemCompletion(acquired, unchecked, "structura");

    expect(result.items[0]?.estimate.fixed).toBe(true);
    expect(result.instalments).toEqual(acquired.instalments);
    expect(result.payments).toEqual(acquired.payments);
  });

  it("lasă finalizarea cu mai multe tranșe independentă de bani", () => {
    const previous = makeDocument({
      instalments: [
        makeInstalment({ id: "transa-unu", projectedCents: 4_000 }),
        makeInstalment({ id: "transa-doi", projectedCents: 6_000 }),
      ],
      payments: [makePayment({ instalmentId: "transa-unu", amountCents: 1_000 })],
    });
    const submitted = complete(previous);
    const result = reconcileItemCompletion(previous, submitted, "structura");

    expect(result).toEqual(submitted);
  });

  it("nu creează plăți pentru bunurile declarate deja deținute", () => {
    const previous = makeDocument({ instalments: [], payments: [] });
    const submitted = complete(previous);
    submitted.items = submitted.items.map((item) => ({ ...item, ownership: "owned" as const }));
    const result = reconcileItemCompletion(previous, submitted, "structura");

    expect(result.instalments).toEqual([]);
    expect(result.payments).toEqual([]);
  });
});
