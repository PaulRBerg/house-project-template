# Structure

Research/access was on 2026-09-24 for the concept reinforced-concrete frame audit ("stâlpi + grinzi" monolithic C25/30
frames, non-structural 36 cm ceramic-brick infill, 18 cm RC slabs, RC stair, continuous footings and foundation beams).
Recheck at use time.

Record the access date for every value. When a source was not fetched, write a named gap under Gaps, never a number.

These are inputs for concept predimensioning of the frame, not a structural design. The structural engineer and
the verificator de proiect atestat establish the binding site data, load combinations, detailing and compliance for
the permit design. Nothing here substitutes for their calculation.

## Contents

- [P 100-1/2013 seismic design](#p-100-12013-seismic-design)
- [CR 6-2013 masonry design](#cr-6-2013-masonry-design)
- [CR 1-1-3/2012 snow load](#cr-1-1-32012-snow-load)
- [STAS 6054-77 frost depth](#stas-6054-77-frost-depth)
- [NP 112-2014 shallow foundations](#np-112-2014-shallow-foundations)
- [CR 0-2012 basis of design](#cr-0-2012-basis-of-design)
- [Gaps](#gaps)

## P 100-1/2013 seismic design

- **Basis: Law/regulation. Scope: Site seismic design values.** P 100-1/2013 sets the peak design ground acceleration
  **ag** (for an average recurrence interval IMR = 225 years) and the response-spectrum corner period **Tc** by
  locality, through its seismic zonation maps and annex tables. The project's values are `<ag>` and `<Tc>`, a
  project-specific unknown until the structural engineer reads them for the project's locality and the geotechnical
  study confirms the site class. `verified 2026-09-24`. Source: P 100-1/2013 as published in Monitorul Oficial.

  Caveat: no numeric seismic value is recorded here. The geotechnical/seismic study for the actual site must confirm
  the applicable microzonation and site class.

- **Basis: Law/regulation. Scope: Chapter 5 RC frame minima.** Art. 5.3.2.1(1)–(2) set beam width ≥ **200 mm** and the
  ratio of beam width bw to section height hw ≥ **1/4**. Art. 5.3.2.1(3) limits beam-axis eccentricity at a
  beam-column node to at most **bc/3** (bc = column width, normal to the beam axis). Art. 5.3.2.2(1) sets the minimum
  column cross-section dimension at **300 mm**. Art. 5.4.2.2(1) applies 5.3.2.2 (column minimum) unchanged to medium
  ductility class (DCM). Art. 5.4.2.1(1) applies 5.3.2.1 to beams except its eccentricity clause.
  `verified 2026-09-24`. Sources: official text, [P 100-1/2013, mdlpa.ro](https://www.mdlpa.ro/userfiles/reglementari/Domeniul_I/I_22_P100_1_2013.pdf)
  and [Encipedia, Chapter 5](https://www.encipedia.org/articole/proiectare/coduri-de-proiectare/cod-de-proiectare-seismica-p100-1-2013/capitolul-5-prevederi-specifice-constructiilor-de-beton.html).

  Caveat: these are code minima for ductile detailing, not sized structural members. The structural engineer
  dimensions each column and beam from the actual load combinations and ductility class chosen.

- **Basis: Law/regulation. Scope: Chapter 4 regularity in elevation.** Art. 4.4.3.3(1) accepts gradual setbacks over
  a building's height only if they do not exceed, at any level, **20%** of the dimension of the immediately lower
  level (plus limits on stiffness/strength/mass irregularity in (2)–(5)). For buildings that fail the 4.4.3.2/4.4.3.3
  regularity checks, art. 4.5.3.5.2.1(2) requires a spatial
  (3-D) calculation model instead of two independent planar models. For a building irregular in elevation per
  4.4.3.3, art. 6.3.2(2) requires a **20%** reduction in the behaviour factor q from Table 6.3.
  `verified 2026-09-24`. Source: official text,
  [P 100-1/2013, mdlpa.ro](https://www.mdlpa.ro/userfiles/reglementari/Domeniul_I/I_22_P100_1_2013.pdf).

  Caveat: this
  reference states the code mechanism only. The structural engineer determines whether the concept's own setbacks
  (if any) trigger these consequences. This reference does not perform that self-check.

- **Basis: Law/regulation. Scope: Masonry infill effects on the frame (art. 5.9).** Art. 5.9 covers RC frame
  structures with masonry infill panels whose materials/connections significantly affect structural behaviour.
  It gives measures to limit unfavourable local effects — principally brittle shear failure — from the infill-frame
  interaction:
  - (2) Avoiding short-column/short-beam proportions where possible (e.g. at parapets or transom openings).
  - (3) Transverse reinforcement of beam/column zones for the extra shear from the compressed-diagonal action of the
    infill panel, incomplete infill-to-beam contact, short-column/short-beam conditions, or door/window openings in the panel.
  - (5) Critical-zone rules cover both column ends in contact with infill and the full length of ground-floor
    columns. They also cover the full column length where an opening adjoins the column or infill sits on only one
    side of the column (corner/edge columns).
  - (6) Additional detailing for a column adjacent to an infill opening includes the plastic-hinge shear model and
    transverse reinforcement over the opening length plus hc. It includes inclined bars if the infill-free length is
    under 1.5 hc.

  `verified 2026-09-24`. Source: official text,
  [P 100-1/2013, mdlpa.ro](https://www.mdlpa.ro/userfiles/reglementari/Domeniul_I/I_22_P100_1_2013.pdf) and
  [Encipedia, Chapter 5](https://www.encipedia.org/articole/proiectare/coduri-de-proiectare/cod-de-proiectare-seismica-p100-1-2013/capitolul-5-prevederi-specifice-constructiilor-de-beton.html).

  Caveat: the 36 cm ceramic-brick infill is non-structural by concept, but art. 5.9 still binds the frame's detailing
  wherever that infill is present. The structural engineer selects the critical zones and detailing that apply.

## CR 6-2013 masonry design

- **Basis: Law/regulation. Scope: Applicability to non-structural infill panels in RC frames.** CR 6-2013 governs
  the design of masonry-structural-wall buildings and all other masonry construction parts/elements regardless of
  structure type (art. 1.1(1)). For the seismic design situation, it applies only together with P 100-1: chapter 8 for
  structural masonry walls, and **chapter 10** for non-structural walls and masonry infill panels framed in frames
  ("pereţi nestructurali, panouri de zidărie înrămate în cadre") and other non-structural elements such as chimneys
  and vent stacks (art. 1.1(2)). `verified 2026-09-24`. Source: official published text,
  [CR 6-2013, republished copy](https://colegiu-diriginti-santier.ro/norme/cod%20de%20proiectare%20pentru%20structuri%20din%20zidarie%20CR6.pdf),
  approved by [Ordin 2464/2013](https://legislatie.just.ro/Public/DetaliiDocument/151408).

  Caveat: for the house's
  RC-frame-with-infill concept, CR 6-2013 supplies masonry material and verification rules for the infill panels
  themselves. P 100-1 art. 5.9 (above) governs the frame's own detailing against infill interaction. The structural
  engineer coordinates both.

## CR 1-1-3/2012 snow load

- **Basis: Law/regulation. Scope: Illustrative ground snow load.** CR 1-1-3/2012's own worked example (Exemplul C.2)
  sizes an industrial building at another Romanian locality. It uses characteristic ground snow load
  **s0,k = 2.5 kN/m²** (IMR = 50 years, probability of non-exceedance p = 0.98). Its low-slope roof has a shape
  coefficient μi = 0.8, giving a design roof snow load of 2.0 kN/m². `verified 2026-09-24`. Source: official
  published text (Anexa),
  [legislatie.just.ro, CR 1-1-3/2012](https://legislatie.just.ro/Public/DetaliiDocument/222507).

  Caveat: this is an illustration from the code's own example, not the project's value. The project's s0,k is
  `<s0,k>`, a project-specific unknown until the structural engineer reads it for the project's locality from the
  Figure 3.1 zonation map or the by-locality Table A.1.

## STAS 6054-77 frost depth

- **Basis: Law/regulation. Scope: Locality frost depth.** STAS 6054-77 gives the maximum frost depth by locality, measured
  from natural ground level. The project's value is `<frost depth>`, a project-specific unknown until it is read for
  the project's locality. NP 112-2014 Annex C confirms STAS 6054-77 as the reference source for frost-depth values and
  gives the minimum-foundation-depth table (Tabelul C.1) that combines frost depth, soil type and groundwater depth.
  `verified 2026-09-24`. Source:
  [NP 112-2014, Anexa C](https://stefanardelean.files.wordpress.com/2017/02/adancimea-de-inghet-anexa-c-np112-2014.pdf).

  Caveat: the geotechnical study sets the actual minimum foundation depth from Tabelul C.1, local soil and
  groundwater level.

## NP 112-2014 shallow foundations

- **Basis: Law/regulation. Scope: Applicability to continuous footings and foundation beams.** The geotechnical-design
  part (Partea I) applies to shallow foundations, harmonized with SR EN 1997-1 and its national annex (with associated
  errata/amendments). When the foundation depth D ≤ 3.00 m and/or the equivalent embedment ratio De/B ≤ 1.5
  (B = the footing's small side or diameter), it classes a shallow foundation as "directă". The normative has two parts
  for shallow foundations: Partea I geotechnical design and Partea II structural design. `verified 2026-09-24`. Source:
  pre-publication text under the same title,
  [colegiu-diriginti-santier.ro](https://colegiu-diriginti-santier.ro/norme/NP112%20normativ%20privind%20proiectarea%20fundatiilor%20de%20suprafata.pdf),
  approved in final form as NP 112-2014 by
  [Ordin 2352/2014](https://legislatie.just.ro/public/DetaliiDocument/164063).

  Caveat: the fetched text is the
  pre-publication draft (labelled indicativ NP 112-2013 in the document itself). Before quoting article numbers, confirm the final consolidated
  NP 112-2014 wording with the structural/geotechnical engineer. Continuous footings
  and foundation beams for a P+1 house are shallow ("directe") foundations under this classification.
  The geotechnical study and structural design determine sizing. This reference gives no sizing value.

## CR 0-2012 basis of design

- **Basis: Law/regulation. Scope: Applicability.** "Codul cuprinde principii, reguli de aplicare şi date de bază
  armonizate cu standardul SR EN 1990, necesare pentru proiectarea şi verificarea structurilor de construcţii,
  elementelor structurale şi ale tuturor elementelor de construcţii, instalaţii şi echipamente pentru care există
  cerinţe normative de rezistenţă, stabilitate şi durabilitate" (art. 1.1). It applies to new buildings and
  engineering structures and to existing ones under rehabilitation or a change of function. It explicitly excludes
  nuclear power plants, dams and bridges. `verified 2026-09-24`. Source:
  [legislatie.just.ro, Ordinul nr. 1530/2012](https://legislatie.just.ro/Public/DetaliiDocumentAfis/222161).

  Caveat:
  CR 0-2012 provides the basis of design (limit states, actions, safety/durability principles) for P 100-1,
  CR 6, CR 1-1-3, NP 112 and SR EN 1992-1-1 with its Romanian national annex. It supplies no numeric value
  used elsewhere in this file.

## Gaps

- Named gap: the P 100-1/2013 ag/Tc, CR 1-1-3/2012 s0,k and STAS 6054-77 frost-depth values for the project's
  locality are not recorded. Read them from the code maps and tables once the project's locality and parcel are known.
- Named gap: CR 1-1-3/2012's Figure 3.1 zonation map and Table A.1 by-locality table were not read directly. The
  s0,k = 2.5 kN/m² value above comes from the code's own worked example only.
- Named gap: the final consolidated NP 112-2014 publication text (as opposed to the pre-publication NP 112-2013 draft
  text read above) was not independently fetched. Article numbering should be reconfirmed.
- Named gap: SR EN 1992-1-1 (RC design) and its Romanian national annex were not fetched. This file records only
  P 100-1's seismic-specific minima layered on top of it. No foreign national annex, IBC or ACI provision is used
  anywhere in this file.
