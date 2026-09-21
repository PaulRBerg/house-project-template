# Budget data guidance

`project.json` is the operational source for budget categories, estimates, inclusion, ownership, completion, instalments, and payments. The included `Demo House` document is fictional template data, not a quote, a measured bill of quantities, or advice about a real project.

## Stable structure

- Keep exactly one milestone for each ID: `la-rosu`, `la-gri`, `la-cheie`, and `la-mutat`. Dates are editable valid `YYYY-MM` values.
- Keep the top-level group IDs `construction`, `rough`, `finish`, and `move` aligned with those milestones.
- Keep project, group, item, source, instalment, and payment IDs globally unique and stable after other records refer to them.
- Keep `builtAreaSqm` consistent with the project's declared total built floor-area basis and every estimate with `quantityBasis: "built-area"`. For multiple storeys, use the total applicable floor area rather than only the footprint. The single-storey demo uses 48 m² for its 8 m by 6 m external footprint.

## Accounting

- Store all money as integer EUR cents. A quantity-rate estimate stores cents per unit and derives its total by multiplying quantity by rate.
- The app uses `baseCents` for one budget and displays estimate-to-forecast ranges. Retain `highCents` for legacy data and selector compatibility, with base less than or equal to high; it is not the upper end of the displayed range.
- Instalments hold the base-scenario plan. Payments must reference an instalment belonging to the same item.
- Set `contingencyEligible` only for core costs other than land. Movable goods are `costScope: "movable"`, `costType: "movable-good"`, and never receive contingency.
- Keep included, archived, ownership, and completion states explicit; do not infer them from cost or payment values.

## Evidence and examples

- The eight checked-in estimates and instalments are deliberately small fictional placeholders. Their notes must continue to say that they are fictional and not price claims.
- Real estimates should cite reusable public sources in `sources` or carry a clear note explaining their provisional basis. Each item may reference sources by stable ID.
- Keep personal names, addresses, private documents, supplier negotiations, and unpublished quotes out of the reusable template.
