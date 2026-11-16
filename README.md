# House Project Template

A local-first starter for planning a house build in Romania. It keeps three linked records of one project, plus the
agent skills and tooling to maintain them:

- a Romanian-language **household brief** of accepted decisions (`brief/`);
- a local EUR **budget planner** with cost hierarchy, calendar, cash flow and payments (`budget/`);
- a procedural **Blender house model** with plans, cutaways and renders (`model/`).

Agents (Claude Code, Codex) work on all three through the project skills in `.agents/skills` and a Blender MCP server.

## Demo content

Everything in `brief/`, `budget/data/project.json` and `model/` is **fictional demo content**: the household (two
adults and a school-age child), the 960 m² parcel and Casa Exemplu, a P+1 house of about 160 m² in Comuna Exemplu.
Nothing is surveyed, quoted or priced from real offers. Replace it with your own household, site and numbers; the
structure, schemas, engine and workflows are the reusable part.

The records support early reasoning and later communication with an architect-led design team. They are not a surveyed
site model, approved design, legal or energy assessment, cost plan, specification, or construction package.

## Prerequisites

- [Bun](https://bun.sh) 1.4 or later (see `packageManager` in [`package.json`](package.json))
- [just](https://github.com/casey/just)
- [uv](https://docs.astral.sh/uv/) with Python 3.13, for the model engine and its tests
- [Blender](https://www.blender.org) with [Blender Lab's MCP add-on](https://projects.blender.org/lab/blender_mcp), to
  open, edit and render `model/house.blend`
- Optional: `ai-skillet`, a CLI that `just skill-check` uses to audit the skills; the recipe skips when it is missing

## Quick start

```sh
bun install
just setup          # installs the Husky Git hooks
just budget dev     # budget planner at http://127.0.0.1:8437
```

Run `just --list --list-submodules` for every task.

## The three records

**Brief.** The Markdown records in [`brief/`](brief/) are the semantic authority for household decisions. They keep
stable record IDs and five completion stages: `La roșu` (structure and envelope), `La gri` (concealed routes and
preparations), `La cheie` (installed, commissioned systems and finishes), `La mutat` (movable goods at move-in) and
`Extra` (commitments completed after move-in). See the [brief conventions](brief/README.md).
[`DIAGRAM.md`](DIAGRAM.md) shows the room relationships and [`GLOSSARY.md`](GLOSSARY.md) explains specialist terms.

**Budget.** [`budget/`](budget/) serves the catalogue in `budget/data/project.json` through a read-only app on
`127.0.0.1:8437`. The catalogue is the operational authority for categories, estimates, inclusion, ownership,
instalments and payments, and references brief records only by `recordId`. Edit single cost items with
`just budget cost <add|delete|move|rename|set-price|split> ...`. See [`budget/AGENTS.md`](budget/AGENTS.md).

**Model.** [`model/house.blend`](model/house.blend) is generated from the maintained JSON designs in `model/design/`
and the Python engine in `model/engine/`. It is concept evidence subordinate to the brief. Renders and backups stay
local and ignored. The [model guide](model/AGENTS.md) covers the edit loop, invariants and safety rules.

Agents normally drive a live Blender through the MCP server. Without it, rebuild and render headlessly by pointing
`BLENDER` at the Blender binary:

```sh
export BLENDER=/Applications/Blender.app/Contents/MacOS/Blender   # macOS example
just model-compile
just model-headless build save export-geometry export-drawings
just model-headless render          # add --preview for the first four views
just parcel-drawings
```

When a design, requirement or cost change is accepted, update the affected records across all three. The brief stays
the semantic authority and the budget the operational authority for costs.

## Agent setup

[`AGENTS.md`](AGENTS.md) holds the repository rules for coding agents. The Blender Lab MCP server is configured for
Claude Code in [`.mcp.json`](.mcp.json) and for Codex in [`.codex/config.toml`](.codex/config.toml); keep the two in
sync. Start Blender with the MCP add-on connected before asking an agent to inspect or edit the model.

Project skills live in [`.agents/skills`](.agents/skills) and are linked into Claude Code from
[`.claude/skills`](.claude/skills):

- `household-brief`: read and update the brief;
- `blender-model`: inspect, edit and render the Blender model;
- `design-exploration` and `concept-imagery`: rendered alternatives and concept images from the brief;
- `building-science`: healthy-home and high-performance evidence, with Passive House as a benchmark only;
- `romanian-building-code`: Romanian legislation, normatives and standards for every dimensional or compliance rule;
- `price-estimator`: current EUR price research with sources.

## Checks

- `just full-check`: Ox, Ruff, the budget typecheck and tests, and the skill audit. It builds no model.
- `just model-tests`: the host-side model engine suite.
- `just budget check`, `just budget lint`, `just budget format-check`: the budget app.

The Husky pre-commit hook runs lint-staged ([`.lintstagedrc.mjs`](.lintstagedrc.mjs)) over whole-file staged changes
and rejects partially staged files. Shared `@prb/devkit` presets provide the base Prettier, TypeScript and Vitest
configuration.

## License

[MIT](LICENSE.md)
