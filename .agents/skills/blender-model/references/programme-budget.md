# Services scope and budget stages

Read this reference before you change services scope, PV, staged items or budget-linked model quantities.

Paths in this reference are relative to `model/` unless they start with `.agents/` or the repository root. The
[model guide](../../../../model/AGENTS.md) holds the invariants, and [the skill](../SKILL.md) the workflow and safety
rules.

## Services in the model

The services strategy lives in [systems](../../../../brief/systems.md) (`EN-*`) and controls in
[smart home](../../../../brief/smart-home.md) (`TECH-*`). The model shows only dimensional proxies: the technical room
holds the heat-pump indoor unit, DHW tank, MVHR unit, washer, dryer, electrical panel and network rack
(`RM-TECH-01`), the heat-pump outdoor unit stands on site (`EN-03`), and the roof carries the PV arrays whose module
count `requirements.json` `pv_modules` checks (`EN-07`). Sizes, routes, circuits, sensors and service clearances need
coordinated design, and the model changes no equipment quantity on its own.

## Budget linkage

`budget/data/project.json` owns categories, estimates, inclusion and completion stages (`La roșu`, `La gri`,
`La cheie`, `La mutat`, `Extra`). Staging an item in the budget never hides its geometry: later-stage furniture and
equipment stay modeled and visible. The budget area basis follows `LAY-06`; when an accepted change alters the gross
area, room areas, finish areas or equipment counts, reconcile the brief, the budget (through `just budget cost …`), the
maintained JSON and the saved blend.
