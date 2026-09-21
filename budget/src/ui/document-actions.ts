import { estimateCents, type BudgetDocument, type Milestone } from "../domain/index.js";

export function makeStableId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID().replaceAll("-", "")}`;
}

export function descendantGroupIds(document: BudgetDocument, groupId: string): Set<string> {
  const result = new Set<string>();
  const visit = (parentId: string): void => {
    for (const group of document.groups) {
      if (group.parentId === parentId && !result.has(group.id)) {
        result.add(group.id);
        visit(group.id);
      }
    }
  };
  visit(groupId);
  return result;
}

export function isGroupEffectivelyArchived(document: BudgetDocument, groupId: string): boolean {
  const byId = new Map(document.groups.map((group) => [group.id, group]));
  const visited = new Set<string>();
  let current = byId.get(groupId);
  while (current) {
    if (current.archived) return true;
    if (!current.parentId || visited.has(current.parentId)) return false;
    visited.add(current.id);
    current = byId.get(current.parentId);
  }
  return false;
}

export function updateGroupPlacement(
  document: BudgetDocument,
  groupId: string,
  parentId: string | null,
  milestoneId: Milestone["id"],
): BudgetDocument {
  const group = document.groups.find((entry) => entry.id === groupId);
  if (!group) throw new Error("Categoria nu mai există în document.");
  const descendants = descendantGroupIds(document, groupId);
  if (parentId === groupId || (parentId !== null && descendants.has(parentId))) {
    throw new Error("O categorie nu poate fi mutată sub unul dintre subgrupurile sale.");
  }
  const parent = parentId ? document.groups.find((entry) => entry.id === parentId) : undefined;
  if (parentId && !parent) throw new Error("Categoria părinte nu există.");
  if (parent && isGroupEffectivelyArchived(document, parent.id)) {
    throw new Error("Alege o categorie părinte activă.");
  }
  if (parent && parent.milestoneId !== milestoneId) {
    throw new Error("Categoria părinte trebuie să fie în aceeași etapă.");
  }

  const moving = new Set([groupId, ...descendants]);
  return {
    ...document,
    groups: document.groups.map((entry) =>
      moving.has(entry.id)
        ? {
            ...entry,
            milestoneId,
            ...(entry.id === groupId ? { parentId } : {}),
          }
        : entry,
    ),
    items: document.items.map((item) =>
      moving.has(item.groupId) ? { ...item, milestoneId } : item,
    ),
  };
}

export function setGroupArchived(
  document: BudgetDocument,
  groupId: string,
  archived: boolean,
): BudgetDocument {
  if (!document.groups.some((group) => group.id === groupId)) {
    throw new Error("Categoria nu mai există în document.");
  }
  return {
    ...document,
    groups: document.groups.map((group) => (group.id === groupId ? { ...group, archived } : group)),
  };
}

/** Applies the financial side effects of an incomplete-to-complete item transition. */
export function reconcileItemCompletion(
  previousDocument: BudgetDocument,
  nextDocument: BudgetDocument,
  itemId: string,
): BudgetDocument {
  const previousItem = previousDocument.items.find((item) => item.id === itemId);
  const nextItem = nextDocument.items.find((item) => item.id === itemId);
  if (!nextItem) throw new Error("Elementul nu mai există în document.");
  if (
    previousItem?.completion.complete ||
    !nextItem.completion.complete ||
    nextItem.ownership !== "planned"
  ) {
    return nextDocument;
  }

  const instalments = nextDocument.instalments.filter((entry) => entry.itemId === itemId);
  if (instalments.length > 1) return nextDocument;

  const completedOn = nextItem.completion.completedOn;
  if (!completedOn) {
    throw new Error("Finalizarea unui cost unic necesită data finalizării.");
  }

  const existingInstalment = instalments[0];
  const targetCents = Math.max(
    estimateCents(nextItem.estimate, "base"),
    existingInstalment?.projectedCents ?? 0,
  );
  const actualPaidCents = nextDocument.payments
    .filter((payment) => payment.itemId === itemId)
    .reduce((total, payment) => total + payment.amountCents, 0);
  const outstandingCents = Math.max(targetCents - actualPaidCents, 0);
  const acquisitionInstalment =
    existingInstalment ??
    (targetCents > 0
      ? {
          id: makeStableId("transa"),
          itemId,
          label: "Achiziție",
          dueOn: completedOn.slice(0, 7),
          projectedCents: targetCents,
        }
      : undefined);

  return {
    ...nextDocument,
    items: nextDocument.items.map((item) =>
      item.id === itemId ? { ...item, estimate: { ...item.estimate, fixed: true } } : item,
    ),
    instalments: acquisitionInstalment
      ? existingInstalment
        ? nextDocument.instalments.map((entry) =>
            entry.id === existingInstalment.id ? { ...entry, projectedCents: targetCents } : entry,
          )
        : [...nextDocument.instalments, acquisitionInstalment]
      : nextDocument.instalments,
    payments:
      outstandingCents > 0 && acquisitionInstalment
        ? [
            ...nextDocument.payments,
            {
              id: makeStableId("plata"),
              itemId,
              instalmentId: acquisitionInstalment.id,
              paidOn: completedOn,
              amountCents: outstandingCents,
              note: "Sold înregistrat la finalizare",
            },
          ]
        : nextDocument.payments,
  };
}
