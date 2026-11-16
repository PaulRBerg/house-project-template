"""Focused unit tests for the Blender MCP task transport (no Blender process)."""

from __future__ import annotations

import ast
import hashlib
import json
import runpy
import sys
import types
from copy import deepcopy
from pathlib import Path

import pytest

from engine import paths, persistence


@pytest.fixture
def runner(load_script_module):
    return load_script_module("run_blender_task_in_blender")


@pytest.fixture
def sandbox(runner, tmp_path, monkeypatch, fake_bpy):
    """Point the runner at a temporary scripts dir, saved blend, receipts and fake ``bpy``."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    blend = tmp_path / "house.blend"
    blend.write_bytes(b"saved input")
    fake = fake_bpy(blend)
    receipts = tmp_path / "receipts"
    monkeypatch.setattr(runner, "SCRIPTS_DIR", scripts)
    monkeypatch.setattr(runner, "BLEND", blend)
    monkeypatch.setattr(runner, "RECEIPTS", receipts)
    monkeypatch.setattr(runner, "_bpy", lambda: fake)
    monkeypatch.setattr(runner, "_bootstrap_modules", lambda: {"project_paths": object()})
    return types.SimpleNamespace(scripts=scripts, blend=blend, receipts=receipts, fake=fake)


def write_image(root: Path, name: str, content: bytes) -> Path:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def test_bootstrap_replaces_stale_checkout_modules(runner, tmp_path, monkeypatch):
    scripts = tmp_path / "model" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "project_paths.py").write_text("MARKER = 'fresh'\n")
    (scripts / "parcel_render_output.py").write_text(
        "import project_paths\nMARKER = project_paths.MARKER\n"
    )
    for name in runner._REFRESH_MODULES:
        stale_module = types.ModuleType(name)
        stale_module.__file__ = f"/wrong/{name}.py"
        stale_module.MARKER = "stale"
        monkeypatch.setitem(sys.modules, name, stale_module)
    monkeypatch.setattr(runner, "SCRIPTS_DIR", scripts)

    original_sys_path = list(sys.path)
    try:
        modules = runner._bootstrap_modules()
        assert modules["project_paths"].MARKER == "fresh"
        assert modules["parcel_render_output"].MARKER == "fresh"
        assert all(
            Path(module.__file__).resolve().parent == scripts.resolve()
            for module in modules.values()
        )
    finally:
        sys.path[:] = original_sys_path


def test_wrong_file_guard_preserves_prior_output(runner, sandbox, tmp_path, monkeypatch):
    prior = tmp_path / "prior-output.json"
    prior.write_text("preserve me")
    sandbox.fake.data.filepath = str(tmp_path / "other.blend")
    task = {"script": "never.py", "outputs": (prior,), "requires_clean": False}
    monkeypatch.setattr(runner, "_TASKS", {"save": task})

    with pytest.raises(RuntimeError, match="Wrong Blender file"):
        runner.run_task("save", sandbox.blend)
    assert prior.read_text() == "preserve me"
    assert not sandbox.receipts.exists()


def test_each_task_uses_a_fresh_namespace(runner, sandbox, tmp_path, monkeypatch):
    blend = sandbox.blend
    output = tmp_path / "namespace.txt"
    task_script = sandbox.scripts / "probe.py"
    task_script.write_text(
        "from pathlib import Path\n"
        f"assert Path(__file__).resolve() == Path({str(task_script)!r}).resolve()\n"
        "assert __name__ == '__blender_task__'\n"
        "counter = globals().get('counter', 0) + 1\n"
        f"Path({str(output)!r}).write_text(str(counter))\n"
    )
    task = {"script": task_script.name, "outputs": (output,), "requires_clean": False}
    monkeypatch.setattr(runner, "_TASKS", {"probe": task})

    first = runner.run_task("probe", blend, {"run_id": "probe-one"})
    second = runner.run_task("probe", blend, {"run_id": "probe-two"})
    assert first["status"] == "complete"
    assert second["status"] == "complete"
    assert output.read_text() == "1"


def test_script_exception_propagates_and_records_failure(runner, sandbox, monkeypatch):
    (sandbox.scripts / "failure.py").write_text("raise LookupError('deliberate')\n")
    task = {"script": "failure.py", "outputs": (), "requires_clean": False}
    monkeypatch.setattr(runner, "_TASKS", {"failure": task})

    with pytest.raises(LookupError, match="deliberate"):
        runner.run_task("failure", sandbox.blend, {"run_id": "failed-run"})
    receipt = json.loads((sandbox.receipts / "failed-run.json").read_text())
    assert receipt["status"] == "failed"
    assert "deliberate" in receipt["traceback"]


def test_missing_declared_output_is_a_task_failure(runner, sandbox, tmp_path, monkeypatch):
    (sandbox.scripts / "incomplete.py").write_text("pass\n")
    task = {
        "script": "incomplete.py",
        "outputs": (tmp_path / "missing.json",),
        "requires_clean": False,
    }
    monkeypatch.setattr(runner, "_TASKS", {"incomplete": task})

    with pytest.raises(RuntimeError, match="declared outputs"):
        runner.run_task("incomplete", sandbox.blend, {"run_id": "incomplete-run"})
    receipt = json.loads((sandbox.receipts / "incomplete-run.json").read_text())
    assert receipt["status"] == "failed"


def test_drawing_export_aggregates_multipart_rooms_and_rejects_missing_room(scripts_dir):
    source_path = scripts_dir / "export_parcel_drawings_in_blender.py"
    tree = ast.parse(source_path.read_text(), filename=str(source_path))
    helpers = ast.Module(
        body=[
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {"add_room_part", "finalize_rooms"}
        ],
        type_ignores=[],
    )
    namespace = {}
    exec(compile(helpers, str(source_path), "exec"), namespace)  # noqa: S102

    rooms = {}
    namespace["add_room_part"](rooms, "G-HALL", [[[0, 0], [1, 0], [1, 1], [0, 1]]])
    namespace["add_room_part"](rooms, "G-HALL", [[[1, 0], [3, 0], [3, 1], [1, 1]]])
    namespace["add_room_part"](rooms, "G-LIV", [[[0, 1], [2, 1], [2, 3], [0, 3]]])

    # Rooms keep the design's order.
    result = namespace["finalize_rooms"](rooms, ["G-LIV", "G-HALL"], "G")
    assert [room["id"] for room in result] == ["G-LIV", "G-HALL"]
    hall = result[1]
    assert len(hall["polygons"]) == 2
    assert hall["area_m2"] == pytest.approx(3.0)
    with pytest.raises(AssertionError, match=r"missing=\['G-TECH'\]"):
        namespace["finalize_rooms"](rooms, ["G-LIV", "G-TECH", "G-HALL"], "G")


def test_render_acceptance_duplicate_rejection_and_incomplete_failure(
    runner, sandbox, tmp_path, monkeypatch
):
    (sandbox.scripts / "render_parcel_in_blender.py").write_text("pass\n")
    blend, fake, receipts = sandbox.blend, sandbox.fake, sandbox.receipts
    monkeypatch.setattr(
        runner,
        "_completion_receipt",
        lambda _, mode: tmp_path / "renders" / f"{mode}-complete.json",
    )

    accepted = runner.start_render(blend, {"run_id": "render-test", "preview": True})
    assert accepted["accepted"]
    with pytest.raises(RuntimeError, match="already pending"):
        runner.start_render(blend, {"run_id": "render-other"})
    callback, interval = fake.app.timers.callbacks[0]
    assert interval == 0.1
    assert callback() is None

    receipt = json.loads((receipts / "render-test.json").read_text())
    assert receipt["status"] == "failed"
    assert "returned without" in receipt["error"]
    assert runner._RENDER_STATE_KEY not in fake.app.driver_namespace


VIEW_ENGINES = {"eevee": "BLENDER_EEVEE", "cycles": "CYCLES"}


def test_render_rejects_unknown_engine(runner, tmp_path):
    with pytest.raises(ValueError, match="engine must be one of"):
        runner.start_render(tmp_path / "house.blend", {"engine": "workbench"})


@pytest.fixture
def render_output(load_script_module, tmp_path, monkeypatch):
    module = load_script_module("parcel_render_output")
    root = tmp_path / "renders"
    monkeypatch.setattr(module, "RENDERS", root)
    return module, root


def test_render_runner_clears_stale_cancel_and_records_cancellation(
    runner, sandbox, tmp_path, monkeypatch
):
    (sandbox.scripts / "render_parcel_in_blender.py").write_text(
        "BLENDER_TASK_CONTEXT['cancelled_outputs'] = ['first.png']\n"
    )
    blend, fake, receipts = sandbox.blend, sandbox.fake, sandbox.receipts
    cancel = tmp_path / "cancel-render"
    cancel.touch()
    monkeypatch.setattr(runner, "RENDER_CANCEL", cancel)

    runner.start_render(blend, {"run_id": "render-cancelled"})
    assert not cancel.exists()
    callback, _ = fake.app.timers.callbacks[0]
    assert callback() is None

    receipt = json.loads((receipts / "render-cancelled.json").read_text())
    assert (receipt["status"], receipt["outputs"]) == ("cancelled", ["first.png"])
    assert runner._RENDER_STATE_KEY not in fake.app.driver_namespace


@pytest.fixture
def render_queue(scripts_dir, tmp_path, monkeypatch, fake_bpy):
    """Run the canonical queue over two fake plan views; returns its output dirs and context."""
    blend = tmp_path / "house.blend"
    blend.write_bytes(b"saved geometry")
    outputs = {"eevee": tmp_path / "renders" / "current", "cycles": tmp_path / "renders-cycles"}
    cancel = tmp_path / "cancel-render"
    fake = fake_bpy(blend)
    fake.app.version_string = "test"
    fake.data.scenes = {"Upper": types.SimpleNamespace(objects={"Camera": object()})}
    rendered_stems = []

    def render_image(_bpy, *, view, quality, output_path, sun):
        assert sun == ("key", "fill")
        rendered_stems.append(view["stem"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"rendered image")
        return {"seconds": 1, "settings": {"engine": quality["engine"]}}

    views = {"upper": "Plan etaj.png", "lower": "Plan parter.png"}
    design = tmp_path / "design"
    design.mkdir()
    (design / "style.json").write_text(json.dumps({"cameras": []}))
    modules = {
        "persistence": persistence,
        "render_inventory": types.SimpleNamespace(
            render_views=lambda style: [
                {
                    "scene": "Upper",
                    "camera": "Camera",
                    "stem": stem,
                    "filename": name,
                    "category": "plans",
                }
                for stem, name in views.items()
            ],
            sun_rotations=lambda style: ("key", "fill"),
            QUALITY_PROFILES={
                "eevee": {"final": {"engine": "BLENDER_EEVEE"}},
                "cycles": {"final": {"engine": "CYCLES"}},
            },
        ),
        "rendering": types.SimpleNamespace(render_view_image=render_image),
    }
    monkeypatch.setitem(sys.modules, "bpy", fake)
    monkeypatch.setitem(
        sys.modules,
        "project_paths",
        types.SimpleNamespace(
            BLEND=blend,
            DESIGN=design,
            RENDER_CANCEL=cancel,
            completion_name=paths.completion_name,
            load_engine_modules=lambda *names: tuple(modules[name] for name in names),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "parcel_render_output",
        types.SimpleNamespace(
            prepare_outputs=lambda *_: outputs["eevee"], prepare_cycles=lambda: outputs["cycles"]
        ),
    )

    def run(engine="eevee"):
        outputs[engine].mkdir(parents=True, exist_ok=True)
        context = {
            "run_id": "canonical-final",
            "blend_sha256": hashlib.sha256(blend.read_bytes()).hexdigest(),
        }
        runpy.run_path(
            str(scripts_dir / "render_parcel_in_blender.py"),
            init_globals={"BLENDER_TASK_CONTEXT": context, "PARCEL_ENGINE": engine},
        )
        return outputs[engine], context

    return types.SimpleNamespace(run=run, cancel=cancel, rendered_stems=rendered_stems)


@pytest.mark.parametrize("engine", ["eevee", "cycles"])
def test_canonical_renderer_records_image_hashes(render_queue, engine):
    current, _ = render_queue.run(engine)

    receipt = json.loads((current / "final-complete.json").read_text())
    assert receipt["status"] == "complete"
    entry = receipt["images"][0]
    assert Path(entry["path"]) == current / "plans" / "Plan etaj.png"
    assert Path(entry["path"]).read_bytes() == b"rendered image"
    assert (receipt["engine"], entry["engine"]) == (engine, VIEW_ENGINES[engine])
    assert entry["sha256"] == hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest()
    assert json.loads((current / "final-log.json").read_text()) == receipt


def test_cancel_request_stops_the_queue_before_its_next_view(render_queue, monkeypatch):
    rendering = sys.modules["project_paths"].load_engine_modules("rendering")[0]
    render_image = rendering.render_view_image

    def render_then_cancel(*args, **kwargs):
        result = render_image(*args, **kwargs)
        render_queue.cancel.touch()
        return result

    monkeypatch.setattr(rendering, "render_view_image", render_then_cancel)
    current, context = render_queue.run()

    assert render_queue.rendered_stems == ["upper"]
    assert not render_queue.cancel.exists()
    assert not (current / "final-complete.json").exists()
    log = json.loads((current / "final-log.json").read_text())
    assert log["status"] == "cancelled"
    assert context["cancelled_outputs"] == [str(current / "plans" / "Plan etaj.png")]


def test_three_models_keep_only_latest_prior_set_and_relocate_receipts(render_output):
    output, root = render_output
    current = output.prepare_current("first")
    first = write_image(current, "exteriors/Vedere gradina.png", b"first")
    (current / "final-complete.json").write_text(json.dumps({"images": [{"path": str(first)}]}))

    current = output.prepare_outputs("renders", "second")
    receipt = json.loads((root / "previous/final-complete.json").read_text())
    assert Path(receipt["images"][0]["path"]).read_bytes() == b"first"
    second = write_image(current, "exteriors/Vedere gradina.png", b"second")
    (current / "final-complete.json").write_text(json.dumps({"images": [{"path": str(second)}]}))

    current = output.prepare_current("third")
    assert not (current / "exteriors/Vedere gradina.png").exists()
    assert (root / "previous/exteriors/Vedere gradina.png").read_bytes() == b"second"
    assert {p.read_bytes() for p in (root / "previous").rglob("*.png")} == {b"second"}
    receipt = json.loads((root / "previous/final-complete.json").read_text())
    assert Path(receipt["images"][0]["path"]).read_bytes() == b"second"
    assert {p.name for p in root.iterdir()} == {"current", "previous"}


def plain_floor():
    """A drawing-export floor with every exported key and one exterior wall ring."""
    return {
        "walls": [{"points": [(0, 0), (4, 0), (4, 4), (0, 4)], "role": "exterior"}],
        "glazing": [],
        "frames": [],
        "doors": [],
        "sliding_doors": [],
        "stairs": [],
        "rooms": [],
        "openings": [],
        "columns": [],
        "beams": [],
        "axes": [],
        "elevation_m": 0.0,
    }


def test_drawing_renderer_marks_sliding_travel_without_a_swing_arc(load_script_module):
    draw = load_script_module("draw_parcel_plans")
    base = plain_floor()
    sliding = deepcopy(base)
    sliding["sliding_doors"] = [
        {
            "id": "opening-sliding",
            "active_leaf_points": [(1, 0), (2, 0), (2, 0.1), (1, 0.1)],
            "opening_span": [(0, 0), (3, 0)],
            "travel_vector": [1, 0],
        }
    ]
    sliding_with_door = deepcopy(sliding)
    sliding_with_door["doors"] = [
        {
            "opening_id": "opening-sliding",
            "hinge": (0, 0),
            "end": (1, 1),
            "closed_angle": 0.0,
            "points": [(0, 0), (1, 0), (1, 0.1), (0, 0.1)],
        }
    ]

    summary = sheet_summary(draw, {"G": base})
    plain, _ = draw.draw_architectural_sheet(base, "G", summary)
    marked, _ = draw.draw_architectural_sheet(sliding, "G", summary)
    without_arc, _ = draw.draw_architectural_sheet(sliding_with_door, "G", summary)

    assert marked.tobytes() != plain.tobytes()
    assert without_arc.tobytes() == marked.tobytes()


def framed_floor(base, mark="S1"):
    """The plain fixture floor with one column, one upturned beam and two structural axes."""
    floor = deepcopy(base)
    floor["columns"] = [
        {
            "id": "col-1",
            "mark": mark,
            "level": "G",
            "section": "30×30",
            "points": [(0.2, 0.2), (0.5, 0.2), (0.5, 0.5), (0.2, 0.5)],
        }
    ]
    floor["beams"] = [
        {
            "id": "beam-1",
            "mark": "G2",
            "level": "G",
            "section": "30×90",
            "placement": "upturned",
            "points": [(0.2, 1.8), (3.8, 1.8), (3.8, 2.1), (0.2, 2.1)],
        }
    ]
    floor["axes"] = [
        {"id": "axis-1", "label": "1", "direction": "x", "position": 0.35},
        {"id": "axis-A", "label": "A", "direction": "y", "position": 0.35},
    ]
    return floor


def sheet_summary(draw, floors, north_local=(0.0, 1.0)):
    return {
        **draw.summarize(floors),
        "north_local": north_local,
        "project_name": "Casa Exemplu",
        "section_height_m": 1.6,
    }


def test_frame_members_mark_both_sheets(load_script_module):
    draw = load_script_module("draw_parcel_plans")
    base = plain_floor()
    framed = framed_floor(base)
    summary = sheet_summary(draw, {"G": framed})
    assert summary["column_storeys"] == {"S1": "P"}

    plain, _ = draw.draw_architectural_sheet(base, "G", sheet_summary(draw, {"G": base}))
    marked, _ = draw.draw_architectural_sheet(framed, "G", summary)
    assert marked.tobytes() != plain.tobytes()

    bare = draw.draw_structure_sheet(base, "G", sheet_summary(draw, {"G": base}))
    structure = draw.draw_structure_sheet(framed, "G", summary)
    without_axes = draw.draw_structure_sheet({**framed, "axes": []}, "G", summary)
    renamed = framed_floor(base, mark="S2")
    other_mark = draw.draw_structure_sheet(renamed, "G", sheet_summary(draw, {"G": renamed}))
    assert structure.size == bare.size == plain.size
    assert structure.tobytes() != bare.tobytes()
    assert structure.tobytes() != without_axes.tobytes()
    assert structure.tobytes() != other_mark.tobytes()


def test_drawing_run_writes_architectural_and_structure_sheets(
    load_script_module, tmp_path, monkeypatch
):
    draw = load_script_module("draw_parcel_plans")
    assert {
        "Plan arhitectural parter.png",
        "Plan arhitectural etaj.png",
        "Plan structura parter.png",
        "Plan structura etaj.png",
    } == set(draw.DRAWING_FILENAMES.values())
    blend = tmp_path / "house.blend"
    blend.write_bytes(b"saved model")
    base = plain_floor()
    geometry = tmp_path / "drawing-geometry.json"
    geometry.write_text(
        json.dumps(
            {
                "blend_sha256": persistence.sha256_file(blend),
                "project_name": "Casa Exemplu",
                "north_local": None,
                "section_height_m": 1.6,
                "floors": {"G": framed_floor(base), "U": {**base, "elevation_m": 3.3}},
            }
        )
    )
    run_dir = tmp_path / "current"
    run_dir.mkdir()
    monkeypatch.setattr(draw, "BLEND", blend)
    monkeypatch.setattr(draw, "DRAWING_GEOMETRY", geometry)
    monkeypatch.setattr(draw, "prepare_outputs", lambda kind, _: run_dir)
    monkeypatch.setattr(sys, "argv", ["draw_parcel_plans.py"])

    draw.main()
    receipt = json.loads((run_dir / "drawings-complete.json").read_text())
    assert {Path(image["path"]).name for image in receipt["images"]} == set(
        draw.DRAWING_FILENAMES.values()
    )
    structure = next(
        image
        for image in receipt["images"]
        if image["sheet"] == "structure" and image["level"] == "G"
    )
    assert (structure["columns"], structure["beams"], structure["axes"]) == (1, 1, 2)


def test_repeated_partial_renders_keep_one_previous_set_and_complementary_drawings(
    render_output,
):
    output, root = render_output
    current = output.prepare_outputs("renders", "same")
    write_image(current, "exteriors/Vedere gradina.png", b"preview")
    write_image(current, "plans/Plan arhitectural parter.png", b"drawing")

    current = output.prepare_outputs("renders", "same")
    assert (current / "plans/Plan arhitectural parter.png").read_bytes() == b"drawing"
    assert not (current / "exteriors/Vedere gradina.png").exists()

    write_image(current, "exteriors/Vedere sosire.png", b"final")
    write_image(current, "plans/Plan structura etaj.png", b"drawing")
    current = output.prepare_outputs("drawings", "same")
    assert (current / "exteriors/Vedere sosire.png").read_bytes() == b"final"
    assert not (current / "plans/Plan arhitectural parter.png").exists()
    assert not (current / "plans/Plan structura etaj.png").exists()
    assert {"plans", "exteriors"} <= {p.name for p in (root / "previous").iterdir()}
    assert {p.read_bytes() for p in (root / "previous").rglob("*.png")} == {
        b"drawing",
        b"final",
    }


def test_failed_receipt_relocation_preserves_both_sets(render_output, monkeypatch):
    output, root = render_output
    current = output.prepare_current("first")
    write_image(current, "exteriors/Vedere gradina.png", b"first")
    current = output.prepare_current("second")
    write_image(current, "exteriors/Vedere gradina.png", b"second")

    def fail_relocate(*args, **kwargs):
        raise ValueError("invalid receipt")

    monkeypatch.setattr(output, "_relocate_receipts", fail_relocate)
    with pytest.raises(ValueError, match="invalid receipt"):
        output.prepare_current("third")
    assert {p.read_bytes() for p in (root / "previous").rglob("*.png")} == {b"first"}
    assert {p.read_bytes() for p in current.rglob("*.png")} == {b"second"}


def test_empty_generation_does_not_create_archive_and_symlinks_are_rejected(
    render_output, tmp_path
):
    output, root = render_output
    output.prepare_current("first")
    output.prepare_current("second")
    assert not (root / "previous").exists()
    (root / "previous").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        output.prepare_outputs("renders", "second")


@pytest.mark.parametrize(
    ("module_name", "attribute"),
    [
        ("furnishings", "relink_furnishings"),
        ("presentation", "configure_scene"),
        ("render_inventory", "render_views"),
        ("rendering", "render_view_image"),
        ("blender_runtime", "apply_runtime_bundle"),
    ],
)
def test_load_engine_modules_serves_the_blender_scripts(load_script_module, module_name, attribute):
    """The maintained scripts load engine modules as a package, never via runpy.run_path."""

    project_paths = load_script_module("project_paths")

    def engine_names() -> list[str]:
        return [name for name in sys.modules if name == "engine" or name.startswith("engine.")]

    saved_modules = {name: sys.modules[name] for name in engine_names()}
    saved_path = list(sys.path)
    try:
        module = project_paths.load_engine_modules(module_name)
        assert hasattr(module, attribute)
        assert module.__name__ == f"engine.{module_name}"
    finally:
        # The helper replaces cached engine modules; restore them so later tests keep
        # comparing against the exception classes they already imported.
        for name in engine_names():
            del sys.modules[name]
        sys.modules.update(saved_modules)
        sys.path[:] = saved_path


def test_drawings_omit_the_compass_without_a_bearing_and_label_rooms_at_their_anchor(
    load_script_module,
):
    draw = load_script_module("draw_parcel_plans")
    base = plain_floor()
    with_north = draw.draw_architectural_sheet(base, "G", sheet_summary(draw, {"G": base}))[0]
    without = draw.draw_architectural_sheet(base, "G", sheet_summary(draw, {"G": base}, None))[0]
    assert with_north.tobytes() != without.tobytes()

    square = [[[0, 0], [2, 0], [2, 2], [0, 2]]]
    labelled = deepcopy(base)
    labelled["rooms"] = [
        {"id": "G-HALL", "label": "Hol", "area_m2": 4.0, "polygons": square, "anchor": [1, 1]}
    ]
    moved = deepcopy(labelled)
    moved["rooms"][0]["anchor"] = [1.5, 1.5]
    first = draw.draw_architectural_sheet(labelled, "G", sheet_summary(draw, {"G": labelled}))[0]
    second = draw.draw_architectural_sheet(moved, "G", sheet_summary(draw, {"G": moved}))[0]
    assert first.tobytes() != second.tobytes()


def test_stair_rooms_are_the_rooms_the_stair_parts_mostly_cover(load_script_module):
    draw = load_script_module("draw_parcel_plans")
    floor = plain_floor()
    floor["rooms"] = [
        {"id": "G-STAIR", "polygons": [[[0, 0], [1, 0], [1, 2], [0, 2]]]},
        {"id": "G-HALL", "polygons": [[[1, 0], [4, 0], [4, 2], [1, 2]]]},
    ]
    floor["stairs"] = [{"points": [[0, 0], [1, 0], [1, 1.8], [0, 1.8]], "overhead": False}]
    assert draw.stair_rooms(floor) == {"G-STAIR"}


def test_background_blender_treats_the_loaded_file_as_clean_until_a_mutation(
    runner, sandbox, monkeypatch
):
    sandbox.fake.app.background = True
    sandbox.fake.data.is_dirty = True  # Background Blender reports a fresh load as dirty.
    (sandbox.scripts / "probe.py").write_text("pass\n")
    tasks = {
        "build": {"script": "probe.py", "outputs": (), "requires_clean": False},
        "export": {"script": "probe.py", "outputs": (), "requires_clean": True},
    }
    monkeypatch.setattr(runner, "_TASKS", tasks)

    assert runner.run_task("export", sandbox.blend)["input"]["dirty"] is False
    runner.run_task("build", sandbox.blend)
    with pytest.raises(RuntimeError, match="requires clean"):
        runner.run_task("export", sandbox.blend)


def test_background_blender_save_clears_the_unsaved_mark(runner, sandbox, monkeypatch):
    sandbox.fake.app.background = True
    (sandbox.scripts / "save.py").write_text(
        "BLENDER_TASK_CONTEXT['output_blend_sha256'] = 'saved'\n"
    )
    (sandbox.scripts / "probe.py").write_text("pass\n")
    tasks = {
        "build": {"script": "probe.py", "outputs": (), "requires_clean": False},
        "save": {"script": "save.py", "outputs": (), "requires_clean": False},
        "export": {"script": "probe.py", "outputs": (), "requires_clean": True},
    }
    monkeypatch.setattr(runner, "_TASKS", tasks)

    runner.run_task("build", sandbox.blend)
    runner.run_task("save", sandbox.blend)
    assert runner.run_task("export", sandbox.blend)["status"] == "complete"


def test_background_blender_renders_synchronously_without_timers(
    runner, sandbox, tmp_path, monkeypatch
):
    sandbox.fake.app.background = True
    (sandbox.scripts / "render_parcel_in_blender.py").write_text(
        "BLENDER_TASK_CONTEXT['cancelled_outputs'] = []\n"
    )
    monkeypatch.setattr(runner, "RENDER_CANCEL", tmp_path / "cancel-render")

    result = runner.start_render(sandbox.blend, {"run_id": "render-headless"})
    assert result["status"] == "cancelled"
    assert not sandbox.fake.app.timers.callbacks
    assert runner._RENDER_STATE_KEY not in sandbox.fake.app.driver_namespace
