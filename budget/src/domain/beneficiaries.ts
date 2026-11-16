import { groupBy, sumCents } from "./collections.js";
import { compareUndatedLast } from "./dates.js";
import { TBD_BENEFICIARY_ID, type Beneficiary, type BudgetDocument } from "./schema.js";
import { hierarchyEstimateCents, type BudgetView, type DerivedItem } from "./selectors.js";

export const TBD_BENEFICIARY_LABEL = "TBD";

export interface BeneficiaryBundle {
  id: string;
  name: string;
  beneficiary?: Beneficiary;
  items: DerivedItem[];
  itemCount: number;
  estimateCents: number;
  totalCents: number;
  settledCents: number;
}

export function beneficiaryNamesById(
  beneficiaries: readonly Beneficiary[],
): ReadonlyMap<string, string> {
  return new Map(beneficiaries.map((beneficiary) => [beneficiary.id, beneficiary.name]));
}

/** Payee name of an item, or "TBD" when it has none or it is unknown. */
export function beneficiaryName(
  item: { beneficiaryId?: string | undefined },
  names: ReadonlyMap<string, string>,
): string {
  return (
    (item.beneficiaryId === undefined ? undefined : names.get(item.beneficiaryId)) ??
    TBD_BENEFICIARY_LABEL
  );
}

function makeBundle(
  id: string,
  name: string,
  items: DerivedItem[],
  beneficiary?: Beneficiary,
): BeneficiaryBundle {
  return {
    id,
    name,
    ...(beneficiary === undefined ? {} : { beneficiary }),
    items,
    itemCount: items.length,
    estimateCents: sumCents(items.map(hierarchyEstimateCents)),
    totalCents: sumCents(items.map((entry) => entry.totalCents)),
    settledCents: sumCents(items.map((entry) => entry.settledCents)),
  };
}

/**
 * Groups the budget's derived items by their beneficiary (the payee invoicing the whole item),
 * mirroring the hierarchy's forecast-descending, earliest-scheduled ordering
 * (`byHierarchyOrder` in `selectors.ts`) but tie-broken by catalogue order across groups.
 */
export function getBeneficiaryBundles(
  document: BudgetDocument,
  view: BudgetView,
): BeneficiaryBundle[] {
  const itemIndex = new Map(document.items.map((item, index) => [item.id, index]));
  const byBundleOrder = (left: DerivedItem, right: DerivedItem): number =>
    right.totalCents - left.totalCents ||
    compareUndatedLast(left.scheduleStartOn, right.scheduleStartOn) ||
    (itemIndex.get(left.item.id) ?? 0) - (itemIndex.get(right.item.id) ?? 0);

  const itemsByBeneficiaryId = groupBy(view.items, (entry) => entry.item.beneficiaryId);
  const unassigned = itemsByBeneficiaryId.get(undefined) ?? [];

  const bundles = document.beneficiaries.map((beneficiary) =>
    makeBundle(
      beneficiary.id,
      beneficiary.name,
      (itemsByBeneficiaryId.get(beneficiary.id) ?? []).sort(byBundleOrder),
      beneficiary,
    ),
  );

  if (unassigned.length > 0) {
    bundles.push(
      makeBundle(TBD_BENEFICIARY_ID, TBD_BENEFICIARY_LABEL, unassigned.sort(byBundleOrder)),
    );
  }

  return bundles;
}
