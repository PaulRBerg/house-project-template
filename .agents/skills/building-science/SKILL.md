---
coordination: exempt
name: building-science
skill-dependencies: [romanian-building-code]
description: >-
  Healthy home, indoor air quality, ventilation, filtration, humidity, circadian light, sleep, acoustics,
  low-emission materials, recovery, monitoring, healthy operation; high-performance envelope, airtightness,
  thermal bridges, windows, moisture, MVHR, heat pump, DHW, PV, controls, commissioning, resilience, Passive
  House principles as benchmarks, Casa Buhnici, climate inputs for the project's locality — for the household's house.
---

# Building Science

Evidence-disciplined healthy and high-performance design guidance for the household's house.

This skill is coordination-exempt: skip the ai-coord gate for its declared work. Explicitly authorized implementation or
other repository writes re-enter the gate.

This skill supplies evidence for healthy and high-performance design. Passive House is inspiration and benchmark only.
The household contracts no voluntary certification (`SITE-08`). The nZEB legal floor (`SITE-08`) and every Romanian
legal or dimensional rule route to the `romanian-building-code` skill. Research snapshot: 2026-08-10. Recheck at use
time.

## Working contract

- Frame the decision first: occupancy, climate, phase, and available evidence.
- Prefer source control before dilution. Separate a measured result, a target, and the intervention. Never silently
  promote one evidence class into another — calculated ≠ metered, certified-elsewhere ≠ this project, product rating
  ≠ delivered performance.
- Put conflicting targets side by side with provenance. Never average them. Treat product names only as documented
  examples.
- Every quantitative value carries units, boundary, date, canonical source URL, and a material caveat.
- The references keep `Basis` labels (and, in high-performance, `Scope` labels) as INTERNAL research metadata.
  User-facing answers explain provenance, applicability, and uncertainty in plain language, such as “according to the
  owner” or “not verified for this house”. Never print taxonomy tags.
- Escalate medical, combustion, electrical, structural, moisture, radon, water-treatment, hygrothermal, HVAC, and
  geotechnical questions to appropriately qualified Romanian professionals.

## Routing

- Read [healthy](references/healthy.md) when evaluating air, ventilation, filtration, cooking, moisture, water,
  materials, pollutants, legacy hazards, bedrooms, light, noise, recovery amenities, sensors, automation, or operations.
- Read [high-performance](references/high-performance.md) when evaluating Passive House principles or benchmark values,
  envelope, solar control, airtightness, windows, moisture and durability, ventilation equipment, heat pumps, DHW,
  renewables, controls, commissioning, resilience, or Casa Buhnici.
- Use the `romanian-building-code` skill for any legal minimum, nZEB compliance, urbanism, permit, or dimensional rule.

## Output

Lead with the decision. Give only material recommendations with plain-language provenance, source URL, and caveat. End
with the smallest verification or commissioning action.

Completion requires all of the following: no project fact is invented, every number carries its boundary and caveat,
legal minimum vs benchmark vs household preference stays distinct, and no certification is recommended.
