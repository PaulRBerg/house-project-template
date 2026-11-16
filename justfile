set default-list := true
set dotenv-load := false

import "node_modules/@prb/devkit/just/settings.just"

# Budget app development and validation.
mod budget

model_uv := "uv run --project model"
# Blender executable for headless model tasks; set BLENDER when it is not on PATH.
blender := env("BLENDER", "blender")
supplemental_ox_paths := [
    ".lintstagedrc.mjs",
    ".prettierrc.mjs",
    ".vscode/settings.json",
    "oxfmt.config.ts",
    "oxlint.config.ts",
    "package.json",
]

# Install the Husky Git hooks after `bun install`; the pre-commit hook runs lint-staged over staged files.
[group("setup")]
@setup:
    na husky

# Check supplemental workspace scripts and configuration with Oxlint and Oxfmt.
# Pass `budget` explicitly for a standalone Ox check of the app (`just budget lint` covers it day to day).
[group("checks")]
[positional-arguments]
@ox-check +paths=supplemental_ox_paths:
    na oxlint --format agent --config oxlint.config.ts --no-error-on-unmatched-pattern "$@"
    na oxfmt --check --config oxfmt.config.ts --no-error-on-unmatched-pattern "$@"
alias oc := ox-check

# Apply Oxlint's safe fixes and formatting to supplemental workspace scripts and configuration.
[group("checks")]
[positional-arguments]
@ox-write +paths=supplemental_ox_paths:
    na oxlint --fix --format agent --config oxlint.config.ts --no-error-on-unmatched-pattern "$@"
    na oxfmt --write --config oxfmt.config.ts --no-error-on-unmatched-pattern "$@"
alias ow := ox-write

# Check the model Python project with Ruff's linter and formatter.
[group("checks")]
[positional-arguments]
@py-check +paths="model":
    {{ model_uv }} ruff check "$@"
    {{ model_uv }} ruff format --check "$@"
alias pc := py-check

# Apply Ruff's safe fixes and formatting to the model Python project.
[group("checks")]
[positional-arguments]
@py-write +paths="model":
    {{ model_uv }} ruff check --fix "$@"
    {{ model_uv }} ruff format "$@"
alias pw := py-write

# Check the project-local skills under `.agents` for metadata, dependency and completion-contract drift; skips when the optional `ai-skillet` CLI is missing.
[group("checks")]
@skill-check:
    if command -v ai-skillet >/dev/null; then ai-skillet doctor --root .agents; else echo "ai-skillet not installed; skipping skill check"; fi
alias sc := skill-check

# Run every read-only check except Blender renders and model builds: Ox, Ruff, the budget app and the skills.
[group("checks")]
@full-check:
    just ox-check
    just py-check
    just budget check
    just skill-check
alias fc := full-check

# Compile design/, engine/ and assets/ into the runtime bundle that `run_task('build'|'update')` applies.
[group("model")]
@model-compile:
    PYTHONPATH=model {{ model_uv }} python -m engine.runtime_bundle

# Regenerate the project-authored wallpaper, mural and tile PNGs under assets/interior.
[group("model")]
@model-wallpapers:
    {{ model_uv }} python model/scripts/generate_wallpapers.py

# Fetch a CC0 Poly Haven texture or HDRI into assets/<group> and record it in that group's sources.json.
[group("model")]
@model-asset group asset_id resolution="2k":
    {{ model_uv }} python model/scripts/fetch_polyhaven_asset.py {{ group }} {{ asset_id }} {{ resolution }}

# Run model tasks in background Blender: `new` saves an empty model/house.blend, or chain tasks such as `build save export-geometry export-drawings render --preview`.
[group("model")]
[positional-arguments]
@model-headless +args:
    if [ "$1" = new ]; then \
        "{{ blender }}" -b --factory-startup --python-exit-code 1 --python model/scripts/run_headless_in_blender.py -- "$@"; \
    else \
        "{{ blender }}" -b model/house.blend --python-exit-code 1 --python model/scripts/run_headless_in_blender.py -- "$@"; \
    fi

# Run the complete host-side procedural engine suite with pytest.
[group("model")]
@model-tests:
    {{ model_uv }} pytest model/tests

# Stop the pending Blender render queue before its next view; the view in progress finishes.
[group("model")]
@render-cancel:
    PYTHONPATH=model {{ model_uv }} python -c 'from engine.paths import RENDER_CANCEL; RENDER_CANCEL.parent.mkdir(parents=True, exist_ok=True); RENDER_CANCEL.touch(); print(RENDER_CANCEL)'

# Audit the latest saved parcel export independently of Blender.
[group("model")]
@parcel-audit:
    {{ model_uv }} python model/scripts/audit_parcel.py

# Draft both floors from the latest clean saved-model drawing export.
[group("model")]
@parcel-drawings:
    {{ model_uv }} python model/scripts/draw_parcel_plans.py

# Fail when `model/renders` holds more than `current/` and one flat `previous/` set, or a set holds nested or non-PNG output.
[group("model")]
@render-check:
    PYTHONPATH=model {{ model_uv }} python -m engine.render_layout
