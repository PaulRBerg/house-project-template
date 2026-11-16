# Model guidance

[house.blend](house.blend) is the procedural, furnished parcel concept of the demo house _Casa Exemplu_. It uses native
editable geometry, procedural and CC0 image materials, and EEVEE by default (Cycles on request). It does not require
IFC. The [household brief](../brief/README.md) remains the authority for decisions. The maintained sources live in
`design/` (the house, furnishings, style, site and requirement JSON), `engine/`, `assets/` and `scripts/`. Replace the
demo by editing `design/*.json` and the brief; the engine holds no house-specific IDs or values.

Use the [`blender-model`](../.agents/skills/blender-model/SKILL.md) skill for every model task. It owns the edit,
compile, build, save, preview and full-render workflow (through MCP or headless Blender), the Blender safety rules, the
render output layout and the completion checks, and it lists the references to read for each kind of task.

## Construction material intent

The brief requires ceramic brick for the exterior and primary walls (`SITE-04`) inside a reinforced-concrete frame
(`SITE-05`). BCA is not a substitute for those elements; it may appear only in secondary elements that the coordinated
project identifies and verifies. The model is concept geometry and does not prove the final structural assembly,
thicknesses, performance or compliance.

## Exploration policy

House and room areas, dimensions, proportions and plan shapes are open to exploration under `LAY-06`. Measurements in
the references describe the current variant, not targets or limits, except for these accepted rules:

- The house, including facade finishes, stays within the 180 m² gross-area cap (`LAY-06`, `requirements.json`
  `gross_area`).
- Every level keeps the 2.55 m finished clear height, with every room a single storey high (`LAY-07`).
- The house, terrace and roof projections stay inside the 2 m concept setback from every parcel limit (`SITE-02`).
  Fences, gates, access paving and the parking space may reach the boundary.
- The programme and connection graph of `LAY-01` hold: every room is reached from `G-HALL` or `U-LOBBY` (the kitchen
  through the open link from `G-LIV`) without crossing another occupied room.

When another variant becomes the working basis, reconcile the affected brief records and budget quantities. Geometry
audits use semantic IDs and independently exported evaluated meshes. Do not rebuild accepted geometry for
sub-decimetre parity or expose the complete internal review list in an everyday preview.

## Invariants

- The brief is the authority for decisions. The model is concept evidence, not professional approval.
- `design/requirements.json` cites only brief records that exist; the compiler rejects unknown IDs.
- The demo parcel is fictional and unsurveyed (`SITE-01`). Replace its polygon with surveyed corners before any siting
  decision. Infer no solar orientation; `parcel.grid_north_deg` stays absent until a survey supplies it.
- Furnishing assemblies live in their declared collections, never directly in scene roots.
- Keep scene fake users enabled so unused variants survive saving.
- Reuse `engine/paths.py`, `engine/persistence.py` and `engine/blender_datablocks.py` instead of local copies.
- Add CC0 Poly Haven maps or skies with `just model-asset <exterior|interior> <id> [resolution]`. It downloads into
  `assets/<group>/`, verifies the published MD5 and records the entry in that group's `sources.json`.
- Keep `.codex/config.toml` and `.mcp.json` in sync. Do not commit an absolute `BLENDER_PATH`.
- Keep the canonical blend, sources and guidance tracked. Do not blanket-purge `.generated/`.

## Coordination still required

The floor-face, doorway and arrival-route checks do not certify useful area, complete furniture clearance, stair
headroom, structure, acoustics, building services, fire safety or code compliance. Dimensional proxies represent
equipment. Roof drainage, external shading and PV layout depend on the survey, climate analysis and engineering.

`stair:np057:<stair>` checks the NP 057-02 relation, `corridor:legea114:<room>` the 1.20 m Legea 114/1996 circulation
reference (`LAY-05`) from evaluated floor faces minus columns and low furnishings, and `bath-access:legea114:U-BATH`
reports the review-only bathtub approach (`RM-UBATH-01`). Read measured values and review flags from the
`just parcel-audit` report, not from this guide. The architect verifies finished dimensions.
