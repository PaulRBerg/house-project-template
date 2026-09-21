# Budget planner

This local-first React application tracks estimates, instalments, payments, assumptions, and cash flow for a house project. It persists the canonical document in `data/project.json`, rejects stale writes with revision conflicts, creates bounded local backups before saves, and exports the current document as JSON or CSV.

The included `Demo House` data is fictional. Its eight small placeholder costs exist only to demonstrate the four stages `La roșu`, `La gri`, `La cheie`, and `La mutat`; they are not market prices or a bill of quantities. Replace the project details, areas, groups, items, sources, and dates before using the planner for a real project.

## Setup

From the repository root:

```sh
bun install
cd budget
just dev
```

Open `http://127.0.0.1:5173`. The server binds to loopback and accepts writes only from the same loopback origin.

Use `just --list` to see the available development, check, and model-workflow recipes. Package manifests intentionally contain no script entries.

## Data model

Amounts are stored as integer EUR cents. The app uses `baseCents` for one budget and displays estimate-to-forecast ranges. `highCents` remains in the format for legacy compatibility; it does not set the displayed forecast. Instalments form the planned schedule; payments record actual cash movements. Eligible core items receive the configured contingency; land costs and movable goods never receive contingency.

The four milestone IDs and the four top-level group IDs are stable integration keys:

- milestones: `la-rosu`, `la-gri`, `la-cheie`, `la-mutat`
- groups: `construction`, `rough`, `finish`, `move`

Milestone dates are project data and may be changed to valid `YYYY-MM` values, including shared months. The schema requires each known milestone ID exactly once. Preserve the Romanian stage labels on both milestones and top-level groups, which supply the visible tabs.
