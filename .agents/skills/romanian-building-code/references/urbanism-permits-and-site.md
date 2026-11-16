# Urbanism, permits and site

Items carried over from the earlier skill were researched/accessed 2026-08-10. Items marked `verified 2026-09-21` or later were fetched from the cited source at implementation time. Recheck at use time.

Record the access date for every value. When a source was not fetched, write a named gap under Gaps, never a number.

## Contents

- [Urbanism instruments](#urbanism-instruments)
- [Setbacks and height regime](#setbacks-and-height-regime)
- [Permits and statutory levies](#permits-and-statutory-levies)
- [Parcel facts and unknowns](#parcel-facts-and-unknowns)
- [Gaps](#gaps)

## Urbanism instruments

- **Basis: Law/regulation. Scope: General principle.** NP 057-02 §2.7.1 requires
  the height regime to agree with PUZ/PUD and the POT/CUT indicators stated in the certificat de urbanism. `verified 2026-09-21`.
  Source: [NP 057-02](https://lege5.ro/Gratuit/geztinrxgmya/normativul-privind-proiectarea-cladirilor-de-locuinte-revizuire-np-016-96-indicativ-np-057-02-din-24092002).

  Caveat: do not infer parcel controls from nearby buildings or generic guidance.

- **Basis: Law/regulation. Scope: General principle.** A certificat de urbanism is an information act, states its purpose
  and does not itself authorize construction. The authorization procedure proceeds through the certificate, applicable
  environmental act, required avize/acorduri, technical authorization documentation, filing and the final autorizație de
  construire. `verified 2026-09-21`. Source: [Legea 50/1991, arts. 2 and 6](https://legislatie.just.ro/Public/DetaliiDocument/1515).

  Caveat: the issued certificate controls the actual list for the project's parcel.

## Setbacks and height regime

- **Basis: Issued urbanism documents. Scope: Project-specific limit.** The maximum height at the eaves or parapet, POT,
  CUT and legal setbacks are set by the project's certificat de urbanism and the applicable PUZ/PUG for its locality.
  They are project-specific unknowns until the certificat de urbanism is issued and read.

  Caveat: the Blender model measures heights against its modeled terrain, not the surveyed regulatory datum. Photovoltaic
  panels or roof equipment above the limit need the architect's confirmation. No exemption is assumed.

- **Basis: Household decision. Scope: Project-specific choice.** `SITE-02` requires a **2 m** concept setback
  for the house, terrace and roof projections. The model's setback audit treats fences, gates, access paving and the
  parking space as outside that household inset. `verified 2026-09-21`. Sources:
  [architecture record](../../../../brief/architecture.md) and
  [site and exterior reference](../../blender-model/references/site-exterior.md).

  Caveat: this is explicitly not a statement of
  legal setbacks. The model's measured clearance is evidence against a demonstrative parcel, not a surveyed siting
  result.

- **Basis: Law/regulation. Scope: General principle.** Codul civil (Legea 287/2009) art. 615 requires at least **2 m**
  between the neighbouring plot, fenced or not, and a view window, balcony or similar work facing it (alin. 1). It prohibits a view
  window or similar work not parallel to the boundary closer than **1 m** (alin. 2). The distance is
  measured perpendicular to the boundary from the nearest point of the wall face or balcony line (alin. 3). Art. 616
  leaves light windows free of any distance limit if they are built to prevent a view onto the neighbouring plot.
  `verified 2026-09-29`. Sources: [art. 615](https://www.codulcivil.ro/art-615-distanta-minima-pentru-fereastra-de-vedere/),
  [art. 616](https://legeaz.net/noul-cod-civil/art-616-fereastra-de-lumina-limite-legale-limitele-juridice-ale-dreptului-de-proprietate-privata)
  and [Codul civil](https://legislatie.just.ro/Public/DetaliiDocument/175630). The official page listed the articles but
  did not render their text, so the wording was read from the two secondary portals.

  Caveat: this is the civil-law
  neighbour rule, distinct from the legal setback in the certificat de urbanism and from the household 2 m concept inset
  (`SITE-02`). Recheck the consolidated text at use time.

- **Basis: Household decision. Scope: Project-specific choice.** `SITE-03` requires a **P+1** house without a
  basement, while the regim de înălțime remains subject to the certificat de urbanism and the local regulation.
  `verified 2026-09-21`. Source: [architecture records](../../../../brief/architecture.md).

  Caveat: household form does not establish legal
  permission.

## Permits and statutory levies

- **Basis: Law/regulation. Scope: General principle.** Legea 50/1991 Annex 1 defines D.T.A.C. as the authorization
  documentation. After authorization, it develops into P.Th. and execution details, without changing the authorized
  D.T. `verified 2026-09-21`. Source: [Legea 50/1991, Annexes 1 and 2](https://legislatie.just.ro/Public/DetaliiDocument/1515).

  Caveat: the architect must confirm the complete D.T.A.C./P.Th./D.E. package and specialty verification for this project.

- **Basis: Law/regulation. Scope: General principle.** Legea 10/1995 art. 13 requires applicable fundamental-requirement
  checks by attested verificatori de proiect independent of the project authors. `verified 2026-09-21`. Source:
  [consolidated Legea 10/1995](https://legislatie.just.ro/Public/DetaliiDocument/307735).

  Caveat: the project team must
  identify the required domains, subdomains and specialties.

- **Basis: Law/regulation. Scope: Project-specific levy.** Codul fiscal art. 474(5) sets a building-permit tax of
  **0.5%** of the authorized value for a residential building or residential annex, applied through the local council's
  fiscal decision (HCL). `verified 2026-09-21`. Source: [Codul fiscal](https://legislatie.just.ro/Public/DetaliiDocument/197070).

  Caveat: the
  authorized value does not yet exist and the project's municipality confirms its current HCL and the assessed base.

- **Basis: Law/regulation. Scope: Project-specific levy.** Legea 10/1995 art. 43 applies an ISC quality levy of **0.5%**
  to the value excluding VAT of authorized new-construction or intervention works. `verified 2026-09-21`. Source:
  [consolidated Legea 10/1995](https://legislatie.just.ro/Public/DetaliiDocument/307735).

  Caveat: confirm payment stages,
  exclusions and final base with ISC for the authorized work.

- **Basis: Law/regulation. Scope: Project-specific levy.** Legea 50/1991 art. 30 applies an ISC state-control levy of
  **0.1%** of the authorized works value. `verified 2026-09-21`. Source:
  [consolidated Legea 50/1991](https://legislatie.just.ro/Public/DetaliiDocument/1515).

  Caveat: confirm payment mechanics
  and regularization for the permit.

- **Basis: Law/regulation. Scope: Project-specific levy.** The architecture stamp is **0.05%** of the investment value and
  is collected with the building permit. `verified 2026-09-21`. Source: [OAR Timbrul Arhitecturii](https://cultural.oar.archi/despre-timbru/).

  Caveat: confirm the investment base and payment form used by the project's municipality.

- **Basis: Budget convention. Scope: Project-specific allowance.** the budget's permit and utility administration category treats statutory levies as
  outside VAT. It expects the taxable base to be confirmed at authorization and regularized at reception. It excludes any
  PUZ or urbanism derogation. Source:
  [budget project data](../../../../budget/data/project.json).

  Caveat: this is budget treatment, not a legal opinion or
  published fee quote.

## Parcel facts and unknowns

- **Basis: Household evidence. Scope: Project-specific fact.** `SITE-01` records the demonstrative **24 × 40 m**
  parcel of **960 m²**, which is fictional and not surveyed. `verified 2026-09-21`. Source:
  [architecture record](../../../../brief/architecture.md).

  Caveat: the demonstrative parcel is not a surveyed boundary. Replace it with the household's own parcel facts.

- **Basis: Household decision. Scope: Project-specific choice.** `SITE-07` and `GAR-04` put vehicle access and one open
  parking space on the street edge. `verified 2026-09-21`. Sources:
  [architecture records](../../../../brief/architecture.md) and [outdoor record](../../../../brief/outdoor.md).

  Caveat: final geometry awaits survey and design.

- **Basis: Project-specific unknown. Scope: Survey prerequisite.** Before siting is fixed, `HH-05` requires the
  parcel outline to be checked against Stereo 70 coordinates or a topographic survey. `verified 2026-09-21`.
  Source: [project record](../../../../brief/project.md).

  Caveat: a GPS pin is not a corner survey.

- **Basis: Budget assumption. Scope: Project-specific unknown.** Utility availability at the parcel boundary
  (electricity, water, sewer, internet) is a budget assumption in the household's records. `verified 2026-09-21`.
  Source: [project record](../../../../brief/project.md).

  Caveat: this is not evidence of actual
  utility availability or connection capacity.

- **Basis: Household decision. Scope: Project-specific choice.** `SITE-04` requires ceramic brick for the exterior and
  primary walls of the house. `verified 2026-09-21`. Source: [architecture record](../../../../brief/architecture.md).

  Caveat: this is a household material rule with no normative citation and does not select the structural system.

## Gaps

- The height limit, POT, CUT, setbacks, avize/acorduri, certificate validity and the surveyed height datum are
  project-specific unknowns until the certificat de urbanism is issued. They need a complete parcel-specific review
  before siting or authorization.
- Current legal setbacks under the certificat de urbanism were not fetched. Do not infer them from the household's
  concept inset or from the Codul civil view-window distances.
- The official ISC Order 55 PDF at
  <https://www.isc.gov.ro/files/2022/Formulare/Ordin%2055-08.02.2022.pdf> failed by both curl and web fetch on
  2026-09-21. Its intended cross-check of the ISC levies remains outstanding even though the percentages were read in
  the controlling laws above.
- No project-specific authorized value, municipal calculation, payment schedule or reception regularization has been
  issued. Before payment, confirm all levy bases and due dates with the municipality, ISC and the architect.
