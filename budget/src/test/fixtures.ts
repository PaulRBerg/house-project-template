import { budgetDocumentSchema, type BudgetDocument } from "../domain/schema.js";
import { makeDocument, makeGroup, makeInstalment, makeItem } from "../domain/test-fixtures.js";

export const uiFixtureIds = {
  groups: {
    professional: "professional",
    construction: "construction",
    rough: "rough",
    finish: "finish",
    move: "move",
  },
  items: {
    professionalCore: "professional-core",
    constructionCore: "construction-core",
    finishOptional: "finish-optional",
    moveMovable: "move-movable",
    moveArchivedComplete: "move-archived-complete",
  },
} as const;

export function makeUiDocument(overrides: Partial<BudgetDocument> = {}): BudgetDocument {
  const groups = [
    makeGroup({
      id: uiFixtureIds.groups.professional,
      label: "Proiectare și consultanță",
      parentId: uiFixtureIds.groups.construction,
      milestoneId: "la-rosu",
      sortOrder: 0,
    }),
    makeGroup({
      id: uiFixtureIds.groups.construction,
      label: "La roșu",
      milestoneId: "la-rosu",
      sortOrder: 1,
    }),
    makeGroup({
      id: uiFixtureIds.groups.rough,
      label: "La gri",
      milestoneId: "la-gri",
      sortOrder: 2,
    }),
    makeGroup({
      id: uiFixtureIds.groups.finish,
      label: "La cheie",
      milestoneId: "la-cheie",
      sortOrder: 3,
    }),
    makeGroup({
      id: uiFixtureIds.groups.move,
      label: "La mutat",
      milestoneId: "la-mutat",
      sortOrder: 4,
    }),
  ];
  const items = [
    makeItem({
      id: uiFixtureIds.items.professionalCore,
      label: "Arhitectură",
      groupId: uiFixtureIds.groups.professional,
      milestoneId: "la-rosu",
      costType: "professional-fee",
      sortOrder: 0,
    }),
    makeItem({
      id: uiFixtureIds.items.constructionCore,
      label: "Structură",
      groupId: uiFixtureIds.groups.construction,
      milestoneId: "la-rosu",
      costType: "work",
      sortOrder: 0,
    }),
    makeItem({
      id: uiFixtureIds.items.finishOptional,
      label: "Placare opțională",
      groupId: uiFixtureIds.groups.finish,
      included: false,
      milestoneId: "la-cheie",
      sortOrder: 0,
    }),
    makeItem({
      id: uiFixtureIds.items.moveMovable,
      label: "Canapea mobilă",
      groupId: uiFixtureIds.groups.move,
      milestoneId: "la-mutat",
      costScope: "movable",
      costType: "movable-good",
      contingencyEligible: false,
      sortOrder: 0,
    }),
    makeItem({
      id: uiFixtureIds.items.moveArchivedComplete,
      label: "Scaun arhivat",
      groupId: uiFixtureIds.groups.move,
      milestoneId: "la-mutat",
      costScope: "movable",
      costType: "movable-good",
      contingencyEligible: false,
      archived: true,
      completion: { complete: true, completedOn: "2026-09-18" },
      ownership: "owned",
      sortOrder: 1,
    }),
  ];

  return budgetDocumentSchema.parse(
    makeDocument({
      groups,
      items,
      instalments: items.map((item) =>
        makeInstalment({
          id: `instalment-${item.id}`,
          itemId: item.id,
          label: `Tranșă ${item.label}`,
        }),
      ),
      ...overrides,
    }),
  );
}
