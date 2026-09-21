---
name: price-estimator
description: Research current, traceable local price evidence for house-project cost items and return concise EUR estimates with assumptions and sources.
---

# Price estimator

Research comparable current offers for requested budget items. This skill reports evidence; it does not change the budget, contact suppliers, request quotes, or make purchases.

## Method

1. Read the relevant `budget/data/project.json` records and linked brief decisions. Use the recorded quantity only when its definition suits the quoted rate; flag conflicts instead of changing either record.
2. Ask for or identify the project location, jurisdiction, currency context, quality level, quantity, supply-versus-installation scope, taxes, delivery, access constraints, and required date. Do not assume a country, provider, or local rate.
3. Obtain current evidence through available search, browser, supplier, public procurement, or professional-rate capabilities. Search results alone do not establish a price; record direct source links and access dates.
4. Compare like-for-like scope. State exclusions, quantity uncertainty, tax treatment, currency conversion basis, and confidence. Return EUR as the retained budget base, while preserving raw-currency source context where needed.
5. If the quantity is unknown or comparison is weak, return a clearly labelled unit-rate range instead of an invented total.

## Deliverable

Return a compact table of item, comparable scope, quantity basis, EUR range, source links, access date, and caveat. Separate supplier quotes, market indications, and design allowances. Price research is not affordability evidence, a binding quotation, or permission to alter a household requirement.
