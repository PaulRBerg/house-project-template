# Project guidance

This template begins with fictional, unaccepted records. `brief/` is the semantic authority for household decisions. `budget/data/project.json` is the operational authority for budget taxonomy, estimates, inclusion, ownership, completion, instalments, and payments. `model/house.blend` expresses the current working geometry; its initial demo is not an accepted design.

When a decision changes, reconcile the affected brief requirements, budget quantities and model geometry together. A price or accounting change alone does not alter a household requirement or require unrelated model work. Preserve stable brief IDs and the literal statuses `required`, `preferred`, `phased`, and `deferred`.

Keep preferences separate from evidence, regulations, professional guidance, and project-specific unknowns. Survey, design, cost, compliance, permits, and construction information require appropriate professionals and project evidence.

Use the project skills under `.agents/skills/` when their scope fits: `house-brief` for decisions, `blender-house` for model work, `gen-3d-renders` for concept images, `healthy-home-design` and `high-performance-home` for evidence-led guidance, and `price-estimator` for current pricing research. Ask for the project location and jurisdiction before making location-dependent claims.

Run the narrowest applicable task in `budget/justfile`. `just --justfile budget/justfile check` verifies the budget app, and `just --justfile budget/justfile blender-workflow-tests` verifies the model workflow harness. Keep task recipes in `budget/justfile`; do not add `scripts` to package manifests.
