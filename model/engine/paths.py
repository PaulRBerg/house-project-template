"""Checkout-relative model paths and artifact names shared by the engine and scripts.

Standard library only, with no relative imports, so Blender scripts can also load it
with ``runpy.run_path`` before the ``engine`` package is importable.
"""

from __future__ import annotations

from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = MODEL_DIR.parent
BRIEF = REPO_DIR / "brief"
BLEND = MODEL_DIR / "house.blend"
SCRIPTS = MODEL_DIR / "scripts"

DESIGN = MODEL_DIR / "design"
SCHEMA = DESIGN / "schema.json"
REQUIREMENTS = DESIGN / "requirements.json"

ASSETS = MODEL_DIR / "assets"
ASSET_CATALOG = ASSETS / "catalog.json"
ASSET_LIBRARY = ASSETS / "baseline-assets.blend"
SCENE_MANIFEST = ASSETS / "scene-manifest.json"

GENERATED = MODEL_DIR / ".generated"
RUNTIME_BUNDLE = GENERATED / "runtime.json"
ACTUAL_GEOMETRY = GENERATED / "actual-geometry.json"
DRAWING_GEOMETRY = GENERATED / "drawing-geometry.json"
PARCEL_AUDIT = GENERATED / "parcel-audit.json"
RECEIPTS = GENERATED / "blender-workflow"
# Sentinel `just render-cancel` writes; the pending render queue stops before its next view.
RENDER_CANCEL = RECEIPTS / "cancel-render"

RENDERS = MODEL_DIR / "renders"
CURRENT_RENDERS = RENDERS / "current"
# Cycles renders overwrite one flat set in place, without current/previous rotation.
CYCLES_RENDERS = MODEL_DIR / "renders-cycles"
RENDER_OUTPUTS = {"eevee": CURRENT_RENDERS, "cycles": CYCLES_RENDERS}
DRAWINGS_COMPLETE = "drawings-complete.json"

# User-owned notes that never count as model sources or brief records.
USER_OWNED_FILES = frozenset({"TODO.md", "PROMPT.md"})


def completion_name(mode: str) -> str:
    """File name of the success marker a finished ``preview`` or ``final`` queue leaves."""
    return f"{mode}-complete.json"


def completion_receipt(engine: str, mode: str) -> Path:
    """Success marker a finished ``preview`` or ``final`` queue leaves in its engine's output set."""
    return RENDER_OUTPUTS[engine] / completion_name(mode)
