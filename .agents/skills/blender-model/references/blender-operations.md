# Blender operations

Read this reference before you connect to Blender, run maintained scripts or recover from a failure.

Paths in this reference are relative to `model/` unless they start with `.agents/` or the repository root. The
[model guide](../../../../model/AGENTS.md) holds the invariants, and [the skill](../SKILL.md) the workflow and safety
rules.

## Navigate

`save` creates one scene per `scene_definitions` entry in `design/style.json` and names it after the entry's `name`
(for example `01 • Casa Exemplu | Grădină`). Select a scene, then use Numpad 0 for its camera. Scene variants share
geometry. Room floor objects carry stable `Room ID`, `Floor level` and area properties. Low and high wall collections
support the cutaways; site annotations live in `Site | Annotations` and per-level `<level> | Annotations`.

Use the existing cutaways and floor collection isolation first for geometry review. If materials or lighting obscure
wall joins, openings or intersections, inspect the viewport in Solid shading through Computer Use or MCP, then restore
the original shading, visibility and view. Hide obstructing collections temporarily rather than deleting geometry, and
do not save the diagnostic state.

## Sources and output

`design/` holds the editable house, furnishing, style and site parameters, `requirements.json` (the audit catalogue)
and `schema.json`. `engine/` compiles host-side geometry with Shapely; its native adapter applies precompiled
descriptors in Blender. `assets/` contains the reusable furniture/equipment/plant library (`catalog.json`,
`baseline-assets.blend`), material and world sources (`scene-manifest.json`) and the CC0 texture groups.

`engine/paths.py` names every checkout path and generated artifact. Scripts reach it through
`scripts/project_paths.py`, whose `load_engine_modules` imports fresh engine modules in the live Blender session.
`engine/persistence.py` owns JSON I/O, hashing and timestamps. `engine/blender_datablocks.py` owns the Blender
collection, property, light and library-append adapters. Reuse them instead of local copies.

The maintained `scripts/` are:

| Script                                 | Runs in | Entry point                   | Role                                                        |
| -------------------------------------- | ------- | ----------------------------- | ----------------------------------------------------------- |
| `run_blender_task_in_blender.py`       | Blender | MCP `execute_blender_code`    | Loads the checkout and dispatches `run_task`/`start_render` |
| `run_headless_in_blender.py`           | Blender | `just model-headless`         | Runs `new`, chained tasks and `render` in background        |
| `build_parcel_in_blender.py`           | Blender | `run_task('build'\|'update')` | Applies the compiled runtime bundle without saving          |
| `save_parcel_in_blender.py`            | Blender | `run_task('save')`            | Reconciles presentation links and saves the blend           |
| `present_parcel_in_blender.py`         | Blender | `run_task('present')`         | Restores the default camera view without saving (UI only)   |
| `export_parcel_geometry_in_blender.py` | Blender | `run_task('export-geometry')` | Exports evaluated geometry for the audit                    |
| `export_parcel_drawings_in_blender.py` | Blender | `run_task('export-drawings')` | Exports nominal sections for the PNG drawings               |
| `render_parcel_in_blender.py`          | Blender | `start_render`                | Renders the style-driven view queue                         |
| `parcel_render_output.py`              | Both    | imported                      | Rotates current/previous render and drawing sets            |
| `project_paths.py`                     | Both    | imported                      | Exposes `engine/paths.py` and fresh engine imports          |
| `audit_parcel.py`                      | Host    | `just parcel-audit`           | Audits the latest geometry export                           |
| `draw_parcel_plans.py`                 | Host    | `just parcel-drawings`        | Drafts the labeled architectural and structure PNGs         |
| `plan_sheet.py`                        | Host    | imported                      | Shared plan-sheet layout and drawing primitives             |
| `generate_wallpapers.py`               | Host    | `just model-wallpapers`       | Regenerates project-authored wallpaper and tile textures    |
| `fetch_polyhaven_asset.py`             | Host    | `just model-asset`            | Fetches a CC0 Poly Haven map or HDRI into `assets/<group>/` |

## Headless Blender

`just model-headless` runs the same runner in `blender -b`; set `BLENDER` when the executable is not on `PATH`.

1. `just model-headless new` saves an empty `model/house.blend` from a factory-startup session. It refuses to
   overwrite an existing blend.
2. `just model-compile`.
3. `just model-headless build save export-geometry export-drawings` runs the tasks in order against the saved blend.
4. `just model-headless render [--preview] [--engine eevee|cycles] [stem…]` renders the queue synchronously (background
   Blender never fires timers, so the queue runs before the call returns). `render` must come last when chained.
5. `just parcel-drawings`, `just parcel-audit` and `just render-check` then run on the host.

In background mode the runner tracks unsaved state itself, so read-only exports after `save` in the same call see
clean data. `present` needs the UI and has no headless use.

## Operate Blender through official MCP and Computer Use

Use the official Blender Lab server for scene facts and maintained-script execution, and native Computer Use for
visual inspection, installation, workspace and dialog interaction, render progress and observable recovery. Routine
work must not depend on a focused Python Console, typed snippets or clipboard pastes.

The supported server is [Blender Lab's `blender_mcp`](https://projects.blender.org/lab/blender_mcp), pinned to
`2cea8d566dde07fbac28a61d698909d69724e853` (release `v1.0.3`). Install it with
`uv tool install 'git+https://projects.blender.org/lab/blender_mcp.git@2cea8d566dde07fbac28a61d698909d69724e853#subdirectory=mcp'`.
It requires Blender 5.1 or later, and the server executable is `blender-mcp --transport=stdio`. Install and enable the
add-on built from that pinned source with Blender's native UI. Its endpoint is loopback-only (`127.0.0.1:9876`).
Configure `BLENDER_MCP_HOST`, `BLENDER_MCP_PORT` and, where needed, `BLENDER_PATH` for this host. The project
`.codex/config.toml` (Codex) and `.mcp.json` (Claude Code) pin the same server and loopback endpoint; keep them in sync
and never commit an absolute application path.

Useful tools include `execute_blender_code(code)` (returns `status` and `result` or `error`), window and editor
screenshots, object summaries, path information and tab navigation. Assign a JSON-compatible dictionary to `result` in
MCP code. `execute_blender_code_for_cli(blend_file, code)` has a 120-second background timeout and may save a dirty live
file to a temporary copy, so use an independent saved snapshot for on-disk proof.

Wait for a freshly opened file to settle and coordinate exclusive control of the Blender instance. Execute the
maintained helper from its absolute checkout path (replace `<checkout>`):

```json
{
  "code": "from pathlib import Path\nimport runpy\n\nscripts = Path('<checkout>/model/scripts')\nnamespace = runpy.run_path(str(scripts / 'run_blender_task_in_blender.py'))\nexpected_blend = str(scripts.parent / 'house.blend')\nresult = namespace['run_task']('build', expected_blend)"
}
```

Each MCP call loads the helper again; do not depend on variables left by an earlier call. `run_task` accepts `build`,
`update`, `save`, `export-geometry`, `export-drawings` and `present`. Read-only exports reject dirty Blender data, and
every task rejects a different open blend or missing declared outputs.

`start_render` accepts `preview`, optional nonempty `views` of render stems, an optional `engine` (`'eevee'`, the
default, or `'cycles'`) and an optional safe `run_id`. In the UI it schedules the queue on the main thread and returns
immediately with a receipt under `.generated/blender-workflow/`. One queue may be pending. The receipt moves from
`accepted` to `running`, then `complete`, `failed` or `cancelled`.

`just render-cancel` writes the `.generated/blender-workflow/cancel-render` sentinel, which the queue checks before each
view. The view in progress finishes, the images already written are kept and the run ends `cancelled` without a
`*-complete.json` marker. Accepting a new queue clears a stale sentinel.

After a timeout, disconnect or UI failure, inspect the receipt, live MCP state and, when needed, the native UI. Do not
replay a mutation, save or start another render until the state is known. Inspect semantic IDs and world matrices
before targeted changes; the house `transform` in `design/house.json` maps local plan coordinates to parcel
coordinates.

## Requested export work

The maintained workflow has no game-engine exporter. For an explicitly requested transfer, verify evaluated modifiers,
units and axes, instances and material approximations in the target, and check door pivots and collision there before
using free movement to review routes.
