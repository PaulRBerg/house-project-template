# Render and drawing output

Read this reference before you render, export drawings or clean up render output. Run `just render-check` after a
render or a cleanup. It fails when `model/renders/` holds more than `current/` and one flat `previous/` set.

Paths in this reference are relative to `model/` unless they start with `.agents/` or the repository root. The
[model guide](../../../../model/AGENTS.md) holds the invariants, and [the skill](../SKILL.md) the workflow and safety
rules.

## View queue

`design/style.json` owns the queue. Each camera declares `render_jobs` (`stem`, `category`, `scene_id`, `filename`,
optional `default: true`) and `scene_definitions` (`id`, `name`, `camera_id`, `cutaway` `none`|`plan`|`section`,
`level_id` for floor views, optional `world_id`, `interior`, `evening`, `view_transform`, `look`, `exposure`,
`white_balance_temperature`, `excluded_collections`). `engine/render_inventory.render_views` derives the queue in
camera order, then job order. The flagged default job opens the saved file and `present`; a preview renders the first
four jobs. To add or rename a view, edit the camera in `style.json`; no engine change is needed.

The current demo queue:

| Stem             | Category    | Filename                   | Scene                                             |
| ---------------- | ----------- | -------------------------- | ------------------------------------------------- |
| `garden`         | `exteriors` | `Gradina.png`              | Garden view of the house and grounds (default)    |
| `evening`        | `exteriors` | `Seara.png`                | Same camera, evening sky                          |
| `arrival`        | `exteriors` | `Sosire din strada.png`    | Arrival from the street gate                      |
| `site-plan`      | `exteriors` | `Plan parcela.png`         | Overhead parcel plan with the 2 m setback outline |
| `ground-plan`    | `plans`     | `Plan parter.png`          | Ground-floor overhead plan                        |
| `ground-cutaway` | `plans`     | `Sectiune parter.png`      | Furnished ground-floor cutaway                    |
| `upper-plan`     | `plans`     | `Plan etaj.png`            | Upper-floor overhead plan                         |
| `upper-cutaway`  | `plans`     | `Sectiune etaj.png`        | Furnished upper-floor cutaway                     |
| `living`         | `interiors` | `Living.png`               | Living and dining at eye level                    |
| `kitchen`        | `interiors` | `Bucatarie.png`            | Kitchen                                           |
| `office`         | `interiors` | `Birou.png`                | Office / guest room                               |
| `main-bedroom`   | `interiors` | `Dormitor matrimonial.png` | Main bedroom                                      |
| `child-room`     | `interiors` | `Camera copilului.png`     | Child's room                                      |
| `upper-bathroom` | `interiors` | `Baie etaj.png`            | Upper bathroom                                    |

Interior cameras stand about 1.4 m above the floor in a room corner, looking diagonally across the room with 14 mm
lenses and nearly level, so verticals stay straight; an optional `shift_y` on the camera favours the floor and furniture.
Architectural comparisons keep sharp focus, straight verticals and comparable camera position and field of view.
`apply_presentation` disables depth of field for the maintained cameras.

## Render

Use `start_render` through MCP, or `just model-headless render`, after saving the intended clean model. EEVEE output is
always `model/renders/current/`, and only the most recent previous generation is kept in `model/renders/previous/`.
Pass `'engine': 'cycles'` (or `--engine cycles`) for path-traced images on request; Cycles writes one flat set to
`model/renders-cycles/` with the same folders and filenames, overwriting files without rotation.

`QUALITY_PROFILES` in `engine/render_inventory.py` set the sizes: EEVEE final 1800 × 1200 at 32 samples, preview
900 × 600 at 16; Cycles final 3600 × 2400 at up to 256 adaptive denoised samples, preview 1200 × 800 at 128. Cycles is
much slower; use it for selected delivery images, never the iteration loop or the end-of-task set. Images use AgX.
`EEVEE_LIGHTING` holds two profiles: exteriors and interiors use `gi` (screen-traced reflections and fast GI), plans
and cutaways use `studio`. Shadow maps render at `SHADOW_RESOLUTION_SCALE` 0.75 so fixture shadows fit EEVEE's pool.
Mirror-finished furnishings get plane reflection probes during build, update and save.

The render script reads `PARCEL_PREVIEW`, `PARCEL_ENGINE` and `PARCEL_VIEWS` (exact stems) from the runner options.

## Lighting and worlds

A world in `style.json` may carry an `environment` (`map`, `rotation_deg` and optional `sun` with `threshold`,
`angle_deg`, `shadow_resolution_m`, `texture_azimuth_deg`, `elevation_deg`). `engine/materials.py` builds an HDRI
node tree and EEVEE extracts the map's sun as a shadowing light. `world-daylight` and `world-interior-daylight` use
the CC0 `kloofendal_48d_partly_cloudy_puresky_2k.hdr`, `world-evening` uses `belfast_sunset_puresky_2k.hdr`.
`world-interior-daylight` must record its sun position: `sun_rotations` aligns the temporary interior key sun with it
so interior sunlight agrees with the sky in the windows.

`render_inventory.py` owns the temporary sun energies: zero for exteriors (the HDRI sun casts shadows), a faint fill
for evening, studio values for plans and cutaways, and `INTERIOR_PRESENTATION` per engine for interior exposure, white
balance and key/fill. A scene definition may override `exposure` and `white_balance_temperature`. The queue restores
the original world and settings after each view. These lights illustrate the concept, not surveyed sunlight.

When diagnosing lighting, relate highlights and shadows to the visible windows and fixture geometry before changing the
accepted palette.

## Floor views and cutaways

Each floor plan and cutaway shows only its own level: its scene's `excluded_collections` list the other level,
roof, site and exterior collections. `engine/floor_view_graphics.py` places compact Romanian room
labels with measured square metres from actual floor faces without overlaps, and adds temporary pale glazing symbols at
the section plane for every window and glazed opening; the renderer removes them after the view. Cutaways use an
off-white backdrop, warm-white wall bodies, grey section caps and pale label cards, and temporarily hide curtains and
wall pieces flagged `cutaway_hidden` above the 1.05 m cutaway line. These presentation conventions do not change the
design. Furnishing assemblies must live in their declared collections so floor exclusions apply. Exterior and interior
scenes exclude `Site | Annotations` and the per-level annotation collections.

## Output layout

Each set holds:

- `plans/`: overhead floor renders, furnished cutaways and the black-on-white architectural and structure PNGs.
- `exteriors/`: house, arrival, evening and site-plan views.
- `interiors/`: eye-level room views.

Delivery filenames use concise Romanian title case with spaces and no diacritics. Every render invocation archives an
existing set before writing a replacement in `current/`, so selected and preview sets are for iteration only. The
current `preview-log.json`/`final-log.json` and matching `*-complete.json` live in `current/`; a failed batch leaves a
partial log without a success marker. Each set's `source-blend.json` names the saved blend it came from, so saving a
changed model archives the current set on the next output. The queue restores the settings and active scene it found
and does not save the blend.

## Architectural drawings

Run `export-drawings` from the clean saved blend, then `just parcel-drawings`. The exporter writes
`.generated/drawing-geometry.json`; the Pillow renderer draws `Plan arhitectural parter.png`,
`Plan arhitectural etaj.png`, `Plan structura parter.png` and `Plan structura etaj.png` as 4800 × 2800 PNG (about A3 at
290 dpi), titled with the design `name`. The architectural sheets show room labels and areas, exterior dimension
chains, interior wall-face lengths, door arcs measured from leaf geometry, a stair travel arrow (`SUS`/`JOS`), joinery
codes (`UF` terrace glazing, `F` windows, `U` doors) and a side column with the conventional-area table (STAS 4908-85
terms, as concept values), the joinery schedule, a legend and a structure note. A compass appears only when
`parcel.grid_north_deg` is set. The structure sheets show columns with marks, labelled beams, the axis grid and
schedules. Shared layout lives in `scripts/plan_sheet.py` and needs Arial or DejaVu Sans for Romanian labels. Do not
generate SVG plans. These are concept drawings, not construction documents.

## Retention and cleanup

Keep the canonical blend, the maintained scripts, design JSON and current export and audit evidence. Automatic
`.blend1` saves, `__pycache__/`, superseded backups and one-off `.generated/` scripts are cleanup candidates. Rotation
removes older render sets. Review references before deleting anything else, and do not blanket-purge `.generated/`.
For an explicitly requested camera film, establish the animation pipeline and preview representative frames before
rendering every frame.
