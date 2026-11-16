"""Apply the host-compiled runtime bundle to the open canonical blend without saving."""

import bpy
from project_paths import load_engine_modules

context = globals().get("BLENDER_TASK_CONTEXT") or {}
runtime, paths = load_engine_modules("blender_runtime", "paths")
bundle = runtime.read_runtime_bundle(paths.RUNTIME_BUNDLE)
# `build` always rebuilds from scratch; `update` applies the change set that
# `just model-compile` computed against the previous runtime.json.
mode = "fresh" if context.get("operation") == "build" else bundle["change_set"]["mode"]
if mode == "noop":
    print("PARCEL BUILD SKIPPED: runtime bundle unchanged since the previous compile")
else:
    result = runtime.apply_runtime_bundle(bpy, bundle, mode=mode)
    print("PARCEL BUILD APPLIED", result)
