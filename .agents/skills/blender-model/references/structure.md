# Structural frame

Read this reference before you edit the `structure` array or any element that the frame crosses.

Paths in this reference are relative to `model/` unless they start with `.agents/` or the repository root. The
[model guide](../../../../model/AGENTS.md) holds the invariants, and [the skill](../SKILL.md) the workflow and safety
rules.

## Concept frame

The concept structure (`SITE-05`) is a monolithic C25/30 reinforced-concrete frame (stâlpi + grinzi) with
non-structural ceramic-brick infill (`SITE-04`) and RC slabs. `design/house.json` owns it as the top-level `structure`
array of `column` (`center`, `section_m`, `bottom_z_m`, `top_z_m`, `mark`), `beam` (`start`, `end`, `width_m`,
`bottom_z_m`, `top_z_m`, `placement` such as `in-wall`, `mark`) and `axis` (`label`, position) members per level.

The demo has nine 30 × 30 cm columns per storey on a 3 × 3 grid (axes 1–3 along local X at about 0, 5.5 and 9.6 m;
A–C along local Y at about 0, 4.4 and 7.6 m), in-wall perimeter beams and interior beams on the grid lines, plus
stair-opening trimmers. Compile reports `structure_column_count`, `structure_beam_length_m` and `structure_concrete_m3`
(gross at nodes); read current values from `just model-compile`.

## Enforced rules

- `engine/design_package.py` enforces the P 100-1/2013 concept minima: columns at least 0.30 m, beams at least 0.20 m
  wide and bw/hw ≥ 1/4 unless declared as band beams.
- `engine/architecture.py` builds `<level> | Frame` collections with a 2 mm face inset against z-fighting. They render
  in exterior and interior scenes and are excluded from cutaways and plans.
- `engine/requirements.py` `structure:clearance` fails when a member, within the floor-to-ceiling band of any storey it
  enters, hits furniture, an opening, a door swing or the stair.

Site values and code minima come from the `romanian-building-code` skill's structure reference. Sections,
reinforcement, regularity, the infill model and foundations remain the structural engineer's design; the frame is
concept predimensioning.
