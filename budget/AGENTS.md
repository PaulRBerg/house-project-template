# Budget app guidance

`budget/` is the local EUR budget planner for the demo house (Casa Exemplu): React, Vite, TypeScript,
Tailwind CSS v4, Bun and Lucide icons, listening only on `127.0.0.1:8437` and reading `data/project.json`.
It is the household's primary tool for budget categories and budget state. The checked-in catalogue is a small
fictional demo to replace with the household's own costs. Household decisions and owned inventory stay
in `brief/` and are referenced by stable IDs. [`data/AGENTS.md`](data/AGENTS.md) owns the catalogue methodology.

- Build and verify the app for desktop only. Do not add mobile layouts, mobile-specific behavior, or mobile viewport checks. Desktop verification is sufficient even when general frontend guidance asks for both.
- Run `bun install` from the repository root. The Bun workspace owns the shared lockfile. App commands below assume `budget/`. From the repository root, use `just budget <recipe>` with the same arguments.

  `just check` runs `typecheck` and `test`. Run `just lint`, `just format-check` and `just build` on demand. `just lint` uses Oxlint plus ESLint's Tailwind CSS and React Hooks rules. `just lint-eslint` runs ESLint alone over `src` and accepts paths or flags.

  `just format` uses Oxfmt for code and Prettier for Markdown/YAML.

- Prefer focused automated tests for functional changes: `just test-node src/api/client.test.ts` or `just test-ui src/App.loading.test.tsx`. `just test` runs both projects. It and `just test-watch` also accept file filters and Vitest flags. Keep `.test.ts` tests in Node and React interaction tests in jsdom `.test.tsx` files. Give a UI test a distinct basename when a `.test.ts` counterpart exists. TypeScript otherwise excludes the `.tsx` file.
- Reuse `src/test/render.tsx` for isolated nuqs state, `src/test/builders.ts` for minimal record builders, `src/test/fixtures.ts` for validated budget documents, `src/test/api.ts` for snapshots and stubbed API fetches, `src/test/budget-file.ts` for temporary server data files, and `src/test/budget-table.ts` for `BudgetTable` props. Exercise real components, selectors, snapshot hook, and API client. Stub network/browser boundaries. The UI setup blocks unstubbed fetches and cleans up renders and spies. Assert dialogs through public roles, state, and interactions rather than native-dialog internals. The animation shim does not prove focus trapping or visual behavior.
- Prefer deep-imported Base UI compound primitives for dialogs, selects, tabs, toggles, collapsibles, and fields where they add accessible interaction behavior. Keep their styling application-owned. Style components with Tailwind CSS v4 utilities.

  `src/styles/global.css` owns the CSS-first theme and base styles. The Vite plugin compiles classes from `src/`. Keep conditional utilities as complete static tokens (enforced by `local/no-classname-concatenation`) and share repeated class values through `src/components/shared/styles.ts`. Preserve automatic light/dark theming through `prefers-color-scheme` and verify the budget, cash-flow, and assumptions-dialog views in both themes on desktop after styling changes.

- Keep Tailwind classes canonical, ordered, and free of unknown, duplicate, or conflicting utilities. ESLint checks JSX classes, `cn`/`tv` calls, and shared `*Styles` variables against the app's CSS entrypoint. Retain React Hooks' recommended rules with `exhaustive-deps` enforced as an error.
- Use the shared `--z-*` scale in `src/styles/global.css` through `z-(--z-...)` utilities instead of numeric z-index values. Keep sticky content below the header and dropdowns. Drawers and their backdrops sit above page UI.
- Use `cn` for class merging and `tv` for reusable variant recipes. Animate Base UI primitives with their starting/ending state attributes. For other animated presence, use the shared motion recipes with `useAnimatedPresence`, attaching its `ref` to the element that owns the animation. Keep drawers and rows mounted through exit. View handovers retain hidden layout while `present` is false. Use `appear: true` only for initially open elements that should animate, and preserve reduced-motion behavior.
- Keep the compiler aliases distinct: `@typescript/native` provides TypeScript 7's `tsc`, while `typescript` aliases `@typescript/typescript6` for the API required by `typescript-eslint`.
- Start the app with `just budget dev` (from `budget/`, `just dev`). It serves on loopback port 8437 with `strictPort`, so a second instance needs an explicit `--port`.

  Chromium evidence is required only for layout, colors or themes, animation appearance, dialog modality or focus restoration, actual History API integration, stylesheet delivery, or browser-specific regressions. Preserve desktop-only and both-theme checks for styling work.

- The catalogue's `beneficiaries` collection (`id`, `name`, optional `phone`/`email`/`website`) records the payee that receives the money for a cost item. An item's optional `beneficiaryId` links to one, and the app shows unassigned items as "TBD". `item.brand` names the product brand and is unrelated to the beneficiary.

- Keep `data/project.json` at schema version 1 and validate it with `budgetDocumentSchema`. Preserve stable IDs and all explicit inclusion, ownership, completion, archive, source, and brief-reference fields.
- Let the stage color follow the selection. The overview's stage spine sizes each segment by forecast share and fills it by completed items. The stage strip is the single category tab bar, retaining dates, totals, completion counts, and forecast shares.

  Stage tabs, the category summary band, and the budget table root use `data-stage` with the `stage-tint`/`stage-header` tokens. Category rows render as stage-tinted section bands (`bg-stage-tint/50`, nested `/25`) with an `eyebrowStyles` label, a muted visible-item count, and shorter cells. Item rows indent past the chevron gutter so each item sits one step right of its parent icon. The room header grid mirrors the table's column widths.

  The five top-level categories are `construction`, `rough`, `finish`, `move`, and `extras`. Planning subcategories belong to `construction`. Share pill toggles through `segmentedGroupStyles`/`segmentedToggleStyles`. Show no ownership/completion badges in the table (owned rows carry only the olive left rule and their historical price. The details drawer's Plăți row reuses `PaymentProgress` with the completion date). Format money ranges with an en dash.

  Payment status uses a muted circle and label when unpaid, an olive check and label when paid, and a compact progress ring with paid/remaining amounts for partial payments. Omit endpoint tracks and percentages. Drawers use the shared `Dialog` with an optional `leading` tile (the item details pass a stage-tinted `ItemIcon`). Inside drawers, prefer ruled sections and stat rows over nested cards.

- Use the installed `lucide-react` library and shared `StageIcon` for consistent stage symbols and colors. Keep labels accessible and decorative icons hidden from assistive technology. Use `ItemIcon`'s explicit stable-ID mapping for cost items, with its named fallback for later imports. Add a monochrome `ItemBrandIcon` only for an explicitly selected, supported brand, while retaining the object icon. Do not infer a brand from a price comparator.
- Store all calculated costs as integer euro cents. A source may retain raw-currency provenance, but application calculations and displayed costs remain EUR.
- Use the selectors in `src/domain/selectors.ts` for all summaries, hierarchy totals, monthly cash flow, cumulative cash, timeline, and upcoming payments. Cash-flow periods bucket allocations with its `emptyCashFlowBucket`, `addToCashFlowBucket` and `withCumulativeCents`. Do not reimplement accounting in React components. Shared owners:

  - `src/domain/schema.ts` for milestone, beneficiary, bps and collection constants.
  - `src/domain/collections.ts` and `dates.ts` for cent sums, grouping, the UI locale and date spans.
  - `src/ui/format.ts` for money, dates, percentages, Romanian plurals, search normalization and table item cost.
  - `src/components/budget/categories.ts` for category defaults and room grouping.
  - `src/api/contracts.ts` for API paths and the BNR page URL.

- `areaId` is optional presentation metadata on budget items. Missing values belong to the `unassigned` fallback. Shared and whole-house areas remain independent catalogue areas, and area views derive filtered category bundles without changing item IDs or accounting.
- Detailed-table `totalCents` and `settledCents` include active owned items at the greater of historical base price and recorded payments, counted once. Keep these distinct from cash forecasts and actual-payment allocations: historical prices alone must not create ledger payments, dates, or future obligations.
- Keep the whole UI read-only, including the assumptions dialog. Clicking a cost item in the budget or
  cash-flow view opens a read-only details drawer with its estimate basis, notes, linked pricing sources (including
  scope, access date, VAT, confidence, and provenance), and brief references. Preserve access to this evidence when
  changing item interactions. Author item notes as Markdown with `€` stored directly. Render them without raw HTML.
  Source descriptions and provenance remain plain text and may retain the `EUR` → `€` presentation transform without
  changing stored source text or numeric notation.
- Sort rows within each budget category by forecast `totalCents` descending, then earliest scheduled date ascending (undated last), with catalogue order as the final tie-breaker. Keep the top-level category tabs in catalogue order.
- Manage main-view and category navigation with `nuqs` query state (`page=flux`, `page=beneficiari`, `category=<stable group ID>`, `beneficiar=<beneficiary ID|tbd>`), using browser history entries. Finish, move and Extra stages default to room grouping. `grouping=categories` selects their alternate category view, while the default room mode is omitted. Omit defaults (`budget` and `construction`) from the URL. `beneficiar` has no default and is omitted when absent. Switching pages never clears `category` or `beneficiar`.

  Start all table groups expanded when opening the app, entering any category, or changing grouping, including through Back/Forward. Users can collapse groups manually, and active search still reveals matching rows. Keep category tabs mounted so keyboard focus survives navigation.

- Persist instalment `projectedCents` as the base-price plan. The app subtracts actuals from that plan and schedules the unpaid remainder at base prices. Completion state never changes amounts or payments. Preserve cent-exact allocation, separate contingency, and actuals when archiving.
- Keep filesystem modules under `src/server/`. Browser code must never import them. Use `src/api/` for the read-only API client and `src/domain/` for validated contracts and accounting.
- Use `just cost` for single cost-item edits instead of editing `data/project.json` by hand. Run it with no arguments to see the usage. From the repository root, use `just budget cost`.

  - `just cost add <id> <category-id> <label> <eur> [--due YYYY-MM]... [--with '<item JSON>']` adds an item at the end of a leaf category. Each `--due` month adds one instalment, and the instalments share the estimate equally.
  - `just cost delete <id>` removes the item and its instalments. It keeps the sources.
  - `just cost move <id> <category-id>` moves the item to the end of a leaf category and takes the category milestone.
  - `just cost rename <id> <label>` changes the label. The stable ID does not change.
  - `just cost set-price <id> <eur> [--priced-on YYYY-MM-DD]` sets the total estimate, or the unit rate of a quantity × rate estimate. It reallocates the instalments proportionally, exact to the cent, and keeps their dates.
  - `just cost split <id> <new-id> <new-label> <eur> [--with '<item JSON>']` moves part of a total estimate into a new item. The new item copies the source fields and instalment dates.

  `--with` merges item fields such as `notes`, `costType`, `sourceIds` or `briefReferences`. The command derives `milestoneId`, `sortOrder` and `contingencyEligible`. Each command validates the whole document with `budgetDocumentSchema`, writes it with `serializeBudgetDocument` through a temporary file and an atomic rename, and stops when the file changed during the edit. `delete` and `split` refuse items with recorded payments. Edit those items by hand. `src/domain/cost-edits.ts` owns the operations and `src/server/cost-cli.ts` owns the file access.

- Write the canonical data (from scripts or tests) with `serializeBudgetDocument`. Do not apply a generic pretty-printer to `data/project.json`, because one-record-per-line formatting keeps the catalog under the repository line limit.
- Missing or malformed canonical data is an actionable error. Never seed, repair, or overwrite it automatically.
- The API is read-only: `GET /api/budget` returns `{ document, revision }` (the SHA-256 of the file bytes) and other methods get `405`. The app never writes `data/project.json`. Edit it in Git. Keep the loopback host/address, 2 MiB file, and schema guards in both dev and preview.
- `GET /api/exchange-rate` returns the cached BNR EUR/RON reference rate (`{ ronPerEur, rateDate, source, sourceUrl, fetchedAt, stale }`) under the same loopback guards as `/api/budget`, refreshed from `.cache/exchange-rate.json` at most once every 7 days, falling back to the ECB reference rate when BNR is unreachable. The header shows this cached rate instead of a hardcoded value. Agents should read the endpoint rather than re-fetching BNR/ECB on every run.
- The API permits only direct HTTP loopback origins (`localhost`, `127.0.0.1`, `[::1]`). Do not trust other `.localhost` subdomains or forwarded headers to authorize origins.
- Use `BUDGET_DATA_FILE` only for server-side isolated test instances. Never accept a storage path from a request or expose it through a `VITE_` variable.
- Ship one budget, not a target. Follow the TBD, iterative budget policy in [`brief/project.md`](../brief/project.md) (`HH-03`) and do not reintroduce a fixed project target, cap, or over-budget warnings. Present the single `baseCents` estimate amount: there are no price scenarios, `amounts`/`rates` carry only `baseCents`, and the app shows no scenario controls or labels. Items, nested groups and category totals show the estimate-to-forecast range, where the forecast adds the eligible contingency. Equal ends collapse to one amount and cash flow uses the forecast.

  House costs include fees, construction and fixed systems. The land price is excluded and movable goods are reported separately. There is no price growth: estimates stay at today's prices whatever the instalment date.

  Contingency is fixed at 10 % (`CONTINGENCY_BPS`, not editable in the UI or the document), proportional and only over eligible future house base costs, excluding land, movables, actual payments and owned goods. The Ipoteze dialog is read-only and only explains these rules.

- An item's forecast cost is the sum of actual payments, the non-negative remainder of its instalments and an unallocated future amount when the estimate exceeds the ledger. Keep such differences visible for reconciliation. Archiving cancels only the future plan and keeps actual payments in totals.
- The cash-flow page shows monthly and cumulative needs. The header nav's Beneficiari page lists each beneficiary with its contact details, item count, cost range and payment progress, and a per-beneficiary detail view of its items. The budget table's Beneficiar column clicks through to the matching beneficiary (or the trailing "TBD" bundle for unassigned items).

- For isolated testing, copy a valid document into a temporary directory and start a separate instance with `BUDGET_DATA_FILE='/absolute/path/project.json' just dev --port 6175`. The API is active in both dev and preview.

- Extra (`extras` category, `extra` milestone) runs from June 2029 through June 2031 after the June 2029 move. Keep its items included within their own budget. Do not use `included: false` to separate stages. `selectBudgetView` defaults to `scope: "initial"`, with explicit `"extra"` and `"all"` scopes.

  The overview and default cash flow use the initial scope. Stage tables and beneficiaries include all stages, and Extra cash flow requires selecting that milestone. Preserve Extra furnishings in the brief and model. The schema requires all five milestones.
