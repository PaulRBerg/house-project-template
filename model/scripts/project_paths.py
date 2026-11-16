"""Checkout-relative paths and fresh engine imports for the Blender scripts."""

import importlib
import runpy
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
# engine/paths.py is stdlib-only, so loading it here leaves the engine package untouched.
_paths = runpy.run_path(str(SCRIPTS_DIR.parent / "engine" / "paths.py"))
MODEL_DIR = _paths["MODEL_DIR"]
BLEND = _paths["BLEND"]
DESIGN = _paths["DESIGN"]
ASSETS = _paths["ASSETS"]
ASSET_CATALOG = _paths["ASSET_CATALOG"]
ACTUAL_GEOMETRY = _paths["ACTUAL_GEOMETRY"]
DRAWING_GEOMETRY = _paths["DRAWING_GEOMETRY"]
RENDERS = _paths["RENDERS"]
CYCLES_RENDERS = _paths["CYCLES_RENDERS"]
RENDER_CANCEL = _paths["RENDER_CANCEL"]
DRAWINGS_COMPLETE = _paths["DRAWINGS_COMPLETE"]
completion_name = _paths["completion_name"]


def load_engine_modules(*names):
    """Import ``engine.<name>`` modules freshly from this checkout, even after another one was used.

    Engine modules use relative imports, so they must load as part of the ``engine``
    package rather than through ``runpy.run_path``. The package is cleared once, so the
    returned modules share one set of engine dependencies.
    """
    model_text = str(MODEL_DIR)
    sys.path[:] = [entry for entry in sys.path if entry != model_text]
    sys.path.insert(0, model_text)
    for module_name in list(sys.modules):
        if module_name == "engine" or module_name.startswith("engine."):
            del sys.modules[module_name]
    modules = tuple(importlib.import_module(f"engine.{name}") for name in names)
    return modules[0] if len(modules) == 1 else modules
