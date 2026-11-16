---
coordination: exempt
name: romanian-building-code
description:
  Romanian legislation, normativ, standard and legal-minimum guidance for clear height, stair geometry, room area,
  corridor and door width, furniture clearance, setback, height regime, POT, CUT, PUG/PUZ, certificat de urbanism,
  autorizație de construire, permit fees, nZEB, Mc 001, C 107, I5, P 118, P 100, CR 6, CR 1-1-3, STAS 6054, NP 112 and
  reinforced-concrete frame ("stâlpi + grinzi") minima. Use whenever dimensioning construction, rooms, stairs,
  openings, furniture, site placement or the structural frame for the project's house.
---

# Romanian Building Code

Bind every dimensional, compliance and construction rule for the house to Romanian law, normatives, standards and the
local urbanism of the project's locality.

This skill is coordination-exempt: skip the ai-coord gate for its declared work. Explicitly authorized implementation
or other repository writes re-enter the gate.

The bundled research comes from the 2026-08-10 specialist snapshot and was selectively reverified through 2026-10-07.
Recheck every live rule at use time.

## Working contract

- Cite the Romanian source, its scope and access date for every rule. Never substitute generic construction guidance
  from other countries or foreign code numbers.
- Use the issued certificat de urbanism and applicable PUZ/PUG for local limits. Treat the height limit, POT, CUT,
  setbacks and every unverified indicator as project-specific unknowns until the certificat de urbanism is issued.
- Distinguish legal minima from household decisions and say which is which. The recorded legal minimum is 2.55 m.
  The heights in `LAY-07`, the 2 m concept setback (`SITE-02`) and the 180 m² cap (`LAY-06`) are household decisions.
- Record the access date for every verified value. When a source was not read, write a named gap instead of a number.
- Keep `Basis` and `Scope` labels internal. Explain provenance in plain language in answers.
- Escalate legal and code interpretation to the responsible Romanian professionals—architect, verificator de proiect,
  structural, fire and services designers—and never present this skill as a compliance result.

## Routing

- Read [dwelling dimensions](references/dwelling-dimensions.md) for clear heights, stairs, room areas, corridor and door
  widths, furniture and equipment clearances, and accessibility.
- Read [urbanism, permits and site](references/urbanism-permits-and-site.md) for setbacks, Codul civil
  neighbour view-window distances, height regime, PUG/PUZ/POT/CUT,
  certificat de urbanism, autorizație de construire, permit fees and levies, and parcel facts.
- Read [energy compliance](references/energy-compliance.md) for nZEB, Mc 001, EPBD, C 107, I5, P 118, I7, I9 and the
  NTPEE-2018 gas rules.
- Read [structure](references/structure.md) for P 100-1 seismic design (including the ag/Tc inputs, RC frame minima and
  masonry-infill effects), CR 6 masonry/infill scope, CR 1-1-3 snow load, STAS 6054 frost depth, NP 112 shallow
  foundations and CR 0 basis of design.

## Output

For each rule, give these details:

- The rule.
- The Romanian source, scope and access date.
- Whether it is a legal minimum, household decision or project-specific unknown.
- The next professional verification.

Finish only when every quoted limit cites its Romanian source and access date, no household preference is presented as
law, gaps are named, and no foreign code appears.
