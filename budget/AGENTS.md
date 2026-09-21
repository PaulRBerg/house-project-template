# Budget workspace guidance

`budget/` is a local-first EUR budget planner built with React, Vite, TypeScript, Tailwind CSS, Bun, and Lucide icons. The development server listens on `127.0.0.1:5173` and persists to `data/project.json`.

## Commands

- Run recipes from this directory with `just <recipe>` or from the repository root with `just --justfile budget/justfile <recipe>`.
- Keep package manifests free of `scripts`; add project automation to `justfile`.
- Prefer the narrowest applicable recipe while developing. `just check` is the aggregate format, lint, typecheck, test, and build verification.
- `just blender-workflow-tests` exercises the repository model workflow without requiring an open Blender session.

## Application contracts

- Keep `data/project.json` valid under `src/domain/schema.ts`. Store EUR values as integer cents and calendar dates as ISO `YYYY-MM-DD` or `YYYY-MM` values according to the field schema.
- Preserve the milestone IDs `la-rosu`, `la-gri`, `la-cheie`, and `la-mutat`, and the top-level group IDs `construction`, `rough`, `finish`, and `move`. Milestone dates remain editable project data.
- Keep assumptions, ownership, completion, estimates, instalments, payments, and contingency as separate concepts. Avoid deriving semantic project decisions from labels.
- Preserve the revision contract: `GET /api/budget` returns `{ document, revision }`; `PUT /api/budget` requires `{ expectedRevision, document }`; stale writes return `409` with the latest snapshot.
- Keep the API restricted to direct loopback hosts and same-origin writes. Preserve request-size limits, schema validation, atomic replacement, and bounded backups in both development and preview.
- Keep JSON and CSV export safe for untrusted text. CSV cells must continue to neutralize spreadsheet formulas.

## Demo data

The checked-in seed is anonymous and fictional. It demonstrates eight costs across the four Romanian stage names without making pricing claims. Keep examples generic, sources empty unless they are public reusable evidence, and personal information out of source, fixtures, tests, labels, notes, and identifiers.

## UI and tests

- Preserve keyboard navigation, focus restoration, dialog modality, reduced-motion behavior, and light/dark themes when changing interactions or styling.
- Keep node tests in `*.test.ts` and browser-component tests in `*.test.tsx`; the Vitest projects select their environments by extension.
- Prefer structural assertions over snapshots for budget accounting, conflict handling, backup safety, cash flow, and exports.
