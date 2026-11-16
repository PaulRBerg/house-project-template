# Repository Guidance

## Authority and evidence

- All brief, budget and model content in this repository is fictional demo content (the Casa Exemplu household, parcel
  and house). Replace it with the household's own facts before relying on it.
- Treat `brief/` as the sole semantic authority for household decisions. Treat `budget/data/project.json` as the
  operational authority for budget categories, estimates, inclusion, ownership/completion state, instalments, and
  payments. Preserve the brief's stable record IDs and five completion stages (`La roșu`, `La gri`, `La cheie`,
  `La mutat`, `Extra`). See [`brief/README.md`](brief/README.md). A stage states when the accepted result is complete,
  independently of its payment milestone or instalment dates. Budget brief references contain only `recordId`.
- Keep the house brief (`brief/*.md`), budget catalogue (`budget/data/project.json`) and Blender model
  (`model/house.blend` and its maintained sources) reconciled on acceptance: when a design, requirement or cost change
  is accepted, update the affected records, quantities and geometry across all three. They may lag each other across
  commits while work is in progress. The brief remains the semantic authority and the budget the operational authority
  for costs and budget state. A price, inclusion, budget-state or model change must never silently alter a household
  requirement.
- Base every dimensional, compliance and construction rule (clear room heights, stair geometry, minimum room areas,
  setbacks, height regime, fire, structural and services provisions) on Romanian legislation, normatives and standards
  through the [`romanian-building-code`](.agents/skills/romanian-building-code/SKILL.md) skill, never on generic construction guidance
  from other countries. Cite the Romanian source and its scope, and treat local urbanism limits as project-specific
  unknowns until the certificat de urbanism is issued.
- Write `brief/*.md` prose in fluent Romanian with appropriate Romanian architecture, construction, and building-services
  terminology. Keep stable IDs and the five literal completion-stage headings unchanged. Records in factual
  introductions may have no stage. All recorded directions are accepted, with real flexibility and unresolved checks
  stated in prose rather than encoded as decision status.
- Keep the records focused on current accepted decisions. When the household accepts a replacement decision, update
  the affected records in place and remove superseded alternatives unless history is explicitly requested.
- Distinguish household preferences from inspirations, laws or standards, specialist guidance, and project-specific
  unknowns. Do not invent or silently promote geometry, site conditions, performance, cost, compliance, or
  construction details.
- Treat every early design output as non-authoritative. The responsible professionals must validate the site, develop
  and coordinate the design, establish compliance and cost, obtain approvals, and produce construction information.
- Keep early model exploration simple: describe a change, inspect one or two relevant previews, then refine or accept.
  Nominal dimensions communicate intent. Use rounded concept measurements and review material drift in the 180 m² cap,
  2 m setback, programme or connections. Do not alter otherwise accepted geometry to erase sub-decimetre modelling
  differences, and do not turn routine previews into exhaustive review-record dumps.

## Change policy

- Backward compatibility is not a goal in this repository. Moving fast is. Rewrite, rename, restructure or delete any
  code, schema, script, recipe or guidance whenever the end state is simpler or better. Do not keep shims, deprecated
  aliases, fallback readers, legacy selectors or migration layers for old callers, and do not keep old names or
  signatures alive for callers you can update in the same change.
- Judge refactor, rewrite and design alternatives on end-state merit, not migration cost. Prefer the breaking
  refactor that simplifies the current code over an additive one that preserves an old shape.
- The only compatibility that matters is for checked-in data and active workflows. When a schema or format changes,
  migrate the checked-in inputs (`budget/data/project.json`, `model/design/*.json`, the brief and the blend) and the
  recipes that consume them in the same change instead of teaching readers to accept the old shape.
- Define each value, rule and helper once, in the module or data file that owns it, and make every consumer import or
  derive it instead of restating it. This covers constants, labels, paths, limits, class strings, schemas and test
  fixtures. Before adding a literal or helper, search for an existing owner. When logic or a value appears a second
  time, extract it rather than copy it. One source of truth lowers maintenance cost and prevents silent drift between
  copies.

## Verification

- Before committing engine or app code, run the narrowest test that covers what you changed and fix any failure you
  introduced: `just budget test-node <file>` or `just budget test-ui <file>` (or `just budget check` for typecheck plus
  the full suite) for `budget/src`, and `just model-tests` or a single pytest file for `model/engine` and
  `model/scripts`. Edits to `budget/data/project.json`, `brief/*.md`, `model/design/*.json` and the blend need no test
  run. `budget/src/data/catalogue.test.ts` checks only structural invariants of the catalogue and does not pin its
  contents. Run `just budget lint`, `just budget format-check` and `just budget build` on demand, not as a commit gate.
- Use `just budget test-agent [file]` for the same Vitest suite with token-efficient agent output. `just skill-check`
  audits `.agents/skills` with the optional `ai-skillet doctor` CLI and skips when it is not installed. `just full-check` chains Ox, Ruff, `just budget check` and
  `skill-check`. It builds no model and renders nothing, so it does not replace `just model-tests` for engine changes.
- The Husky pre-commit hook (`.husky/pre-commit`, installed by `just setup` after `bun install`) runs lint-staged over
  whole-file staged changes: Ox fixes and formatting for code and configuration, Prettier for Markdown and YAML, Ruff
  for Python, `skill-check` for staged skill files, ESLint and the typecheck for `budget/src`, the catalogue test for
  `budget/data/project.json` and `brief/*.md`, and the model suite for `model/` engine, script, test, design and asset
  changes. Partially staged files are rejected because the worktree is shared. Stage whole files.

## Design work

- Use [`household-brief`](.agents/skills/household-brief/SKILL.md) to interpret or update the household brief.
- Place every hinged interior door by brief `STY-02`: it opens into the room it serves, with the hinge on the jamb
  nearest the perpendicular wall so the open leaf folds back against that wall, never into the middle of the room or
  a circulation route. Set `hinge` and `swing_deg` in `model/design/house.json` accordingly and check the plan arcs.
- Use [`design-exploration`](.agents/skills/design-exploration/SKILL.md) for iterative rendered redesigns and user
  feedback before selecting a design. It owns the exploration output layout and review loop.
- Use [`concept-imagery`](.agents/skills/concept-imagery/SKILL.md) for photorealistic house concept images generated
  directly from the current brief and interior design guidelines.
- Use [`blender-model`](.agents/skills/blender-model/SKILL.md) to inspect, edit, render, or maintain
  [`model/house.blend`](model/house.blend), the parcel concept subordinate to the brief. The skill owns the edit,
  compile, build, save, preview and full-render workflow, the Blender safety rules and the render output layout;
  [`model/AGENTS.md`](model/AGENTS.md) owns the model invariants and exploration policy. Every task that changes the
  saved blend or the render or drawing pipeline ends with the complete render set from the final saved blend.
- Use [`building-science`](.agents/skills/building-science/SKILL.md) for healthy-home evidence (air, ventilation,
  filtration, humidity, materials, circadian light, sleep, acoustics, recovery, monitoring, operation) and
  high-performance evidence (envelope, airtightness, moisture, MVHR, heat pumps, PV, controls, commissioning, Casa
  Buhnici). Passive House is inspiration and benchmark only — the household contracts no voluntary certification
  (`SITE-08`).
- Use [`romanian-building-code`](.agents/skills/romanian-building-code/SKILL.md) whenever a task dimensions construction, rooms, clear
  heights, stairs, openings, furniture or equipment clearances, setbacks, height regime, or checks permits, nZEB or any
  other compliance rule. Every such rule is bound by Romanian legislation, normatives and the local urbanism of the project's locality, never
  by generic guidance from other countries.

## Budget planner

- Use [`price-estimator`](.agents/skills/price-estimator/SKILL.md) for current local price research across
  all budget categories, with comparable EUR estimates and direct sources for the project's house.
- `budget/` is the household's primary tool for categorization and budgeting. Its catalogue owns budget taxonomy and
  budget state, but is not a second authority for the household decisions referenced from the brief.
- Keep workspace checks and model recipes in the root `justfile`, and app recipes in the `budget/justfile` module.
  Keep all package manifests free of `scripts`. From the repository root, run `just budget <recipe>` for app tasks
  and `just <recipe>` for workspace/model tasks. Module recipes run in `budget/`. `just <recipe>` there remains valid,
  with unknown recipes falling back to the root. Use `just --list --list-submodules` to discover all tasks.
- Follow [`budget/AGENTS.md`](budget/AGENTS.md) for its schema, accounting, persistence, and validation rules.
- Use `just budget cost <add|delete|move|rename|set-price|split> ...` for single cost-item edits. Do not edit
  `budget/data/project.json` by hand for them.
