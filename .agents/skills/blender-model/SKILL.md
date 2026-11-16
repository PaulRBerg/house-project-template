---
name: blender-model
skill-dependencies:
  - household-brief
  - romanian-building-code
description:
  Inspect, edit, render, or maintain the house Blender model through Blender Lab's official MCP server, native Computer
  Use or headless Blender recipes. Keep the maintained JSON sources and the saved blend aligned.
---

# Blender Model

Use this skill for `model/house.blend`, the maintained parcel scripts, its renders, drawings or geometry audits.
Read the [model guide](../../../model/AGENTS.md) before acting. It holds the invariants, material intent and
exploration policy. This skill owns the workflow, Blender safety rules and output layout. Then read only the
references that the task needs:

- [Blender operations](references/blender-operations.md): scenes, script inventory, MCP and headless setup, the helper
  call and recovery.
- [Render and drawing output](references/render.md): engines, quality profiles, the style-driven view queue,
  lighting, output layout, PNG drawings and cleanup.
- [House layout and rooms](references/house-layout.md): the house overview, storey heights, both floors and the stair.
- [Site, exterior and outdoor scopes](references/site-exterior.md): parcel, areas, setback, site components, roof and
  facade.
- [Interior design](references/interior-design.md): wall finishes, furnishings, curtains and interior doors.
- [Services scope and budget stages](references/programme-budget.md): services, PV and budget-linked quantities.
- [Structural frame](references/structure.md): the concept frame and its enforced minima.

## Route work deliberately

- Interactive work uses Blender Lab's official MCP for scene/path/dirty-state facts and to execute maintained scripts.
  Load the checkout's `run_blender_task_in_blender.py` helper by absolute path, then call
  `run_task(task, expected_blend, options=None)` or `start_render(expected_blend, options=None)` through
  `execute_blender_code`.
- Unattended work uses `just model-headless …`, which runs the same helper in background Blender. Set `BLENDER` to the
  executable when it is not on `PATH` (for example `/Applications/Blender.app/Contents/MacOS/Blender`). Do not run a
  headless task against a blend that an interactive Blender instance has open.
- Use native Computer Use for visual review, Blender preference/add-on UI, dialogs, render progress and observable
  recovery. Use MCP screenshots where they answer the visual question directly.
- Do not use routine Python Console, keyboard or clipboard injection. Shell commands run independent Shapely/PNG checks;
  they do not control a live Blender.

## Workflow

Paths in this section are relative to `model/`, and recipes run from the repository root.

1. Before an interactive mutation, confirm through MCP which blend is open, whether it is dirty and which scene is
   active. One Blender instance owns the file. For a first model, `just model-headless new` saves an empty
   `house.blend` (it refuses to overwrite one).
2. Edit `design/*.json` for house, furnishing, style, site and requirement parameters. Edit `engine/` or `assets/` only
   when the change needs new geometry logic or library entries, then run `just model-tests` (or one pytest file). JSON
   edits need no test run. For layout changes, first inspect connections and circulation in the existing plans or
   furnished cutaways and resolve unintended passage through rooms, blocked openings or conflicting routes in the
   sources before detailed furnishing.
3. Run `just model-compile`. It validates the design against `design/schema.json`, the brief and the requirements,
   writes `.generated/runtime.json` and reports `fresh`, `incremental`, `material-only` or `noop`. Then run `build`
   for a fresh build or `update` to apply the compiled change set to an open blend that was saved after the previous
   compile; when in doubt, use `build`.
4. Run `save`. It relinks furniture, applies the scene definitions and saves. Saved-file exports and renders require
   clean data. Headless, one call chains the steps:
   `just model-headless build save export-geometry export-drawings`. While iterating, render one or two relevant
   views as a preview (`start_render(expected_blend, {'preview': True, 'views': [...]})` or
   `just model-headless render --preview <stem>…`) and inspect them in `renders/current/`. EEVEE is the default; add
   `'engine': 'cycles'` or `--engine cycles` only when the user asks for Cycles.
5. Optionally run `export-geometry` from the clean saved file and `just parcel-audit` to check programme, connections,
   furnishing placement, envelope, heights, the gross-area cap and the setback from evaluated meshes.
   `run_task('present', expected_blend)` returns an interactive session to the default camera without saving.
6. Before finishing any task that changed the saved blend or the render or drawing pipeline, regenerate everything from
   the final saved blend: a full render with no `views` or `preview` (`start_render(expected_blend)` or
   `just model-headless render`), then `export-drawings` and `just parcel-drawings`. Never finish on a preview or a
   selected-view set.
7. To stop a running queue, run `just render-cancel`. It stops before the next view and records `cancelled`. MCP
   cannot reach Blender while it renders. Never use MCP or keyboard injection to cancel.
8. After a timeout, lost connection or failed UI action, inspect the receipt, MCP state and native UI before repeating
   an edit, save or render. A timed-out mutation or render is uncertain until inspected.
9. When the change is accepted, reconcile affected brief decisions and budget quantities. They may lag across commits.

Use rounded concept measurements. Note small mesh drift only when it materially changes the gross-area cap, the
setback, the programme or the connections. For dimensional checks (clear heights, stair geometry, circulation widths,
setbacks and height regime) cite the Romanian sources through `romanian-building-code`. The 2 m setback is a household
decision (`SITE-02`); the 2.55 m clear height (`LAY-07`) matches the habitable-room minimum. Treat the height regime,
POT/CUT and legal setbacks as unknown until a certificat de urbanism is issued.

The review practices adapt
[Architectural visualization with Astra](https://developers.openai.com/blog/architectural-visualization-with-astra)
to this project's maintained workflow.

## Outputs and boundaries

- Keep the latest PNG images in `model/renders/current/` and only the most recent previous generation directly in
  `model/renders/previous/`, each with `plans/`, `exteriors/` and `interiors/`. Do not create `2d/`, `3d/` or
  timestamped subfolders. Saving a changed blend or replacing a render set archives the current outputs and removes
  older previous sets. Run `just render-check` after a render or a cleanup.
- `design/style.json` cameras own the view queue, scene definitions and delivery filenames; `engine/render_inventory.py`
  owns the quality profiles and lighting. [Render and drawing output](references/render.md) lists the current views.
  Use Romanian delivery filenames without diacritics, and isolate every floor view to its own level.
- Cycles renders go to one flat `model/renders-cycles/` set with the same category folders and filenames, overwritten
  in place. The end-of-task full set is always EEVEE.
- Generated imagery and geometry checks remain concept evidence, not professional approval.

## Completion

Before reporting, verify these outcomes from tool results:

- The expected blend is saved and clean, with the `save` receipt for a mutation (MCP state or headless output).
- A changed blend or pipeline has the full end-of-task EEVEE render set and regenerated drawings from the final saved
  blend, never a preview or selected views.
- `just render-check` passes after the last render.
- The affected brief and budget records are reconciled or their lag is stated.
- Any Romanian-source dimensional claim cites `romanian-building-code`.

Report the blend path and state, the task and render receipts, and the output paths inspected. Report any audit
result, remaining discrepancy or unavailable tool. If the Blender connection is lost or UI recovery fails, report a
blocker, not completion. Describe the imagery and geometry as concept evidence, not approval.
