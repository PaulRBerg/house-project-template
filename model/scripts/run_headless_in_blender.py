"""Run model tasks in background Blender through the same runner as the MCP workflow.

just model-headless new
just model-headless build save export-geometry export-drawings
just model-headless render [--preview] [--engine eevee|cycles] [stem ...]

``new`` saves a fresh empty ``model/house.blend`` from a factory-startup session and never
overwrites one. Other tasks run in order against the open canonical blend; ``render`` takes
the rest of the arguments and must come last. Run ``just model-compile`` before ``build``.
"""

import argparse
import importlib
import sys
from pathlib import Path

import bpy

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
runner = importlib.import_module("run_blender_task_in_blender")


def new_blend():
    if runner.BLEND.exists():
        raise FileExistsError(f"{runner.BLEND} exists; remove it first to start a new model")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(runner.BLEND))
    print("HEADLESS NEW BLEND", runner.BLEND)


def render(arguments):
    parser = argparse.ArgumentParser(prog="model-headless render")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--engine", default="eevee")
    parser.add_argument("views", nargs="*")
    parsed = parser.parse_args(arguments)
    options = {"preview": parsed.preview, "engine": parsed.engine}
    if parsed.views:
        options["views"] = parsed.views
    result = runner.start_render(runner.BLEND, options)
    print("HEADLESS RENDER", result["status"], result["receipt"])
    if result["status"] != "complete":
        raise RuntimeError(f"Render queue ended {result['status']}: {result['receipt']}")


def main(arguments):
    if not arguments:
        raise SystemExit(__doc__)
    if arguments[0] == "new":
        if len(arguments) > 1:
            raise SystemExit("`new` takes no further tasks")
        new_blend()
        return
    tasks, rest = arguments, []
    if "render" in arguments:
        index = arguments.index("render")
        tasks, rest = arguments[:index], arguments[index + 1 :]
    for task in tasks:
        receipt = runner.run_task(task, runner.BLEND)
        print("HEADLESS TASK", task, receipt["status"], receipt["receipt"])
    if "render" in arguments:
        render(rest)


main(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
