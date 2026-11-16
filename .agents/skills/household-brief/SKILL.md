---
coordination: exempt
name: household-brief
skill-dependencies: [building-science, romanian-building-code]
description:
  Use for reasoning about, reviewing, or developing the household's ideal-house design, including the household brief,
  rooms and daily life, budget and priority conflicts, site and architecture, healthy-home goals, technology, garden,
  resilience, or inspiration evidence.
---

# Household Brief

Route and interpret the household brief without inventing project facts or silently changing decisions.

This skill is coordination-exempt: skip the ai-coord gate for its declared work. Explicitly authorized implementation or
other repository writes re-enter the gate.

## Workflow

1. Classify the task as `narrow topical`, `whole-house/integrated`, `preference update`, or
   `conflict/feasibility review`.
2. For a narrow topical task or preference update, read only the affected household records. For a
   whole-house/integrated or conflict/feasibility task, read every current record catalogued below.
3. Treat `brief/` alone as authority for household decisions, priorities, and completion stages. For budgeting work,
   treat `budget/data/project.json` as the operational authority for budget categories, estimates, inclusion,
   ownership/completion state, instalments, and payments. This skill routes records and specialists. It does not add
   household rules. Use `building-science` for current healthy-home and high-performance evidence (air, humidity,
   filtration, materials, circadian, acoustics, sleep, recovery, monitoring, envelope, airtightness, energy systems,
   Casa Buhnici, and Passive House as benchmark only). Use `romanian-building-code` for every Romanian legal,
   urbanism, permit, nZEB and dimensional rule. Preserve their ownership boundary rather than duplicating or
   reconciling guidance here.
4. Treat every recorded direction as accepted. Use `La roșu`, `La gri`, `La cheie`, `La mutat`, and `Extra` only to
   state when its result is complete. Factual introductory records may have no stage. Read flexibility, product choice,
   and unresolved verification from the decision prose rather than inventing a decision status.
5. Flag any proposal that conflicts with an accepted decision and offer a compatible direction. Do not silently accept
   the conflict or invent a compromise.
6. Distinguish household preference, inspiration, law or standard, specialist guidance, and project-specific unknown.
   Preserve the specialist skill's provenance, source URLs, scope and caveats in plain language. Do not print its
   internal evidence labels. Let current evidence update external facts and unresolved factual guidance.
   Never silently rewrite a recorded household preference. Expose the conflict and request or record a new household
   decision only when authorized.
7. Do not force a choice where the record explicitly preserves flexibility or requires later project evidence. Ask
   only for a missing household decision that materially controls the answer.
8. Direct live questions governed by law, site data, professional design, testing, or commissioning to appropriate
   project-team verification.
9. When a design change is accepted, reconcile affected decisions, quantities and cost scope. The brief conventions'
   sync section (`Geometrie și sincronizare`) sets how and when to surface model drift.

## Household records

- Read [brief record conventions](../../../brief/README.md) for completion-stage meanings, stable record IDs, and
  citation conventions.
- Read [project](../../../brief/project.md) for household composition, the parcel, budget boundaries, calendar,
  or priority tradeoffs. The all-in budget is explored iteratively in `budget/`. Follow `HH-03` instead of imposing
  a fixed target or cap.
- Read [architecture](../../../brief/architecture.md) for siting, form, programme, topology, circulation, acoustic
  separation, daylight, or performance intent. Use `building-science` to evaluate the technical performance path and
  `romanian-building-code` for legal limits, setbacks, heights, stairs, and circulation dimensions.
- Read [rooms and furnishings](../../../brief/rooms-and-furnishings.md) for room use, occupancy, hosting, bathrooms,
  laundry, storage, furniture, appliances, sanitary fixtures, or media use.
- Read [interiors](../../../brief/interiors.md) for the whole-house interior language, palette, finishes, materials,
  detailing, acoustics, lighting character, or room-specific stylistic expression.
- Read [systems](../../../brief/systems.md) for comfort, fresh air, water, solar power, backup, sensing, commissioning,
  maintainability, and healthy-air decisions. Use `building-science` for technical and health evidence and
  `romanian-building-code` for nZEB compliance.
- Read [smart home](../../../brief/smart-home.md) for controls, automation, AI authority, local operation, data,
  cameras, voice, access control, or security.
- Read [outdoor](../../../brief/outdoor.md) for garden and terrace life, planting, play, cars, bicycles,
  access, or upkeep.
- Read [existing assets](../../../brief/existing-assets.md) when budgeting, specifying, placing, powering, connecting,
  or planning around furniture and personal devices the household already owns and intends to bring to the house.
- Read [references and inspirations](../../../brief/references.md) for evidence types, Casa Buhnici,
  Passive House and nZEB distinctions, healthy-home inspirations, project-specific uncertainties, or the household's
  reading list. Use `building-science` for current conclusions from those sources.

## Output

Lead with the decision. Identify the applicable accepted decisions, completion stages, material conflicts, and
explicitly unresolved checks. When a specialist skill applies, retain its provenance, source URLs, scope, and caveats
while keeping them distinct from household stages. Name the next household decision only when one is genuinely needed.
Finish when the concise, decision-led prose accounts for every materially applicable recorded decision.
