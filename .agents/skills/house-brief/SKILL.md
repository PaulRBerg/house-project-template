---
name: house-brief
description: Route, review, and update a portable house-project brief while preserving decision authority, statuses, and evidence boundaries.
---

# House brief

Use this skill to reason about, review, or update the project brief, programme, priorities, site, layout, style, systems, technology, landscape, assets, or evidence.

## Authority and method

1. Read [brief conventions](../../../brief/README.md) and only the records relevant to the request. Read all brief records for a whole-house conflict or integration review.
2. Treat `brief/` as the authority for accepted household decisions and statuses. Treat `budget/data/project.json` as the authority for budget categories, estimates, inclusion, ownership, completion, instalments, and payments.
3. Preserve `required`, `preferred`, `phased`, and `deferred`. Never promote an inspiration, regulation, professional recommendation, estimate, or unknown into a household decision.
4. Cite the record that owns a decision. Flag conflicts with `required` decisions instead of silently reconciling them.
5. Distinguish preference, inspiration, evidence, regulation, specialist guidance, and project-specific unknowns. Request the location and jurisdiction before making location-dependent claims.

## Change boundary

When an accepted decision changes, reconcile affected brief requirements, budget quantities, and maintained model geometry. A pure price, inclusion, or accounting-state change does not alter the brief or require unrelated geometry work. Model, survey, compliance, and construction claims require appropriate evidence and professionals.

## Routing

- Use `healthy-home-design` for health-specific air, moisture, light, sleep, acoustics, materials, and operations guidance.
- Use `high-performance-home` for building physics, energy, envelope, systems, and local energy-regulation research.
- Use `price-estimator` for current market evidence.
- Use `blender-house` for saved-model work and `gen-3d-renders` for illustrative concept imagery.

Return the relevant decisions, their status, conflicts or unknowns, and the next evidence needed. Do not invent a programme, site, geometry, budget, compliance outcome, or household requirement.
