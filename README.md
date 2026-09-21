# House Project Template

Private, local-first starter records for planning a house project. Replace every demo record before treating it as a decision, estimate, drawing, or construction information.

## Start here

Install Bun (the version in `package.json`) and `just` for the budget app. Blender 5.2 was used to save and verify the sample model. The optional agent connection also needs `uv` and Blender Lab's matching MCP add-on; follow the [model setup guide](model/AGENTS.md).

```sh
bun install
just --justfile budget/justfile dev
```

The budget app is available at `http://127.0.0.1:5173`. Open `model/house.blend` in Blender for the deliberately simple demo shell.

The project has three linked records:

- [`brief/`](brief/README.md) is the semantic authority for accepted household decisions.
- [`budget/data/project.json`](budget/data/project.json) is the operational authority for budget categories, estimates, inclusion, ownership, completion, instalments, and payments.
- `model/house.blend` is the current geometric expression of the accepted brief; its demo is a single-storey 8 m × 6 m external shell (48 m²), not a design proposal.

Replace the fictional, unaccepted demo rows with your own decisions and evidence. Keep affected requirements, quantities, and model geometry reconciled in one change when a decision changes. A pure price, inclusion, or accounting-state change does not require an irrelevant geometry edit.

The app is local only. Project assumptions are editable in the app; the cost catalogue is currently edited through `budget/data/project.json` or an agent, because item editing in the UI is read-only.

Keep the four Romanian stage names: **La roșu → La gri → La cheie → La mutat**. The [budget guide](budget/README.md) describes the data and persistence; the [brief conventions](brief/README.md) explain decision records. The general budget interface retains Romanian text.

Read [AGENTS.md](AGENTS.md) before editing. Task recipes live in `budget/justfile`; package manifests must remain free of `scripts`. Validate with:

```sh
just --justfile budget/justfile check
just --justfile budget/justfile blender-workflow-tests
```

Code, documentation, and the demonstration model are provided under the [MIT license](LICENSE.md).
