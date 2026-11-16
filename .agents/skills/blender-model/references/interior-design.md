# Interior design

Read this reference before you edit wall finishes, procedural furnishings, curtains or interior doors.

Paths in this reference are relative to `model/` unless they start with `.agents/` or the repository root. The
[model guide](../../../../model/AGENTS.md) holds the invariants, and [the skill](../SKILL.md) the workflow and safety
rules.

## Palette

The demo follows the brief's warm, calm interior language (`STY-06`, `STY-08`, `STY-09`): a warm base colour per room
with at most one stronger accent wall and warm-white ceilings (`STY-01`), light natural oak floors in dry rooms
(`STY-03`), matte warm bathroom tiles (`STY-04`) and oak joinery with linen and wool textiles. Review texture scale,
grain direction, roughness and edges at viewing distance, and correct shading defects in the owning material or
template rather than compensating with lighting.

## Wall finishes

A room's `wall_finish` in `design/house.json` sets `material_id`, an optional `wainscot` and per-wall `accents`
(`wall_id`, `material_id`, optional `span_m`). `engine/architectural_details.py` builds 2 mm skins just inside every
wall face that bounds the room's floor, cut at openings and split at the 1.05 m cutaway line into
`<level> | Wall finishes low/high`. An accent must sit on a wall that bounds its room. The demo uses oat halls,
bathrooms and stair, cream living, kitchen and child's room, sand office and greige bedroom and technical room, with
accents on the living stair wall (sage), office rear wall (dusty blue), bedroom bed wall (terracotta limewash, spanned)
and child's room bed wall (sage). Finish materials use `"coordinates": "object"` because every skin carries the
house-to-world transform.

## Procedural furnishings

`design/furnishings.json` items with `generated` select a template by `kind`:

- `TEMPLATES` in `engine/furniture_kit.py`: joinery, worktops and shelving, with seating in `seating_kit.py` and
  tables, beds, rugs, curtains and panels in `bed_table_kit.py`.
- `FIXTURES` in `engine/fixture_kit.py`: mirrors, sanitary fittings, art and decor, with lamps, LED lines and downlights
  in `lighting_kit.py` and plants in `plant_kit.py`.

Style parameters select variants: `joinery` `fluted` reeds the fronts; `panel` `style: "flutes"` or `"slats"` with
`backing_role`; `chair` `style: "shell"`; `bench` `style: "slats"`; `floor_lamp` `style: "lantern"`; a `sofa` pillow's
`forward` layers the cushions. Templates use `engine/kit_geometry.py` and `engine/kit_parts.py`, emit one mesh per
material role (`ROLE_MATERIALS` in `engine/furnishings.py`, so `style.json` must define those material IDs), and
fixtures carry real Blender lights at 2700–3000 K. Artwork uses `frame_role: "frame"`. `cutaway_hidden` hides tall
pieces in the furnished cutaways. Library items use `asset_id` from `assets/catalog.json`, and their `dimensions` must
match the catalogue entry.

`assets/interior/sources.json` records the CC0 texture maps. `just model-asset interior <id> [1k]` fetches another,
and `just model-wallpapers` regenerates the project-authored wallpaper, mural and tile PNGs.

## Curtains

Bedrooms get full-height blackout curtains on ceiling tracks and the living and office warm-white sheers (`STY-05`).
The demo hangs them in the living room, the main bedroom and the child's room. A `curtain` may add
`params.pocket.depth_m` to draw a recessed ceiling pocket over its envelope (with tracks and a pocket LED);
`architecture` cuts that footprint out of the level ceiling, so clear heights are unchanged. `roller` adds a concealed
blackout roller cassette. Layer 0 is on the local −Y (glass) side.

## Interior doors

`door_style` is one of `flush-concealed` (frameless flush leaf with shadow reveals and a slim lever),
`standard` (white leaf with frame and casings), `sliding-pocket` (with `slide_direction`; the leaf parks inside the
partition and the plan draws a travel arrow) or `flush-entry` for the main entrance. The demo uses flush-concealed
hinged doors, a sliding pocket door between the hall and living room and a flush entrance door. Hinge and swing follow
`STY-02` (see [House layout](house-layout.md)).

Products, clearances, lighting levels and joinery remain concept intent for the interior designer and suppliers, not
specified or costed selections.
