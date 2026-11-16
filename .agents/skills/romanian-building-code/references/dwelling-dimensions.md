# Dwelling dimensions

Items carried over from the earlier skill were researched/accessed 2026-08-10. Later items have their own verification date through 2026-10-07. Recheck at use time.

Record the access date for every value. When a source was not fetched, write a named gap under Gaps, never a number.

## Contents

- [Clear heights](#clear-heights)
- [Stairs](#stairs)
- [Room areas and widths](#room-areas-and-widths)
- [Furniture and use clearances](#furniture-and-use-clearances)
- [Accessibility](#accessibility)
- [Gaps](#gaps)

## Clear heights

- **Basis: Law/regulation. Scope: General principle.** Annex 1 to Legea 114/1996 sets the minimum clear height of
  habitable rooms at **2.55 m**. It requires at least **15 m³/person** for attics, mezzanines and niches. These requirements were read in
  the official consolidated text (republished in Monitorul Oficial nr. 393/1997, consolidated form with amendment
  history), `verified 2026-09-21`. Source:
  [Legea 114/1996, Anexa nr. 1, Portal Legislativ](https://legislatie.just.ro/public/detaliidocument/8597).

  Caveat: the portal shows the consolidated form. The architect still confirms the applicable version at permit date.

- **Basis: Household decision. Scope: Project-specific choice.** `LAY-07` binds the project to the Romanian **2.55 m**
  minimum and to the regim de înălțime of the certificat de urbanism. It sets finished floor to finished ceiling as the
  project measurement convention. `verified 2026-09-21`. Source: [architecture record](../../../../brief/architecture.md).

  Caveat: the brief records the household requirement. The cited law and the certificat de urbanism, once issued,
  establish the external rules.

- **Basis: Household decision. Scope: Project-specific choice.** `LAY-07` records **2.55 m** finished clear height in
  ordinary rooms on both floors, with no double-height space. `verified 2026-11-10`. Source:
  [architecture record](../../../../brief/architecture.md).

  Caveat: these are household targets, not statutory minima.

## Stairs

NP 057-02 §1.2.3 describes its provisions as recommendations for rural P/P+1 dwellings. The household adopts its
stair provisions as project benchmarks in `LAY-04`. The architect must establish current mandatory applicability.
The primary text was read on 24 October 2026 in this [NP 057-02 reproduction](https://migs.ro/wp-content/uploads/2021/12/NP-057-2002-Normativ-privind-proiectarea-cla%CC%86dirilor-de-locuint%CC%A6e.pdf).

Section 3.2.(A).6 k gives 0.95 m clear width for main stairs, flights and landings in buildings with at most two levels.
Changes to the arrival or slab opening must preserve headroom. Model measurements (see the
[house layout reference](../../blender-model/references/house-layout.md)) are concept values, not a compliance finding.

- **Basis: Law/regulation. Scope: General principle.** NP 057-02 §3.2.A.6 gives the dwelling-stair relationship
  **2h + l = 62–64 cm**. In the general case, it allows at most **18 risers per flight**. It requires at least **3 risers**
  and equal tread and riser dimensions within a flight. For people with walking difficulties, it gives
  **h ≤ 16 cm**, **l ≥ 30 cm**, and at most **16 risers per flight**. `verified 2026-09-21`. Source:
  [NP 057-02](https://lege5.ro/Gratuit/geztinrxgmya/normativul-privind-proiectarea-cladirilor-de-locuinte-revizuire-np-016-96-indicativ-np-057-02-din-24092002).

  Caveat: confirm the norm's current legal status and the applicable accessibility case with the architect and
  verificator de proiect.

- **Basis: Design evidence. Scope: Project-specific check.** The concept stair consists of two equal straight flights
  with an intermediate landing and closed risers (`LAY-04`). `model/engine/requirements.py` reports each authored stair's
  tread and riser dimensions against the NP 057-02 relation as the `stair:np057:<stair-id>` check. The slab opening
  follows the stair; finished headroom needs coordinated review. `verified 2026-11-10`. Source:
  [saved house design](../../../../model/design/house.json).

- **Basis: Law/regulation. Scope: General principle.** NP 057-02 §3.2.(A).6 also requires clear headroom of at least
  **2.00 m** between flights and under main stairs (1.90 m for secondary stairs). It sizes flight width by stair and
  building type (§3.2.(A).6 k). Door widths are under [Room areas and widths](#room-areas-and-widths). `verified 2026-09-21`. Source:
  [NP 057-02](https://lege5.ro/Gratuit/geztinrxgmya/normativul-privind-proiectarea-cladirilor-de-locuinte-revizuire-np-016-96-indicativ-np-057-02-din-24092002).

  Caveat: the Lege5 page reproduces the published form without later amendments.

## Room areas and widths

- **Basis: Household decision. Scope: Project-specific choice.** `LAY-06` caps the P+1 house at **180 m² gross built
  area**, including facade finishes. `verified 2026-09-22`. Source: [architecture record](../../../../brief/architecture.md).

  Caveat: this is a household ceiling, not a legal minimum or maximum.

- **Basis: Budget convention. Scope: Project-specific choice.** `LAY-06` also fixes the gross built area used as the
  current operational budget basis. `verified 2026-11-10`. Source: [architecture record](../../../../brief/architecture.md).

  Caveat: it is neither certified useful area nor a statutory area calculation.

- **Basis: Household decision. Scope: Project-specific choice.** `LAY-06` keeps dimensions and proportions open to
  exploration within the recorded programme, while `LAY-01` preserves access and the connection graph.
  `verified 2026-09-21`. Source: [architecture records](../../../../brief/architecture.md).

  Caveat: legal minima still control.

- **Basis: Law/regulation. Scope: General principle.** Art. 3 of Legea 114/1996 makes Anexa nr. 1 a permit
  condition: "Autorizarea executării construcțiilor de locuințe noi, indiferent de natura proprietății sau a
  amplasamentului, se face pe baza satisfacerii exigențelor minimale, prevăzute în anexa nr. 1 la prezenta lege." It
  therefore binds this privately owned single-family house even though no household member needs a wheelchair-accessible bathroom.
  `verified 2026-10-07` (consolidated form of 30.07.2022). Source:
  [Legea 114/1996, Portal Legislativ](https://legislatie.just.ro/public/detaliidocument/8597).

  Caveat: the architect who signs the DTAC and the verificator de proiect confirm the version in force at permit date.

- **Basis: Law/regulation. Scope: General principle.** Legea 114/1996, Anexa nr. 1, table B sets minimum areas per
  dwelling by household size. For **3 persons** (such as two adults and one child) it requires **3 rooms**,
  a living room of at least **18.00 m²**, bedrooms totalling **22.00 m²**, a dining place of **3.00 m²**, a kitchen of
  **5.50 m²**, sanitary rooms of **6.50 m²**, storage of **2.50 m²**, a useful area of **66.00 m²** and a built area of
  **102.00 m²**. The table below gives the other household sizes. Built areas may deviate by ±10 % with the site. `verified 2026-09-22`. Source:
  [Legea 114/1996, Anexa nr. 1](https://legislatie.just.ro/public/detaliidocument/8597).

  Caveat: these are statutory
  floors that the concept exceeds by a wide margin. They are not targets. The annex's area definitions (useful,
  habitable, built) differ from the model's floor-face and wall-body measurements. The household row gives one total
  bedroom area. It does not impose a 12 m² minimum on each individual bedroom.

- **Basis: Law/regulation. Scope: General principle.** The same annex requires a minimum circulation width of
  **120 cm** for corridors and the vestibule inside the dwelling. It requires the main sanitary room to allow a wheelchair
  user to reach the bathtub. It sets the number of sanitary rooms by dwelling size (4 rooms: one bath plus one shower room,
  5 rooms: two baths) and lists the minimum sanitary fittings. `verified 2026-09-22`. Source:
  [Legea 114/1996, Anexa nr. 1](https://legislatie.just.ro/public/detaliidocument/8597).

  Caveat: `LAY-05` and `RM-UBATH-01` record both minima. The saved-model audit reports them as
  `corridor:legea114:<room>` for the circulation rooms such as `G-HALL` and `U-LOBBY` (fail below 1.20 m, review within
  4 cm of it for finishes) and as the review-only `bath-access:legea114:U-BATH`. The bathtub-access requirement is a
  statutory minimum that a household choice of no general accessibility requirement does not waive.

Annex 1 to Legea 114/1996 gives these minimum areas. Each row is `verified 2026-09-21` from
[the fetched annex](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo):

| Persons / rooms | Living room | Bedrooms |  Dining | Kitchen | Sanitary | Storage | Useful / built area | Source and status                                                                                                                                               |
| --------------- | ----------: | -------: | ------: | ------: | -------: | ------: | ------------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 / 1           |    18.00 m² |        — | 2.50 m² | 5.00 m² |  4.50 m² | 2.00 m² |    37.00 / 58.00 m² | [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo), `verified 2026-09-21` |
| 2 / 2           |    18.00 m² | 12.00 m² | 3.00 m² | 5.00 m² |  4.50 m² | 2.00 m² |    52.00 / 81.00 m² | [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo), `verified 2026-09-21` |
| 3 / 3           |    18.00 m² | 22.00 m² | 3.00 m² | 5.50 m² |  6.50 m² | 2.50 m² |   66.00 / 102.00 m² | [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo), `verified 2026-09-21` |
| 4 / 3           |    19.00 m² | 24.00 m² | 3.50 m² | 5.50 m² |  6.50 m² | 3.50 m² |   74.00 / 115.00 m² | [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo), `verified 2026-09-21` |
| 5 / 4           |    20.00 m² | 34.00 m² | 3.50 m² | 6.00 m² |  7.50 m² | 4.00 m² |   87.00 / 135.00 m² | [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo), `verified 2026-09-21` |
| 6 / 4           |    21.00 m² | 36.00 m² | 4.50 m² | 6.00 m² |  7.50 m² | 4.50 m² |   93.00 / 144.00 m² | [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo), `verified 2026-09-21` |
| 7 / 5           |    22.00 m² | 46.00 m² | 5.00 m² | 6.50 m² |  9.00 m² | 5.00 m² |  107.00 / 166.00 m² | [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo), `verified 2026-09-21` |
| 8 / 5           |    22.00 m² | 48.00 m² | 6.00 m² | 6.50 m² |  9.00 m² | 5.50 m² |  110.00 / 171.00 m² | [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo), `verified 2026-09-21` |

- **Basis: Law/regulation. Scope: General principle.** Legea 114/1996 Annex 1 and NP 057-02 both give a minimum
  **1.20 m** clear circulation width for internal corridors and vestibules. NP 057-02 §3.2.(A).6 h gives **0.80 m**
  minimum clear room doors within the dwelling, **0.90 m** at the dwelling entrance, and **0.90 m** at the main entrance of a single-family
  building. `verified 2026-09-21`. Sources: [Legea 114/1996 Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo)
  and [NP 057-02](https://lege5.ro/Gratuit/geztinrxgmya/normativul-privind-proiectarea-cladirilor-de-locuinte-revizuire-np-016-96-indicativ-np-057-02-din-24092002).

  Caveat: the architect must confirm applicability and measurement conventions against current consolidated texts.

## Furniture and use clearances

- **Basis: Design evidence. Scope: Project-specific check.** The repository records no numeric furniture-clearance rule.
  The furnishings export carries `clearance_status: not-modeled`, while `RM-KIT-01` preserves working zones
  but leaves the final joinery dimensions to design. `verified 2026-09-21`. Sources:
  [furnishings export](../../../../model/design/furnishings.json) and [kitchen record](../../../../brief/rooms-and-furnishings.md).

  Caveat: no zero-clearance field in the furnishings export proves usable clearance.

- **Basis: Law/regulation. Scope: General principle.** Legea 114/1996 Annex 1 requires the main sanitary room to permit
  access to the bath by a wheelchair user. It reserves space in the bathroom for a washing machine and requires kitchen
  ventilation plus space for a refrigerator and work table. Its minimum-equipment tables specify **one** kitchen sink
  with drainer for dwellings of **1–5 rooms** and the listed bathroom, shower and WC fixtures. `verified 2026-09-21`.
  Source: [Legea 114/1996, Annex 1](https://lege5.ro/Gratuit/ge3dgmru/exigente-minimale-pentru-locuinte-lege-114-1996-anexa-nr-1?dp=geydcnbwgmydo).

  Caveat: these provisions do not supply complete furniture gabarits or manufacturer service clearances.

- **Basis: Law/regulation. Scope: General principle.** Check furniture and equipment gabarits against verified Romanian
  provisions and manufacturer dimensions, never foreign ergonomic tables. Source:
  [NP 057-02](https://lege5.ro/Gratuit/geztinrxgmya/normativul-privind-proiectarea-cladirilor-de-locuinte-revizuire-np-016-96-indicativ-np-057-02-din-24092002),
  `verified 2026-09-21`.

  Caveat: no complete numeric furniture-clearance annex was located in the fetched text.

## Accessibility

- **Basis: Household decision. Scope: Project-specific choice.** `SITE-03` records no lift. The household states no general
  accessibility requirement. `verified 2026-09-21`. Source: [architecture record](../../../../brief/architecture.md).

  Caveat: a household choice cannot waive an applicable legal duty.

- **Basis: Law/regulation. Scope: Conditional principle.** NP 057-02 pct. 3.2.(A).4.f requires a **1.50 × 1.50 m**
  wheelchair manoeuvre space where circulations for wheelchair users are narrowed, and pct. 3.2.(A).1.c and
  3.2.(B).1.b use the same square at path turns and lift landings. `verified 2026-10-07`. Source:
  [NP 057-02](https://lege5.ro/Gratuit/geztinrxgmya/normativul-privind-proiectarea-cladirilor-de-locuinte-revizuire-np-016-96-indicativ-np-057-02-din-24092002).

  Caveat: no fetched provision sizes the bathroom approach required by Legea 114/1996 Anexa nr. 1. The project uses
  the square only as the comparison reference of `bath-access:legea114:U-BATH`, not as a pass limit.

- **Basis: Law/regulation. Scope: Conditional principle.** Apply the NP 057-02 accessible-route stair variant only where
  the design serves people with walking difficulties. `verified 2026-09-21`. Source:
  [NP 057-02](https://lege5.ro/Gratuit/geztinrxgmya/normativul-privind-proiectarea-cladirilor-de-locuinte-revizuire-np-016-96-indicativ-np-057-02-din-24092002).

  Caveat: NP 051 is not adopted as a household requirement, but the architect must still determine every mandatory
  accessibility provision applicable to the permit design.

## Gaps

- The fetched NP 057-02 reproduction warns that later amendments may be absent. Confirm its current status and obtain an
  authoritative consolidated text before compliance work.
- No complete furniture-dimension annex or furniture passage-clearance table was located in Legea 114/1996 or
  NP 057-02. Only the 120 cm corridor width and the door-opening widths above are verified. Do not supply furniture
  clearance values until the architect identifies and reads the applicable Romanian source.
