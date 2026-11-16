# Budget catalogue guidance

`project.json` estimates, in EUR, the costs of the demo P+1 house (Casa Exemplu) with a 160 m² gross built-area
basis. The demo is a small fictional catalogue (all figures are round demonstration allowances, with no real quotes,
suppliers or contacts) meant to be replaced with the household's own costs. It is not a measured bill of quantities or
an execution quote. The brief remains the semantic authority for household decisions, and this catalogue is the
operational authority for costs, inclusion, budget state, instalments and payments. When a change is accepted,
reconcile the brief, this catalogue and the model. They may lag each other across commits, but a new price never
silently alters a brief requirement.

House and room dimensions and shapes are open to exploration (`LAY-06`). The recorded areas and quantities are the
current variant's estimating basis, not a required room size. The house retains the 180 m² gross cap including facade
finishes (`LAY-06`). When another variant becomes the budget basis, update `project.builtAreaSqm`, the affected
quantities and estimates. Do not scale unrelated allowances automatically.

## Single budget and provenance

- The app shows one budget based on the single `baseCents` amount, with estimate-to-forecast ranges on items and
  categories (`HH-03`). There are no price scenarios.
- Instalments use `baseCents`. When an item is kept through a revision, preserve its existing dates and reallocate
  the new total proportionally, exact to the cent. New items receive explicit provisional dates within the authorized
  budget interval, independently of brief completion. Dates are not contractual due dates, and the initial catalogue
  contains no actual payments. Estimates are not grown over time. The fixed 10 % contingency applies only to eligible
  future house costs, never to land, movables or payments already made.
- `paymentMode` controls only row presentation: `one-off` hides the item's payment progress, categories keep their
  aggregate progress even when all items are `one-off`, and the value never changes instalments, payments, totals,
  calendar or completion.
- `briefReferences` contain only `{ recordId }` and must resolve to an ID defined in `brief/*.md` (checked by
  `src/data/catalogue.test.ts`). The brief's completion stage comes from the owning record and remains independent of
  budget milestones and instalment dates.
- Land purchase is excluded. Owned goods keep a fixed historical reference value when known but are not new purchases
  and carry no instalments or project payments. Excluded equipment carries no active instalments. The total budget is
  TBD. The app supports exploration without a target or cap.

## Taxonomy

- The milestone classifies the delivery/budget stage. It does not assert that the referenced brief record is completed
  in that stage and it does not set payment timing. `instalments[].dueOn` carries the provisional cash calendar.

  The subcategory names **which part of the house or which trade** is paid, reusing the same vocabulary across
  stages. Every item belongs to a leaf subcategory. An item's label is a short noun phrase (roughly two to five words)
  naming what the sum buys, without dimensions, quantities, SKUs, colours, materials, component lists or installation
  clauses. A brand or product line belongs in the label only when it identifies the purchase (owned assets, accepted
  appliances). Every dropped detail goes in `notes`, the item's description.

- `La roșu`: `Studii, proiectare și avize`, `Branșamente`, `Structură și zidărie`, `Acoperiș`. `La gri`: `Ferestre,
uși și fațadă`, `Instalații electrice și date`, `Instalații termice și ventilație`, `Instalații sanitare și
hidroizolații băi`, `Tencuieli și șape`. `La cheie`: `Echipamente energetice și punere în funcțiune`, `Băi`,
  `Bucătărie și mobilier fix`, `Pardoseli, pereți, uși și scară`, `Terasă, acces și împrejmuire`.
- `La mutat` groups goods functionally: `Mobilier`, `Electrocasnice`, `Curte și grădină`. Already purchased goods stay
  in their functional category, marked owned and completed, never in a status category.
- `Extra` holds post-move purchases (`Mobilier`, `Sisteme și dispozitive`). Its items stay included and planned.
  Extra runs from the `La mutat` month to the Extra end month fixed by the schema.
- Every group ID needs an icon in `src/components/shared/CategoryIcon.tsx`, and an item without an entry in
  `src/components/shared/ItemIcon.tsx` falls back to a generic icon.

## Scope rules

- Each item explains what the sum buys: product, materials, labour or installed package. Each euro of scope belongs
  to exactly one item. Consolidate product and accessories, equipment and installation, or preparation and main work
  when one purchase delivers them, and remove a line whose scope another item already includes, migrating its
  instalments, sources and brief references. Notes distinguish published prices from assumed quantities and unquoted
  allowances. A source may support only one component. Confidence in a source does not confirm the whole package,
  and a starting price, standard product or kit does not validate a complete custom solution.
- Whenever the catalogue is touched, consolidate superfluous items that buy nothing distinct (tiny allowances, prep
  lines for excluded scopes, duplicated commissioning). Keep household-required separations and record in the item's
  notes why each stays separate.
- Replace assumed quantities and unquoted allowances first with the coordinated design and comparable quotes from
  local contractors. Check VAT, transport, installation, tests and already included components explicitly before
  adding commercial packages.
- Quantity × rate items use `quantityBasis: "built-area"` only when the quantity equals `project.builtAreaSqm`
  (the schema checks it). Other quantities (facade, flooring) are explicit allowances until a coordinated take-off.

## Beneficiari

- `beneficiaryId` names the party that invoices the whole item. The demo records one fictional general contractor for
  the `La roșu` labour package. Statutory fees, studies and everything not yet contracted stay unassigned. Never invent
  a payee or reuse the reserved `tbd` ID. Add a beneficiary only when the household knows who will invoice.

## Currency, VAT and quantities

- Costs are integer EUR cents and gross unless an item's notes say otherwise. New conversions from RON use the latest
  BNR reference rate. Read it from `GET /api/exchange-rate` on the running app (the endpoint refetches BNR once its
  cache is 7 days old), or from [BNR directly](https://curs.bnr.ro/nbrfxrates.xml) when the app is unavailable or
  reports `stale`. Each converted item's notes state the rate and date used, and the original value stays in the
  source provenance.

  Never attach the BNR exchange-rate reference to an item's `sourceIds`: the rate is conversion metadata, not material
  pricing evidence for the cost-item sidebar. The standard Romanian VAT rate (21 %) is added to explicitly net prices,
  without re-taxing gross retail or non-VAT providers. A source that does not state VAT stays flagged. Its budgeted
  total is a gross allowance, not a fiscal confirmation.

- `project.builtAreaSqm` (160 m²) is the operational gross area, excluding detached annexes. House design and labour
  use this basis. Model floor faces are not a certified usable-area schedule.
- The demo sources are generic public pages (legislation portal, national statistics, energy regulator). They support
  scope and context, not unit prices. Replace them with direct, dated price pages or quotes when pricing real work.
