import { describe, expect, it } from "vitest";

import {
  makeBeneficiary,
  makeDocument,
  makeInstalment,
  makeItem,
  makePayment,
} from "../test/builders.js";
import { getBeneficiaryBundles, TBD_BENEFICIARY_LABEL } from "./beneficiaries.js";
import { TBD_BENEFICIARY_ID } from "./schema.js";
import { selectBudgetView } from "./selectors.js";

const options = { asOf: "2027-01-01" };

describe("getBeneficiaryBundles", () => {
  it("orders bundles in catalogue order, with a trailing TBD bundle for unassigned items", () => {
    const alpha = makeBeneficiary({ id: "alpha", name: "Alpha SRL" });
    const beta = makeBeneficiary({ id: "beta", name: "Beta SRL" });
    const document = makeDocument({
      beneficiaries: [alpha, beta],
      items: [
        makeItem({ id: "item-alpha", beneficiaryId: "alpha" }),
        makeItem({ id: "item-beta", beneficiaryId: "beta" }),
        makeItem({ id: "item-unassigned" }),
      ],
      instalments: [],
    });
    const view = selectBudgetView(document, options);
    const bundles = getBeneficiaryBundles(document, view);
    expect(bundles.map((bundle) => bundle.id)).toEqual(["alpha", "beta", TBD_BENEFICIARY_ID]);
    expect(bundles[2]?.name).toBe(TBD_BENEFICIARY_LABEL);
    expect(bundles[2]?.beneficiary).toBeUndefined();
  });

  it("includes a beneficiary with zero items and omits the TBD bundle when every item is assigned", () => {
    const alpha = makeBeneficiary({ id: "alpha", name: "Alpha SRL" });
    const gamma = makeBeneficiary({ id: "gamma", name: "Gamma SRL" });
    const document = makeDocument({
      beneficiaries: [alpha, gamma],
      items: [makeItem({ id: "item-alpha", beneficiaryId: "alpha" })],
      instalments: [],
    });
    const view = selectBudgetView(document, options);
    const bundles = getBeneficiaryBundles(document, view);
    expect(bundles.map((bundle) => bundle.id)).toEqual(["alpha", "gamma"]);
    const gammaBundle = bundles.find((bundle) => bundle.id === "gamma");
    expect(gammaBundle).toMatchObject({
      itemCount: 0,
      estimateCents: 0,
      totalCents: 0,
      settledCents: 0,
    });
  });

  it("leaves unpaid excluded items out of the sums, while item count includes them", () => {
    const alpha = makeBeneficiary({ id: "alpha", name: "Alpha SRL" });
    const document = makeDocument({
      beneficiaries: [alpha],
      items: [
        makeItem({
          id: "item-active",
          beneficiaryId: "alpha",
          estimate: {
            kind: "total",
            amounts: { baseCents: 10_000 },
            fixed: true,
            pricedOn: "2026-09-18",
          },
        }),
        makeItem({
          id: "item-excluded",
          beneficiaryId: "alpha",
          included: false,
          estimate: {
            kind: "total",
            amounts: { baseCents: 50_000 },
            fixed: true,
            pricedOn: "2026-09-18",
          },
        }),
      ],
      instalments: [],
    });
    const view = selectBudgetView(document, options);
    const [bundle] = getBeneficiaryBundles(document, view);
    expect(bundle?.itemCount).toBe(2);
    // The unpaid excluded item's larger 50,000-cent estimate must not reach the sums.
    expect(bundle?.estimateCents).toBe(10_000);
    expect(bundle?.totalCents).toBeLessThan(50_000);
    expect(bundle?.settledCents).toBe(0);
  });

  it("sums archived payments and overpaid items like the category hierarchy", () => {
    const alpha = makeBeneficiary({ id: "alpha", name: "Alpha SRL" });
    const document = makeDocument({
      beneficiaries: [alpha],
      items: [
        makeItem({ id: "item-archived", beneficiaryId: "alpha", archived: true }),
        makeItem({ id: "item-overpaid", beneficiaryId: "alpha", sortOrder: 1 }),
      ],
      instalments: [
        makeInstalment({ id: "archived-plan", itemId: "item-archived" }),
        makeInstalment({ id: "overpaid-plan", itemId: "item-overpaid" }),
      ],
      payments: [
        makePayment({
          id: "archived-payment",
          itemId: "item-archived",
          instalmentId: "archived-plan",
          amountCents: 3_000,
        }),
        makePayment({
          id: "overpaid-payment",
          itemId: "item-overpaid",
          instalmentId: "overpaid-plan",
          amountCents: 12_000,
        }),
      ],
    });
    const view = selectBudgetView(document, options);
    const [bundle] = getBeneficiaryBundles(document, view);
    const root = view.hierarchy[0];
    expect(bundle).toMatchObject({
      estimateCents: 15_000,
      totalCents: 15_000,
      settledCents: 15_000,
    });
    expect(bundle).toMatchObject({
      estimateCents: root?.estimateCents,
      totalCents: root?.totalCents,
      settledCents: root?.settledCents,
    });
  });

  it("orders items within a bundle by totalCents descending", () => {
    const alpha = makeBeneficiary({ id: "alpha", name: "Alpha SRL" });
    const document = makeDocument({
      beneficiaries: [alpha],
      items: [
        makeItem({
          id: "item-small",
          beneficiaryId: "alpha",
          contingencyEligible: false,
          costScope: "movable",
          costType: "movable-good",
          estimate: {
            kind: "total",
            amounts: { baseCents: 10_000 },
            fixed: true,
            pricedOn: "2026-09-18",
          },
        }),
        makeItem({
          id: "item-large",
          beneficiaryId: "alpha",
          contingencyEligible: false,
          costScope: "movable",
          costType: "movable-good",
          estimate: {
            kind: "total",
            amounts: { baseCents: 90_000 },
            fixed: true,
            pricedOn: "2026-09-18",
          },
        }),
      ],
      instalments: [],
    });
    const view = selectBudgetView(document, options);
    const [bundle] = getBeneficiaryBundles(document, view);
    expect(bundle?.items.map((entry) => entry.item.id)).toEqual(["item-large", "item-small"]);
  });
});
