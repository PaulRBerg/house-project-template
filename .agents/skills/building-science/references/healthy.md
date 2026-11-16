# Healthy home

Researched/accessed 2026-08-10. Recheck time-sensitive guidance, standards and product claims at use time.

## Contents

- [Environmental systems](#environmental-systems)
  - [Source control and outdoor air](#source-control-and-outdoor-air)
  - [Ventilation, filtration, and interpretation](#ventilation-filtration-and-interpretation)
  - [Particles, cooking, moisture, water, and alarms](#particles-cooking-moisture-water-and-alarms)
- [Sleep, light, and acoustics](#sleep-light-and-acoustics)
  - [Bedroom conditions](#bedroom-conditions)
  - [Light: timing, spectrum, and controls](#light-timing-spectrum-and-controls)
  - [Noise, blackout, and commissioning](#noise-blackout-and-commissioning)
- [Materials and pollutants](#materials-and-pollutants)
  - [Everyday source control](#everyday-source-control)
  - [Legacy, site, and adjacent-space hazards](#legacy-site-and-adjacent-space-hazards)
- [Recovery, monitoring, and operations](#recovery-monitoring-and-operations)
  - [Layout and optional amenities](#layout-and-optional-amenities)
  - [Sensors and commissioning](#sensors-and-commissioning)
  - [Operations, automation, and data](#operations-automation-and-data)
  - [Evidence gaps to retain](#evidence-gaps-to-retain)

## Environmental systems

Use this reference to frame residential exposure control and commissioning. It is not a substitute for local code,
equipment design, or diagnostic testing.

### Source control and outdoor air

- **Basis: Expert synthesis.** Remove or isolate indoor sources first: smoking, unvented combustion, moisture, solvents,
  particles from cooking, and garage transfer. Harvard's
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  is environmental-health guidance, not a construction manual.
- **Basis: Peer-reviewed study.** Ventilation can support health, but its benefit depends on outdoor-air quality and the
  building. See the [ventilation-health review](https://doi.org/10.1016/j.buildenv.2015.08.011).

  Caveat: do not
  prescribe more outdoor air during smoke, pollution, or local contaminant events without an intake and filtration
  strategy.

- **Basis: Design inference.** Make outdoor-air mode observable and controllable. Normal ventilation, filtered
  recirculation, and smoke-event operation should have distinct commissioning criteria.

### Ventilation, filtration, and interpretation

| Item                                                                       | Basis                | Context and canonical source                                                                                                                                                                                                                                                                                                                                    | Material caveat                                                                                                                                  |
| -------------------------------------------------------------------------- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| PAC scale: below 3 eACH low; 3–4 minimum; 4–5 good; 5–6 excellent; 6 ideal | Expert synthesis     | Harvard's [air-cleaner calculator](https://healthybuildings.hsph.harvard.edu/tools/air-cleaner-calculator/) describes eACH as verified outdoor air plus clean-air delivery rate (CADR).                                                                                                                                                                         | This is a calculator context, not residential code or a whole-home performance guarantee.                                                        |
| Earlier at least 5 ACH guidance                                            | Expert synthesis     | Harvard's [portable-air-cleaner guidance](https://healthybuildings.hsph.harvard.edu/portable-air-cleaners-selection-and-application-considerations-for-covid-19-risk-reduction/) used it for COVID risk reduction.                                                                                                                                              | Do not relabel it as a universal residential requirement.                                                                                        |
| High-efficiency HVAC filtration and portable HEPA air cleaning             | Expert synthesis     | Harvard [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf) supports high-efficiency filtration and portable or whole-house air cleaning where warranted. HEPA is a filter class, while CADR and room volume determine portable-cleaner contribution. | Verify fan static-pressure capability, bypass, airflow, noise, maintenance, and delivered CADR. Filtration does not remove CO2.                  |
| MERV 13 HVAC filtration                                                    | Commercial framework | MAVI recommends MERV 13 or HEPA as a high-leverage category in its [answers](https://mavilongevity.com/answers).                                                                                                                                                                                                                                                | Verify that the actual system can deliver its design airflow and pressure with the selected filter. A rating alone does not prove room exposure. |
| MERV 8 captures about 30% of PM2.5                                         | Personal protocol    | Bryan Johnson reports this estimate in his [14 home changes](https://blueprint.bryanjohnson.com/blogs/news/14-changes-i-made-to-my-home).                                                                                                                                                                                                                       | This is an unsourced personal-page claim, not a system-selection basis.                                                                          |
| CO2 below 800 ppm overnight                                                | Commercial framework | MAVI proposes this bedroom target in [The Verified Home](https://mavilongevity.com/journal/the-verified-home).                                                                                                                                                                                                                                                  | A concentration is a ventilation proxy under assumptions, not an indoor-air-quality verdict or universal residence limit.                        |
| CO2 decay from 1,500 to 800 ppm in 30–45 minutes                           | Commercial framework | MAVI's [Verified Home](https://mavilongevity.com/journal/the-verified-home) proposes this test.                                                                                                                                                                                                                                                                 | Occupancy, room volume, mixing, outdoor background, sensor placement, and starting conditions change the result.                                 |

- **Basis: Expert synthesis.** Interpret CO2 with occupancy/activity, room volume, outdoor background, and steady state.
  Harvard's [CO2 calculator](https://healthybuildings.hsph.harvard.edu/tools/co2-calculator/) makes those assumptions
  explicit. Pair it with particle, humidity/temperature, and source-specific indicators rather than treating one sensor
  as comprehensive.
- **Basis: Personal protocol.** Johnson's
  [home checklist](https://blueprint.bryanjohnson.com/blogs/news/14-changes-i-made-to-my-home) monitors CO2, PM1, PM2.5,
  PM10, and AQI.

  Caveat: this is a personal monitoring set, not a validated minimum sensor suite. AQI is principally an
  outdoor communication index and sensor specifications determine what a reading means.

- **Basis: Peer-reviewed study.** The
  [2024 observational home IAQ/cognition study](https://doi.org/10.1016/j.buildenv.2024.111551) is useful context for
  measuring several indoor conditions together.

  Caveat: observational association is not a universal target or proof
  that a single intervention causes cognitive change.

### Particles, cooking, moisture, water, and alarms

| Item                                        | Basis              | Context and canonical source                                                                                                                         | Material caveat                                                                                         |
| ------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| PM2.5 annual guideline: 5 µg/m³             | Guideline/standard | The [WHO global air quality guidelines](https://www.who.int/publications/i/item/9789240034228) set this outdoor, population-health annual reference. | It is not an indoor residential commissioning pass/fail criterion.                                      |
| Relative humidity below 60%, ideally 30–50% | Guideline/standard | EPA's [mould and moisture guide](https://www.epa.gov/mold/brief-guide-mold-moisture-and-your-home) gives this moisture-management range.             | Climate, enclosure, cold surfaces, and occupant comfort can make a single room reading misleading.      |
| Dry wet materials within 24–48 hours        | Guideline/standard | EPA's [mould and moisture guide](https://www.epa.gov/mold/brief-guide-mold-moisture-and-your-home) gives this response window.                       | Visible or hidden damage still needs source diagnosis and, where appropriate, professional remediation. |
| PFAS: 100 ng/L for the sum of 20            | Guideline/standard | The [EU drinking-water directive](https://eur-lex.europa.eu/eli/dir/2020/2184/oj) supplies this regulatory reference.                                | It is jurisdiction-specific and not a universal water-treatment trigger.                                |

- **Basis: Commercial framework.** MAVI gives an RH range of 40–60% in
  [The Verified Home](https://mavilongevity.com/journal/the-verified-home).

  Caveat: its upper edge conflicts with EPA's
  preferred range. Use condensation risk and moisture diagnostics, not an averaged number.

- **Basis: Commercial framework.** MAVI gives a TVOC range of 300–500 µg/m³ and a 72-hour outdoor-air flush in
  [The Verified Home](https://mavilongevity.com/journal/the-verified-home).

  Caveat: TVOC is a broad screening metric,
  and outdoor conditions, source removal, ventilation rate, and curing govern a flush. Neither is a universal
  residential pass/fail or substitute for source control.

- **Basis: Peer-reviewed study.** Specify externally ducted kitchen extraction and verify capture, especially for
  combustion and high-particle cooking. Residential capture varies substantially by hood and use in this
  [field study](https://doi.org/10.1111/ina.12118).

  Caveat: a flow rating alone does not prove capture. Use position,
  rear burners where practical, make-up air, noise, and field observation.

- **Basis: Expert synthesis.** Use outdoor-ducted kitchen and bathroom exhaust, clean it, and address leaks/condensation
  rather than masking odour. See Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  and WHO [dampness and mould guidance](https://www.who.int/publications/i/item/9789289041683).

  Caveat: persistent
  dampness may be an enclosure, plumbing, drainage, or ventilation defect.

- **Basis: Guideline/standard.** For a private well, test through a certified lab annually for total coliform, nitrate,
  TDS, and pH, plus locally relevant contaminants. EPA's
  [private-well guidance](https://www.epa.gov/privatewells/protect-your-homes-water) is the baseline.

  Caveat: a
  treatment choice follows the actual result and local hydrogeology, not a generic filter stack.

- **Basis: Expert synthesis.** Test source water and investigate premise plumbing before choosing point-of-use or
  whole-house treatment. Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  notes that water can change after utility delivery.

  Caveat: select treatment for measured contaminants and verify
  maintenance and post-treatment performance.

- **Basis: Commercial framework.** MAVI proposes whole-home sediment and carbon treatment plus kitchen point-of-use RO
  with remineralization in [The Verified Home](https://mavilongevity.com/journal/the-verified-home).

  Caveat: this is a
  proprietary default, not a substitute for local testing or contaminant-specific treatment design.

- **Basis: Personal protocol.** Johnson describes RO plus remineralization and a drop from more than 300 to 25 mg/L TDS
  in his [home checklist](https://blueprint.bryanjohnson.com/blogs/news/14-changes-i-made-to-my-home).

  Caveat: this is
  an unverified individual example. TDS does not identify the contaminant or establish healthfulness.

- **Basis: Guideline/standard.** Place carbon-monoxide alarms near sleeping areas and maintain smoke alarms under local
  requirements. Romanian provisions route through `romanian-building-code`. CDC's
  [CO guidance](https://www.cdc.gov/carbon-monoxide/about/index.html) supports the proximity recommendation.

  Caveat: alarms reduce detection delay but do not replace source control, appliance servicing, or an
  evacuation plan.

- **Basis: Personal protocol.** Johnson recommends a monthly smoke-alarm test and adding CO detection in his
  [home checklist](https://blueprint.bryanjohnson.com/blogs/news/14-changes-i-made-to-my-home).

  Caveat: only the smoke
  test is given a monthly interval. Use local rules and each device's instructions for testing, maintenance, and
  replacement.

## Sleep, light, and acoustics

Researched/accessed 2026-08-10. Treat the bedroom as a recovery-critical room, while preserving individual needs,
safety, accessibility, and local daylight/noise constraints.

### Bedroom conditions

| Item                                                        | Basis                | Context and canonical source                                                                                                                                                                                | Material caveat                                                                                           |
| ----------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Bedroom temperature: 65–70 °F (18.3–21.1 °C)                | Expert synthesis     | Harvard [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf) offers this bedroom comfort guidance. | It is not a clinical sleep prescription. Bedding, humidity, age, illness, and preference matter.          |
| Sleep temperature: 17–19 °C, with 18 °C presented elsewhere | Commercial framework | MAVI gives 17–19 °C in [The Verified Home](https://mavilongevity.com/journal/the-verified-home) and 18 °C in [longevity architecture](https://mavilongevity.com/longevity-architecture).                    | This is a proprietary framework target, not a consensus value.                                            |
| Bedroom temperature: 18–20 °C                               | Personal protocol    | Johnson states this range in his [protocol](https://blueprint.bryanjohnson.com/blogs/news/bryan-johnsons-protocol).                                                                                         | It is an individual practice, not general design evidence.                                                |
| Bedroom noise: at most 30 dB LAeq,8h and 45 dB LAFmax       | Commercial framework | MAVI proposes these handover targets in [The Verified Home](https://mavilongevity.com/journal/the-verified-home).                                                                                           | These are proprietary interior commissioning targets, not universal residential or exterior-noise limits. |
| Blackout: 0.5 lux at the pillow                             | Commercial framework | MAVI proposes this in [longevity architecture](https://mavilongevity.com/longevity-architecture).                                                                                                           | Verify meter geometry and safety/navigation needs. This is not a standard.                                |

- **Basis: Peer-reviewed study.** Thermal conditions influence sleep through several mechanisms. Use the
  [thermal-environment sleep review](https://doi.org/10.1186/1880-6805-31-14) for background.

  Caveat: it does not
  establish one optimum setpoint for every resident or bedroom.

- **Basis: Expert synthesis.** Prefer a dark, quiet, controllable bedroom with warm/dim light before sleep and daylight
  in the morning. Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  gives this directional guidance. It does not provide residential lux, melanopic, or dB specifications.

### Light: timing, spectrum, and controls

| Item                                                                                 | Basis                | Context and canonical source                                                                                                                        | Material caveat                                                                                                                   |
| ------------------------------------------------------------------------------------ | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Daytime: at least 250 lx melanopic EDI at the eye throughout the daytime             | Peer-reviewed study  | The [Brown et al. expert consensus](https://doi.org/10.1371/journal.pbio.3001571) specifies vertical measurement at seated eye height, about 1.2 m. | Applies to healthy adults aged 18–55 with regular daytime schedules. Preserve visual, glare, safety, and individual requirements. |
| Evening: at most 10 lx melanopic EDI at the eye from at least 3 hours before bedtime | Peer-reviewed study  | The [Brown et al. expert consensus](https://doi.org/10.1371/journal.pbio.3001571) specifies vertical measurement at seated eye height, about 1.2 m. | It is a consensus recommendation with individual variability, not a guarantee of sleep outcome.                                   |
| Sleep environment: at most 1 lx ambient melanopic EDI at the eye                     | Peer-reviewed study  | The [Brown et al. expert consensus](https://doi.org/10.1371/journal.pbio.3001571) recommends making the sleep environment as dark as possible.      | Night navigation and care tasks may need up to 10 lx melanopic EDI at the eye. Safety and occupant needs remain controlling.      |
| MAVI evening target: at most 20 lx melanopic EDI                                     | Commercial framework | MAVI publishes this in [The Verified Home](https://mavilongevity.com/journal/the-verified-home).                                                    | MAVI gives 10 lx in its [answers](https://mavilongevity.com/answers). Its public targets conflict.                                |
| Morning device: 10,000 lx for 3–4 minutes                                            | Personal protocol    | Johnson describes his personal device use in his [protocol](https://blueprint.bryanjohnson.com/blogs/news/bryan-johnsons-protocol).                 | Device distance, ocular history, timing, and clinical contraindications are not a building-lighting specification.                |
| Dim red light about 2 hours before bed                                               | Personal protocol    | Johnson reports this in his [home checklist](https://blueprint.bryanjohnson.com/blogs/news/14-changes-i-made-to-my-home).                           | His accompanying 10-lux melatonin statement is uncited. Use controllable low light rather than promising a physiological result.  |

- **Basis: Peer-reviewed study.** Evaluate biological light using the measurement concepts in
  [Brown et al.](https://doi.org/10.1371/journal.pbio.3001571) and
  [CIE S 026](https://cie.co.at/publications/cie-system-metrology-optical-radiation-iprgc-influenced-responses-light-0),
  not photopic illuminance alone.

  Caveat: these provide a framework for measurement, not a complete residential control
  specification.

- **Basis: Design inference.** Give occupants independent daytime-admission, blackout, and low-level night-navigation
  controls. Commission scenes at actual eye/pillow positions, including reflected and outdoor spill light. This
  translates the measurement geometry and safety caveats in the
  [Brown et al. consensus](https://doi.org/10.1371/journal.pbio.3001571) into residential verification.

### Noise, blackout, and commissioning

- **Basis: Guideline/standard.** Use WHO's
  [environmental noise guidance](https://www.who.int/europe/publications/i/item/9789289053563) to distinguish exterior
  exposure from bedroom interior measurements.

  Caveat: a facade solution requires site-specific source, spectrum, peak,
  ventilation-opening, and building-envelope analysis.

- **Basis: Design inference.** Start with source reduction and isolation: locate bedrooms away from roads, plant,
  plumbing, and shared-impact zones and decouple noisy equipment. Then use enclosure, seals, and controllable
  ventilation. Masking can improve subjective comfort but is not a substitute for source control. Derive the exterior
  exposure basis from WHO's
  [environmental noise guidance](https://www.who.int/europe/publications/i/item/9789289053563).
- **Basis: Personal protocol.** Johnson uses noise masking and calls pink noise best in his
  [home checklist](https://blueprint.bryanjohnson.com/blogs/news/14-changes-i-made-to-my-home).

  Caveat: the superiority
  claim is uncited. Offer masking only as a user-tested option.

- **Basis: Design inference.** Commission darkness, noise, temperature stability, and ventilation in the occupied
  position, during representative nighttime conditions. Record methods and unresolved gaps rather than treating drawings
  or product ratings as results. MAVI's [Verified Home](https://mavilongevity.com/journal/the-verified-home) is a
  commercial example of making test methods and handover records explicit.

## Materials and pollutants

Researched/accessed 2026-08-10. Prioritize source elimination, separation, and maintainable cleaning over marketing
claims. Before disturbance or remediation, confirm regional rules and site history.

### Everyday source control

- **Basis: Expert synthesis.** Create an entry strategy that captures outdoor soil and pollutants: a shoe-removal
  preference where suitable, durable walk-off surfaces, and cleaning that does not redistribute dust. Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  also supports HEPA vacuuming.

  Caveat: accessibility, cultural practice, and cleaning execution determine whether the
  layout works.

- **Basis: Expert synthesis.** Select durable, cleanable low-emitting finishes and furnishings. Request transparent
  ingredient/disclosure documentation. Where feasible, exclude PFAS as a class. Harvard's
  [Healthier Materials Playbook](https://healthybuildings.hsph.harvard.edu/research/materials/harvards-healthier-materials-playbook/)
  describes that strategy.

  Caveat: documentation signals screening, not a complete exposure measurement or a guarantee
  for every installation.

- **Basis: Guideline/standard.** Treat composite-wood products, furnishings, and combustion as possible formaldehyde
  sources. EPA's
  [formaldehyde guidance](https://www.epa.gov/indoor-air-quality-iaq/what-should-i-know-about-formaldehyde-and-indoor-air-quality)
  identifies source and ventilation considerations.

  Caveat: odour is not a reliable concentration measure. Avoid
  asserting a safe room level without the applicable jurisdictional method.

- **Basis: Guideline/standard.** Prefer cleaning products with transparent ingredient information. EPA's
  [Safer Choice label](https://www.epa.gov/saferchoice/learn-about-safer-choice-label) is one screening signal.

  Caveat:
  a label does not make a product risk-free, and fragrance, dilution, use pattern, and ventilation still matter.

- **Basis: Design inference.** Reduce unnecessary plastic food-contact and non-stick use by choosing durable
  alternatives where function allows. Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  and Johnson's [home checklist](https://blueprint.bryanjohnson.com/blogs/news/14-changes-i-made-to-my-home) motivate
  the direction.

  Caveat: avoid claiming a particular pan or container produces a specific health outcome without
  product- and exposure-specific evidence.

- **Basis: Expert synthesis.** Avoid routine antimicrobial add-ons unless their purpose, exposure, and maintenance
  benefit are explicit. Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  recommends ordinary soap and water over antimicrobial products for routine home use.

  Caveat: do not infer lower
  infection risk from a treated surface in a normal dwelling.

### Legacy, site, and adjacent-space hazards

| Item                                                                             | Basis              | Context and canonical source                                                                                                                      | Material caveat                                                                                                          |
| -------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Pre-1978 housing for lead-safe renovation safeguards                             | Guideline/standard | EPA's [RRP consumer guidance](https://www.epa.gov/lead/renovation-repair-and-painting-rrp-program-consumers) uses this U.S. threshold.            | It supersedes Harvard's older pre-1980 heuristic. Local law, paint condition, and planned disturbance control the scope. |
| Radon mitigation at or above 4 pCi/L (150 Bq/m³); consider action from 2–4 pCi/L | Guideline/standard | EPA's [radon action-level guidance](https://www.epa.gov/radon/what-epas-action-level-radon-and-what-does-it-mean) provides these U.S. references. | Test result, device duration, floor level, season, local regulation, and mitigation verification matter.                 |

- **Basis: Guideline/standard.** Before renovation, assess lead and asbestos risk and use qualified, regulated practices
  where indicated. Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  flags both.

  Caveat: do not sample, disturb, or remediate based solely on a vintage heuristic.

- **Basis: Design inference.** Separate an attached garage from living space with robust air sealing, self-closing
  access where suitable, and no solvent, fuel, pesticide, or idling source migration. Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  supplies the source-control premise.

  Caveat: separation details must fit fire, ventilation, and local code
  requirements. Romanian provisions route through `romanian-building-code`. Odour reports require investigation, not
  masking.

- **Basis: Design inference.** Treat UV window film as a visual-comfort, heat, glare, and material-compatibility choice,
  not a health intervention by default. Johnson's
  [home checklist](https://blueprint.bryanjohnson.com/blogs/news/14-changes-i-made-to-my-home) is a personal UV-control
  example.

  Caveat: film can reduce daylight/circadian opportunity and affect glazing warranty or thermal stress. Assess
  the specific glazing system.

## Recovery, monitoring, and operations

Researched/accessed 2026-08-10. Make routine healthy behavior easy and measurement interpretable. Do not present
wellness amenities as clinically established residential requirements.

### Layout and optional amenities

- **Basis: Design inference.** Support regular movement with convenient circulation, safe storage, a flexible exercise
  area, daylight/ventilation where practical, and enough acoustic/privacy separation for the household.

  Caveat: this
  improves opportunity, not an assured activity or health outcome.

- **Basis: Personal protocol.** Johnson reports dry-heat bathing at 93 °C for 20 minutes and red/NIR exposure for 6 minutes in
  his [protocol](https://blueprint.bryanjohnson.com/blogs/news/bryan-johnsons-protocol).

  Caveat: these are personal
  practices, not building standards or universally safe doses. Medical conditions, medications, supervision, heat load,
  and equipment instructions can change suitability.

- **Basis: Commercial framework.** MAVI depicts heat bathing, 10 °C cold immersion, and infrared amenities in
  [longevity architecture](https://mavilongevity.com/longevity-architecture).

  Caveat: its public materials do not
  provide direct protocol evidence establishing those amenities as health requirements. Do not infer a target frequency,
  duration, or outcome.

- **Basis: Design inference.** Treat HBOT and IHHT as optional, specialist-led equipment rather than a baseline home
  feature. Johnson discusses them in his
  [personal protocol](https://blueprint.bryanjohnson.com/blogs/news/bryan-johnsons-protocol), but neither Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  nor the cited longevity frameworks supply a validated residential protocol. Safety, fire, pressure, electrical,
  ventilation, and clinical oversight are material constraints.

### Sensors and commissioning

- **Basis: Design inference.** Instrument the mechanisms being controlled: temperature/RH for moisture and comfort, CO2
  with occupancy context for ventilation inference, particles for filtration/source events, and smoke/CO alarms for
  acute safety. Choose sensors with documented range, accuracy, placement guidance, data export, and calibration method.
  Harvard's [CO2 calculator](https://healthybuildings.hsph.harvard.edu/tools/co2-calculator/) shows why room and
  occupancy context are necessary.
- **Basis: Expert synthesis.** Use Harvard's
  [CO2 calculator](https://healthybuildings.hsph.harvard.edu/tools/co2-calculator/) to record room volume,
  occupancy/activity, outdoor background, and steady-state assumptions.

  Caveat: no sensor dashboard by itself proves
  fresh-air delivery, filtration performance, or exposure.

- **Basis: Design inference.** Commission installed systems with a written baseline, sensor locations, clock/time-zone
  handling, representative operating modes, observed controls, and corrective actions. MAVI's
  [Verified Home](https://mavilongevity.com/journal/the-verified-home) is a commercial example of recording explicit
  test methods and handover evidence. When drift, replacement, or suspicious readings appear, validate against a known
  reference or manufacturer procedure.
- **Basis: Design inference.** Log trends and events rather than chasing isolated readings. Occupancy, cooking, windows,
  smoke periods, filter changes, cleaning, leaks, and maintenance make correlations auditable.

  Caveat: correlation in a
  household log does not establish causality.

### Operations, automation, and data

- **Basis: Expert synthesis.** Maintain high-efficiency filters on the condition and interval appropriate to the system.
  Harvard
  [Homes for Health](https://healthybuildings.hsph.harvard.edu/wp-content/uploads/2024/10/Harvard_Healthy_Buildings_Program_Homes_for_Health_May-2019_R1.8.pdf)
  suggests replacement every 3–6 months.

  Caveat: pressure drop, load, runtime, wildfire conditions, and manufacturer
  instructions can require a different interval.

- **Basis: Design inference.** Make automation fail safe and legible: retain manual overrides, alert on loss of
  sensing/actuation, avoid unsafe combustion or moisture lockouts, and document ownership of thresholds and maintenance.

  Caveat: automation cannot compensate for an undersized or uncommissioned physical system.

- **Basis: Commercial framework.** MAVI marks Apple Health, WHOOP, Oura, a bed-based sleep tracker, Awair, Airthings, and its other
  listed integrations forthcoming on its [homeowner page](https://mavilongevity.com/for-homeowners).

  Caveat: this
  documents product/integration status only, not availability, endorsement, interoperability, data quality, or clinical
  utility.

- **Basis: Design inference.** Treat wearable and home-sensor data as sensitive. Minimize collection, define retention
  and account ownership, secure access, and preserve operation when cloud services fail.

  Caveat: privacy and health-data
  obligations vary by jurisdiction and user arrangement.

### Evidence gaps to retain

- **Basis: Commercial framework.** MAVI's public methodology describes a proprietary 10-domain, 129-factor, weighted
  0–100 score in its [answers](https://mavilongevity.com/answers) and
  [references](https://mavilongevity.com/references).

  Caveat: its public methodology and standards crosswalk are
  incomplete, so the score is not an independently reproducible certification.

- **Basis: Commercial framework.** MAVI characterizes EMF evidence as partial and its bedroom distances and limits as
  precautionary in [The EMF Question](https://mavilongevity.com/journal/the-emf-question).

  Caveat: its page does not
  provide a study-level crosswalk. Do not upgrade those design choices into settled health requirements.

- **Basis: Commercial framework.** Do not retain a claimed 60% inflammatory-load reduction, curve-driven stress
  percentages, moss-wall IAQ, or specific bath/heat heart-rate-variability outcomes from MAVI materials such as its
  [home walkthrough](https://mavilongevity.com/home-walkthrough).

  Caveat: no adequate cited basis in this corpus
  supports presenting them as design evidence.
