"""Execute parcel tasks through Blender's official MCP main-thread tool or headless Blender.

Load this file from the intended checkout by absolute path. ``run_task`` handles
bounded operations synchronously. ``start_render`` schedules the maintained render
queue once and returns a run-specific receipt that can be monitored from the shell;
background Blender (``-b``) never fires timers, so there it runs the queue before returning.
"""

from __future__ import annotations

import importlib
import re
import runpy
import sys
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
# Both engine modules are stdlib-only, so loading them leaves the engine package untouched.
_paths = runpy.run_path(str(SCRIPTS_DIR.parent / "engine" / "paths.py"))
_persistence = runpy.run_path(str(SCRIPTS_DIR.parent / "engine" / "persistence.py"))
BLEND = _paths["BLEND"]
RECEIPTS = _paths["RECEIPTS"]
RENDER_CANCEL = _paths["RENDER_CANCEL"]
_completion_receipt = _paths["completion_receipt"]
_RENDER_OUTPUTS = _paths["RENDER_OUTPUTS"]
_now = _persistence["utc_now"]
_read_json = _persistence["read_json"]
_sha256 = _persistence["sha256_file"]
_write_receipt = _persistence["atomic_write_json"]

_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
_REFRESH_MODULES = ("project_paths", "parcel_render_output")
_RENDER_STATE_KEY = "house-model/render-parcel"
# Background Blender reports a file freshly loaded from disk as dirty, so headless runs track
# unsaved changes themselves: a mutating task marks the session unsaved and `save` clears it.
_UNSAVED_STATE_KEY = "house-model/unsaved-changes"

_TASKS = {
    "build": {
        "script": "build_parcel_in_blender.py",
        "outputs": (),
        "requires_clean": False,
    },
    "update": {
        "script": "build_parcel_in_blender.py",
        "outputs": (),
        "requires_clean": False,
    },
    "export-geometry": {
        "script": "export_parcel_geometry_in_blender.py",
        "outputs": (_paths["ACTUAL_GEOMETRY"],),
        "requires_clean": True,
    },
    "export-drawings": {
        "script": "export_parcel_drawings_in_blender.py",
        "outputs": (_paths["DRAWING_GEOMETRY"],),
        "requires_clean": True,
    },
    "save": {
        "script": "save_parcel_in_blender.py",
        "outputs": (BLEND,),
        "requires_clean": False,
    },
    "present": {
        "script": "present_parcel_in_blender.py",
        "outputs": (),
        "requires_clean": False,
    },
}


def _new_run_id(prefix):
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def _options(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError("options must be a dict or None")
    return dict(value)


def _run_id(options, prefix):
    run_id = options.get("run_id") or _new_run_id(prefix)
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must contain only letters, digits, dot, underscore or dash")
    return run_id


def _bpy():
    import bpy

    return bpy


def _bootstrap_modules():
    """Load checkout-local support modules even after another checkout was used."""
    expected_scripts = SCRIPTS_DIR.resolve()
    scripts_text = str(expected_scripts)
    sys.path[:] = [entry for entry in sys.path if entry != scripts_text]
    sys.path.insert(0, scripts_text)
    for name in _REFRESH_MODULES:
        sys.modules.pop(name, None)
    modules = {name: importlib.import_module(name) for name in _REFRESH_MODULES}
    for name, module in modules.items():
        module_dir = Path(module.__file__).resolve().parent
        if module_dir != expected_scripts:
            raise RuntimeError(f"Loaded {name} from the wrong checkout: {module_dir}")
    return modules


def _preflight(expected_blend, *, requires_clean=False):
    """Check file identity before any task script can touch bpy data."""
    bpy = _bpy()
    expected = Path(expected_blend).expanduser().resolve()
    canonical = BLEND.resolve()
    if expected != canonical:
        raise ValueError(f"This runner belongs to {canonical}, not {expected}")
    open_blend = Path(bpy.data.filepath).expanduser().resolve()
    if open_blend != expected:
        raise RuntimeError(f"Wrong Blender file: open={open_blend}, expected={expected}")
    if not expected.is_file():
        raise FileNotFoundError(expected)
    if bpy.app.background:
        dirty = bool(_session_state(bpy).get(_UNSAVED_STATE_KEY))
    else:
        dirty = bool(getattr(bpy.data, "is_dirty", False))
    if requires_clean and dirty:
        raise RuntimeError("This saved-file operation requires clean Blender data")
    return {
        "blend": str(expected),
        "blend_sha256": _sha256(expected),
        "dirty": dirty,
    }


def _namespace(script, context, options):
    namespace = {
        "__file__": str(script),
        "__name__": "__blender_task__",
        "BLENDER_TASK_CONTEXT": context,
    }
    if context["operation"] == "render":
        namespace["PARCEL_PREVIEW"] = bool(options.get("preview", False))
        namespace["PARCEL_ENGINE"] = options["engine"]
        if "views" in options:
            namespace["PARCEL_VIEWS"] = list(options["views"])
    return namespace


def _execute(script, namespace):
    source = script.read_text()
    exec(compile(source, str(script), "exec"), namespace)  # noqa: S102 -- allowlisted checkout script


def _push_undo_boundary(task):
    result = _bpy().ops.ed.undo_push(message=f"Parcel MCP mutation boundary: {task}")
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender rejected the mutation boundary for {task}: {result}")


def run_task(task, expected_blend, options=None):
    """Run one bounded task and return its completed receipt."""
    if task not in _TASKS:
        raise ValueError(f"Unknown Blender task {task!r}; choose {sorted(_TASKS)}")
    options = _options(options)
    unknown = set(options) - {"run_id"}
    if unknown:
        raise ValueError(f"Unsupported options for {task}: {sorted(unknown)}")
    spec = _TASKS[task]

    _bootstrap_modules()
    input_state = _preflight(expected_blend, requires_clean=spec["requires_clean"])
    run_id = _run_id(options, task)
    receipt_path = RECEIPTS / f"{run_id}.json"
    if receipt_path.exists():
        raise FileExistsError(f"Run receipt already exists: {receipt_path}")
    script = SCRIPTS_DIR / spec["script"]
    receipt = {
        "run_id": run_id,
        "operation": task,
        "status": "running",
        "started_at": _now(),
        "input": input_state,
        "script": str(script),
        "outputs": [],
        "receipt": str(receipt_path),
    }
    _write_receipt(receipt_path, receipt)
    context = {
        "run_id": run_id,
        "operation": task,
        "expected_blend": input_state["blend"],
        "blend_sha256": input_state["blend_sha256"],
        "receipt": str(receipt_path),
    }
    try:
        if not spec["requires_clean"]:
            _push_undo_boundary(task)
            _session_state(_bpy())[_UNSAVED_STATE_KEY] = True
        _execute(script, _namespace(script, context, options))
        missing = [str(path) for path in spec["outputs"] if not path.exists()]
        if missing:
            raise RuntimeError(f"Task returned without declared outputs: {missing}")
    except BaseException as exc:
        receipt.update(
            status="failed",
            completed_at=_now(),
            error=f"{type(exc).__name__}: {exc}",
            traceback=traceback.format_exc(),
        )
        _write_receipt(receipt_path, receipt)
        raise
    receipt.update(
        status="complete",
        completion="complete",
        completed_at=_now(),
        outputs=[str(path) for path in spec["outputs"]],
    )
    if task == "save":
        receipt["output_blend_sha256"] = context["output_blend_sha256"]
        _session_state(_bpy())[_UNSAVED_STATE_KEY] = False
    _write_receipt(receipt_path, receipt)
    return receipt


def _session_state(bpy):
    """Per-process state that survives reloading this runner: the driver namespace."""
    driver_namespace = getattr(bpy.app, "driver_namespace", None)
    if driver_namespace is None:
        raise RuntimeError("Blender driver namespace is unavailable")
    return driver_namespace


def _render_timer(state, receipt_path, expected_blend, options):
    """Create the one-shot callback separately so its completion is testable."""

    def callback():
        receipt = _read_json(receipt_path)
        try:
            _bootstrap_modules()
            current = _preflight(expected_blend, requires_clean=True)
            receipt.update(status="running", started_at=_now(), input=current)
            _write_receipt(receipt_path, receipt)
            script = SCRIPTS_DIR / "render_parcel_in_blender.py"
            context = {
                "run_id": receipt["run_id"],
                "operation": "render",
                "expected_blend": current["blend"],
                "blend_sha256": current["blend_sha256"],
                "receipt": str(receipt_path),
            }
            _execute(script, _namespace(script, context, options))
            if "cancelled_outputs" in context:
                receipt.update(
                    status="cancelled",
                    completed_at=_now(),
                    outputs=context["cancelled_outputs"],
                )
                _write_receipt(receipt_path, receipt)
                return None
            mode = "preview" if options.get("preview", False) else "final"
            completion = _completion_receipt(options["engine"], mode)
            if not completion.is_file():
                raise RuntimeError(f"Render queue returned without {completion}")
            queue_receipt = _read_json(completion)
            if queue_receipt.get("status") != "complete":
                raise RuntimeError(f"Render queue is incomplete: {queue_receipt.get('status')}")
            receipt.update(
                status="complete",
                completion="complete",
                completed_at=_now(),
                outputs=[image["path"] for image in queue_receipt.get("images", [])],
                queue_receipt=str(completion),
            )
            _write_receipt(receipt_path, receipt)
        except BaseException as exc:  # noqa: BLE001 -- timer failures must persist a receipt
            receipt.update(
                status="failed",
                completed_at=_now(),
                error=f"{type(exc).__name__}: {exc}",
                traceback=traceback.format_exc(),
            )
            _write_receipt(receipt_path, receipt)
        finally:
            state.pop(_RENDER_STATE_KEY, None)

    return callback


def start_render(expected_blend, options=None):
    """Accept one render queue and return before the main-thread timer runs it.

    Background Blender runs the queue at once and returns its final ``status``.
    """
    options = _options(options)
    allowed = {"run_id", "preview", "views", "engine"}
    unknown = set(options) - allowed
    if unknown:
        raise ValueError(f"Unsupported render options: {sorted(unknown)}")
    if "preview" in options and not isinstance(options["preview"], bool):
        raise TypeError("preview must be a bool")
    options.setdefault("engine", "eevee")
    if options["engine"] not in _RENDER_OUTPUTS:
        raise ValueError(f"engine must be one of {sorted(_RENDER_OUTPUTS)}")
    if "views" in options:
        views = options["views"]
        if (
            not isinstance(views, (list, tuple))
            or not views
            or not all(isinstance(view, str) and view for view in views)
        ):
            raise ValueError("views must be a nonempty list of render stems")
        options["views"] = list(views)

    _bootstrap_modules()
    input_state = _preflight(expected_blend, requires_clean=True)
    bpy = _bpy()
    state = _session_state(bpy)
    pending = state.get(_RENDER_STATE_KEY)
    if pending:
        pending_path = Path(pending["receipt"])
        pending_status = (
            _read_json(pending_path).get("status") if pending_path.is_file() else "unknown"
        )
        if pending_status in {"accepted", "running", "unknown"}:
            raise RuntimeError(f"A parcel render is already pending: {pending_path}")
        state.pop(_RENDER_STATE_KEY, None)

    run_id = _run_id(options, "render")
    receipt_path = RECEIPTS / f"{run_id}.json"
    if receipt_path.exists():
        raise FileExistsError(f"Run receipt already exists: {receipt_path}")
    receipt = {
        "run_id": run_id,
        "operation": "render",
        "status": "accepted",
        "accepted_at": _now(),
        "input": input_state,
        "options": {key: value for key, value in options.items() if key != "run_id"},
        "script": str(SCRIPTS_DIR / "render_parcel_in_blender.py"),
        "outputs": [],
        "receipt": str(receipt_path),
    }
    _write_receipt(receipt_path, receipt)
    # A cancel request left from an earlier queue must not stop this one.
    RENDER_CANCEL.unlink(missing_ok=True)
    state[_RENDER_STATE_KEY] = {"run_id": run_id, "receipt": str(receipt_path)}
    callback = _render_timer(state, receipt_path, input_state["blend"], options)
    if bpy.app.background:
        callback()
        return {
            "accepted": True,
            "run_id": run_id,
            "operation": "render",
            "input": input_state,
            "receipt": str(receipt_path),
            "status": _read_json(receipt_path)["status"],
        }
    try:
        bpy.app.timers.register(callback, first_interval=0.1)
    except BaseException:
        state.pop(_RENDER_STATE_KEY, None)
        receipt.update(
            status="failed",
            completed_at=_now(),
            error="Timer registration failed",
            traceback=traceback.format_exc(),
        )
        _write_receipt(receipt_path, receipt)
        raise
    return {
        "accepted": True,
        "run_id": run_id,
        "operation": "render",
        "input": input_state,
        "receipt": str(receipt_path),
    }
