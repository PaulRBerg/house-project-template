# Site, exterior and outdoor scopes

Read this reference before you edit the parcel, setback, site components, roofs or facade finishes.

Paths in this reference are relative to `model/` unless they start with `.agents/` or the repository root. The
[model guide](../../../../model/AGENTS.md) holds the invariants, and [the skill](../SKILL.md) the workflow and safety
rules.

## Parcel and area

`design/house.json` `parcel` holds `id`, the `polygon` in parcel metres, `reported_area_m2`, `side_lengths_m` and the
`vehicle_access_edge` (corner numbers). Optional `ground_material_id` adds a `Parcel / ground` mesh over the outer
polygon in `00 | Site & landscape`; optional `setback_material_id` draws a flat outline at the `setback.minimum_m` inset
in `Site | Annotations`. Optional `parcel_number`, `site_pin_lat_lon` and `grid_north_deg` record survey data;
`grid_north_deg` adds the drawing compass.

The demo parcel (`SITE-01`) is a fictional, unsurveyed 24 × 40 m rectangle (960 m²) with corners 1–2–3–4 and the
street on edge 1–2. It carries no coordinates, cadastral number or orientation. The house sits back from the street
with the garden behind it; its exact position is a concept choice.

| Quantity                        | Source                                      | Demo value |
| ------------------------------- | ------------------------------------------- | ---------: |
| Parcel area                     | `compiled.quantities.parcel_area_m2`        |     960 m² |
| Gross area, wall-body envelope  | `design_quantities` (both levels)           |    ~160 m² |
| Gross-area cap incl. finishes   | `requirements.json` `gross_area` (`LAY-06`) |     180 m² |
| Concept setback from all limits | `requirements.json` `setback` (`SITE-02`)   |        2 m |

The finished gross area and the setback are proven only from evaluated meshes: run `export-geometry` and
`just parcel-audit`. Facade skins count in the gross envelope. The house, terrace and roof projections stay inside the
2 m inset; fences, gates, access paving and the parking space may reach the boundary. Legal setbacks, POT/CUT and the
height regime remain unknown until the certificat de urbanism (see `romanian-building-code`).

## Site components

`design/site.json` `site_components` declares every outdoor element with an `id`, a `purpose`, a collection and either
`parts` (`box`, `prism` or `generated` kit specs from the `FIXTURES`/`TEMPLATES` registries) or an `asset_id` from the
library with matching `dimensions`. `requirements.json` `required_site_components` maps brief records to the purposes
that must be present. The demo provides:

- Lawn and a few trees and shrubs (`GAR-01`), a narrow perimeter walkway (`GAR-02`).
- An uncovered paved terrace with a dining table, six chairs and a planter by the living room (`GAR-03`).
- Paved access, one open parking space with a vehicle proxy and a pedestrian path (`GAR-04`, `SITE-07`).
- Perimeter fence, pedestrian gate and vehicle gate on the street edge (`GAR-05`).
- The heat-pump outdoor unit (`EN-03`).

There are no outbuildings, covered parking or water features. Plant and equipment proxies are dimensional
placeholders, not species or product selections.

## Roof

`roofs[]` declares warm flat roof areas with a `polygon`, `base_z_m`, `deck_z_m`, `pitch_deg`, `slope_direction` and
optional `pv` arrays and `trims` (parapet copings). The demo has two 1° membrane roof fields (`roof-east`, `roof-west`,
about 40 m² each) falling to a central gutter behind level parapets (`SITE-06`), each with a 4 × 2 PV array: 16
modules, matching `requirements.json` `pv_modules` (`EN-07`). Falls, outlets, insulation, ballast and loads are design
work.

## Facade

Each exterior wall's `finish` sets its cladding and `engine/facade_finishes.py` builds it. `design/schema.json`
defines the keys in `$defs.wall` (`finish`), `$defs.ledgestone` and `$defs.opening` (`reveal`):

- `style` is `plain` (one flush skin in `material_id`) or `ledgestone` (thin seeded stones over a backing; requires
  `stone` with `material_ids`, `course_heights_m`, `length_range_m` and optional `joint_m`, `depth_m`, `proud_m`,
  `seed`).
- `bands` are flush sheets over a `z_m` range, optionally limited by `span_m`; they stop at openings.
- `panels` are accent panels over `span_m`, with optional `pitch_m`/`width_m` slats and `z_span_m`.
- `extend_top_m` raises the cladding over the slab edge or parapet: a number, or a list of `{span_m, height_m}`.
- An opening `reveal` sets a lined frame recess (`lining_material_id`, `depth_m`) with optional `surround_m`,
  `surround_material_id`, `pitch_m` and `width_m`.

The demo uses plain white render on every exterior wall with a plinth band on the ground floor and the cladding
extended over the slab edge and parapet. Windows are triple-glazed concept openings; several carry concealed exterior
venetian blinds (`SITE-09`).

## Materials and landscape assets

`assets/exterior/sources.json` and `assets/interior/sources.json` record the installed CC0 maps and HDRI skies with
source links and checksums. `just model-asset exterior <id> [2k]` fetches a further Poly Haven texture or HDRI.
`engine/surface_materials.py` builds metre-scaled shaders from the `surface` entries in `design/style.json`. They are
visual references, not specified construction products. Exterior glazing uses a blended EEVEE material so interiors
read through it; this does not change glazing performance.

Structural spans, thermal interfaces, waterproofing, drainage and thresholds require coordinated Romanian design.
