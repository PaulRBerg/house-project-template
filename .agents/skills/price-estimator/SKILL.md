---
argument-hint: "[budget item labels or IDs] [quantity, specification, or supplier constraints]"
compatibility: Requires internet access and the shared Chromium browser configured by chromium-browser.
coordination: exempt
name: price-estimator
skill-dependencies:
  - PaulRBerg/agent-skills#chromium-browser
  - household-brief
description: >-
  Estimate or compare current prices for any budget-app cost item in the project's Romanian locality: construction
  manoperă, materials, systems, electronics, finisaje, furniture, and other purchases. Return a concise EUR table of
  the best supported estimates with direct source links for the house's current recorded built-area basis.
---

# Price Estimator

Research comparable local offers and turn them into a short, traceable EUR estimate for the household budget.

This skill is coordination-exempt: skip the ai-coord gate for its declared work. Its default deliverable is a chat
report; explicitly authorized repository writes re-enter the gate and follow `budget/AGENTS.md`.

## Contract

- Default to the **project's locality** recorded in `brief/project.md` (`HH-02`). Read the built-area basis (`project.builtAreaSqm`) from
  `budget/data/project.json` before estimating. It is the operational basis and may briefly lag the brief or model.
  Explicit user instructions override these defaults. Mention a mismatch you notice without blocking on it or changing
  the records.
- Cover any requested cost item, regardless of category. Estimate the specified quality and scope. Do not silently
  substitute a cheaper specification, a different product, or a different household decision.
- Invoke `chromium-browser` before browser work and follow its shared-browser ownership, evidence, and cleanup rules.
  Use rendered supplier pages to verify the shortlisted offers. Search tools and public HTTP retrieval may support
  discovery and official exchange-rate retrieval. Search snippets alone do not establish a price.
- Read every shop price and its VAT wording from the rendered page in Chromium, through a snapshot or a screenshot.
  Fetched page text, search snippets and cached copies do not establish a shop price or its VAT status.
- Never use the BNR or ECB exchange rate as a price source. It is conversion metadata only.
- Research and report without changing the budget, contacting suppliers, submitting quote requests, or purchasing.
  Existing explicit authorization for additional work remains valid. This skill adds no confirmation requirement.
- Report all prices, rates, allowances, and totals in **EUR only**. Preserve raw currency in working evidence for
  reproducibility, but do not present RON price columns or mixed-currency comparisons.

## Resolve the requested items

1. Announce the items and research scope in one sentence. Give brief updates when a scope mismatch, local availability,
   or evidence gap changes the estimate.
2. Read `budget/AGENTS.md` and match the user's labels or IDs to `budget/data/project.json`. Inspect only the relevant
   items, groups, linked sources, and project assumptions. Use the running budget app (`http://127.0.0.1:8437`, started with `just budget dev`) through Chromium when the
   request depends on the displayed app state. Keep stable item IDs in working evidence.
3. Invoke `household-brief` to read the item's referenced household decisions and relevant owned inventory. Preserve
   each decision's completion stage and explicit flexibility, and distinguish new purchases from already-owned items. For a proposed
   item absent from the catalogue, research it as a proposal without creating a record.
4. Establish a comparable specification: quantity, unit, dimensions/capacity, material or exact model, quality,
   supply-only versus installation, and included preparation/accessories. Use current records and the user's request
   before assuming anything. Ask only for missing information that materially prevents a useful estimate. While waiting,
   continue independent items. Otherwise, state a narrow assumption or offer a clearly labeled unit-rate range.
5. Use the current recorded built-area basis only where the quoted rate explicitly applies to the same built-area
   definition. It is not the roof, facade, wall, net floor, tiling, garden, or plot area. Never derive concrete volume,
   steel tonnage, cable length, furniture count, or equipment capacity from it without an explicit, defensible quantity
   basis. When the quantity is unknown, return a unit rate and mark the total as unavailable.

## Check material drift

Run this check for every finish, facade, bathroom, flooring, wall or roof item, and when the user asks for a drift
check. Report the result. Do not change the brief, the budget or the model.

1. Read the material that the budget item prices from its `label` and `notes` in `budget/data/project.json`.
2. Read the accepted material from the brief: `brief/interiors.md`, `brief/rooms-and-furnishings.md`,
   `brief/architecture.md` and `brief/outdoor.md`.
3. Read the modeled material from `model/design/house.json` (each room's `material_id` floor and `wall_finish`),
   `model/design/style.json` (materials and `surface` entries) and `model/design/furnishings.json`. The current
   finish list is in `.agents/skills/blender-model/references/interior-design.md`.
4. Report each mismatch with the item ID and the brief record ID:
   - The budget prices a different material, such as ceramic tile where the brief or model shows microcement.
   - The brief or model shows a material that no cost line prices, such as a limewash wall.
5. Price the material that the brief accepts. When the brief and the model disagree, state the conflict and follow
   the brief.

## Find and verify comparable evidence

Search in Romanian, trying diacritic and plain variants of the locality and county names (for example `Ș`/`S`, `ț`/`t`). Combine the
actual item/specification with terms such as `preț`, `manoperă`, `montaj`, `TVA`, and `livrare`. Use current dates to
assess freshness. A year in a page title does not prove the prices were updated.

Prefer businesses serving the project's locality and county, then Romanian suppliers demonstrably delivering to the site. Use national
benchmarks or EU suppliers only when local evidence is sparse or the specified product requires them, and label that
limitation. A national delivery claim does not prove heavy-goods access, unloading, or installation at the project's site.

| Item type                 | Evidence to prioritize                                                                       | Comparison details that control the price                                                                                 |
| ------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Construction manoperă     | Local contractors' own tariffs and defined work packages. Corroborate with another provider. | Labor versus materials, measured unit, substrate/preparation, machinery, access, crew travel, minimum job charge          |
| Raw materials             | Local depots, manufacturers, Romanian distributors and building merchants                    | Grade, strength, dimensions, thickness, density, pack/pallet yield, quantity breaks, transport and unloading              |
| Finisaje                  | Product suppliers plus local installers for the same finish                                  | Wear/specification class, substrate work, primer/adhesive/grout, trims, waste, supply versus fitting                      |
| Electronics/appliances    | Exact manufacturer model/SKU at independent Romanian sellers                                 | Seller identity, new/refurbished condition, warranty, stock, accessories, delivery and installation                       |
| Furniture/joinery         | Retailers for matched dimensions/materials. Local workshops for custom work.                 | Modules, carcass/front materials, hardware, worktops, assembly, measuring and fitting. Bespoke scope often needs a quote. |
| Building systems/services | Specialist suppliers/installers with specified packages                                      | Capacity/design basis, equipment, distribution, controls, commissioning, exclusions and service coverage                  |

For each item, seek **2–4 independent, comparable price sources** across different businesses/websites. Inspect extra
candidates only to resolve a material discrepancy or evidence gap. Present just the best few. Multiple pages from one
seller or syndicated copies of one tariff count as one source. Aggregators, marketplaces, forums, and generic cost
articles can help discovery or corroboration. Prefer the underlying seller/provider for the actual price.

Open shortlisted sources through Chromium and verify the selected variant, seller, price, unit, VAT wording,
availability, location/service area, delivery terms, and offer conditions. Record the exact product/service URL,
page title, access date, stated price date/expiry if any, raw price/currency, inclusions/exclusions, and any assumptions.
Keep evidence compact enough to preserve it across compaction together with owned page IDs and unresolved items.

Exclude expired offers and unavailable products from the actionable shortlist. If useful, label them as historical
benchmarks. Separate membership, coupon, bulk-only, or financing conditions from generally available prices. Treat
“de la”/“from” figures as lower bounds, and “price on request” as missing evidence. A supplier's advertised price is
not a site-specific quotation. If Chromium or a site is unavailable, follow the browser skill's recovery boundary,
finish independently supported items, and disclose which prices could not be verified.

## Normalize to EUR and the same scope

- Read the **EUR/RON reference rate** from `GET http://127.0.0.1:8437/api/exchange-rate`: a server-side cache
  refreshed at most every 7 days, BNR first with an ECB fallback. The response carries `ronPerEur`, `rateDate`,
  `source`, and `stale`. State the returned `rateDate` and `source`. Fetch `https://curs.bnr.ro/nbrfxrates.xml`
  directly (the old `www.bnr.ro/nbrfxrates.xml` URL now redirects to an HTML page) when the app is unavailable or its
  rate is `stale` or more than 7 days old, and fall back to the **ECB reference rate** if BNR is unreachable, identifying the fallback. Link the official rate
  source.

  For `r` RON per EUR, calculate `EUR = RON / r`. Use the same rate throughout the run. Never assume a round
  exchange rate. If no verified rate is available, leave affected EUR estimates unavailable unless the user supplies a
  rate, which must be labeled as their assumption.

- For other currencies, use a verified dated official EUR conversion or same-date cross-rate. Keep intermediate
  precision and round only for presentation. Use a calculator or code for conversion, pack rounding, and totals.
- Compare household out-of-pocket costs. Record the VAT status of every price as `included`, `excluded`,
  `not-applicable` or `unknown`, the `tax.status` values of the budget sources. Take the status from the rendered
  page. An `unknown` status is an evidence gap, not a value. Do not assume that a shop price includes VAT. Report
  every `unknown` status as a gap. For a net price, verify the applicable current VAT treatment from an official source before adding it.
  Never add VAT twice or assume a provider charges VAT. Label unknown tax treatment. Do not call that total all-in.
- Normalize pieces, packs, pallets, m², m³, tonnes, linear metres, hours, and lump sums explicitly. For packaged goods,
  calculate purchasable pack counts. Show any assumed waste separately and justify it for the material. Do not apply
  one waste percentage to every category.
- Calculate the comparable total from the purchased quantity, gross unit price, and separately identified delivery,
  unloading, travel, assembly, installation, consumables, and other necessary charges. Mark each material add-on as
  included, evidenced, assumed, excluded, or unknown. Unknown charges are not zero. Label a partial subtotal clearly.
- Keep labor, materials, and bundled supply/install quotes distinct until scopes match. Avoid counting installation,
  accessories, or material allowances again when they are already included or owned elsewhere in the budget.
- Estimate at today's prices. The app applies no price growth and adds a fixed 10 % contingency to eligible house
  costs itself. Do not embed escalation or a reserve in an item price. If the user asks for a future-date estimate,
  state its date and escalation basis separately.

## Select the best estimates

Prefer comparable scope, local applicability, credible current evidence, and complete delivered/installed costs over
the lowest headline price. Investigate outliers. Do not average different specifications or use arbitrary local
discounts. Distinguish observed prices from calculated totals and judgment-based allowances.

For each item, recommend one **base allowance** supported by current comparable offers for the same specification
and quantity. Where useful, show an evidence-backed offer range separately. Do not manufacture an upper bound,
automatic percentage uplift, or specification upgrade. Browsing a price does not make it fixed.

The app uses the single `baseCents` amount for its budget and calculates the displayed estimate-to-forecast range from
its accounting assumptions. `amounts`/`rates` carry no other tier. Do not present Optimist/Prudent scenarios.

Assign confidence to the whole estimate:

- **high** for matched current offers with quantity, tax and local fulfillment established.
- **medium** for corroborated offers with a limited stated assumption.
- **low** for sparse, indirect, old, or scope-incomplete evidence.

A precise retail price does not make an unknown installation total high-confidence.
When fewer than two independent sources survive, show the evidence found and the limitation. Never pad the shortlist.

## Present a compact, polished table

Lead with the recommended EUR allowance and its key qualification. Add one compact context line with location,
quantity/area basis, research date, and tax/delivery basis. Put the dated FX convention and official source in a short
note. Exchange-rate metadata may name RON, but all cost figures remain EUR.

For **one item**, show 2–4 of the best comparable offers when supported. Use these columns, right-align monetary
values, and bold the preferred row's label and total:

| Offer / exact scope | VAT | Unit price (€ / unit) | Total for stated quantity (€) | Included / unresolved | Sources |
| ------------------- | --- | --------------------: | ----------------------------: | --------------------- | ------- |

State the recommended **base allowance** and confidence immediately beside the table in concise
prose. If totals are unknowable, make the monetary column explicitly a unit rate and show `—` for missing totals.

For **multiple items**, use one row per requested item, keeping every requested item accounted for:

| Item / quantity | Recommended allowance (€) | Scope / confidence | Sources |
| --------------- | ------------------------: | ------------------ | ------- |

Use short labels, consistent separators, and meaningful rounding: cents where a small unit rate needs them, usually
whole euros for retail totals, and appropriately coarser rounding for uncertain construction allowances. Use `—` for
unknown values, never zero. Add a sum only for independent, non-overlapping items with compatible scope and known
quantities. Label partial subtotals and never sum alternative offers. Omit a grand total when it would mislead.

Link directly to the exact product, tariff, or service page in the relevant row with descriptive supplier/page labels.
Keep the displayed reference set small, normally 2–4 price links per item plus the shared FX source. Deduplicate
shared sources and briefly state what each supports when the row alone is insufficient. Prefer durable URLs without
tracking parameters. Retain identifiers needed to resolve the actual product or variant. Do not cite search-result
pages or unrelated homepages as price evidence.

Finish with only the material assumptions/exclusions and the missing quantity or site-specific quotation that would
most improve accuracy. Keep table cells short and put explanations below them. Match the user's language.
Generate an HTML report or write estimates back only when requested.
The default Markdown table should already be attractive and self-contained.

## Completion check

Before responding, verify all of the following:

- Every requested item has a supported estimate or explicit evidence gap.
- Comparisons share scope and units.
- All cost figures are EUR.
- Arithmetic and any offer-range ordering are checked.
- VAT, local fulfillment and unknown add-ons are disclosed.
- Each recommendation has direct dated evidence.
- Every shop price was read from the rendered page in Chromium.
- Every price has a VAT status, and every `unknown` status is reported as a gap.
- No exchange rate is cited as a price source.
- The material drift check ran for every finish, facade, bathroom, flooring, wall or roof item.

Complete `chromium-browser` page cleanup. State any verification limitation honestly. The result is a dated budgeting
estimate, not a binding quote.
