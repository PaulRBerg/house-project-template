from __future__ import annotations

import subprocess
import sys

import pytest

from engine import paths

# Modules Blender imports through the runner or scripts; Blender's Python has no Shapely,
# jsonschema or host compiler.
BLENDER_MODULES = (
    "assets",
    "blender_datablocks",
    "blender_runtime",
    "furnishings",
    "materials",
    "mesh_descriptors",
    "paths",
    "persistence",
    "presentation",
    "render_inventory",
    "rendering",
    "site_components",
    "transforms",
)
HOST_ONLY = ("shapely", "jsonschema", "engine.compiler", "engine.design_package", "engine.geometry")


@pytest.mark.parametrize("module", BLENDER_MODULES)
def test_blender_modules_do_not_import_host_dependencies(module):
    code = f"""
import builtins, sys
sys.path.insert(0, {str(paths.MODEL_DIR)!r})
original = builtins.__import__
def guarded(name, globals=None, locals=None, fromlist=(), level=0):
    resolved = name if level == 0 else f"engine.{{name}}" if name else "engine"
    if resolved.split(".")[0] in {{"shapely", "jsonschema"}} or resolved in {HOST_ONLY!r}:
        raise AssertionError(f"{module} imported {{resolved}}")
    return original(name, globals, locals, fromlist, level)
builtins.__import__ = guarded
import engine.{module}
assert not set({HOST_ONLY!r}) & set(sys.modules)
"""
    result = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
