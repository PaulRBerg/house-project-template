"""Guarded Blender entry points for building and verifying the demo model."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
MODEL_DIR = SCRIPTS_DIR.parent
CANONICAL_BLEND = MODEL_DIR / "house.blend"
BUILDER = SCRIPTS_DIR / "build_demo_house.py"
EXPECTED_OBJECTS = {
    "Area.Fill",
    "Camera.Demo",
    "Door.Front",
    "Ground",
    "Roof.Gabled",
    "Slab.8x6m",
    "Sun.Demo",
    "Wall.Back",
    "Wall.East",
    "Wall.Front",
    "Wall.West",
    "Window.Back.Left",
    "Window.Back.Right",
    "Window.East",
    "Window.Front",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_target(candidate: str | Path) -> Path:
    resolved = Path(candidate).expanduser().resolve()
    if resolved != CANONICAL_BLEND.resolve():
        raise RuntimeError(f"Refusing non-canonical blend target: {resolved}")
    return resolved


def assert_expected_file(path: Path, expected_sha256: str) -> None:
    if not expected_sha256 or len(expected_sha256) != 64:
        raise RuntimeError("A complete expected SHA-256 is required")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"Saved-file hash changed: expected {expected_sha256}, found {actual}")


def _bpy() -> Any:
    import bpy

    return bpy


def _load_builder() -> Any:
    spec = importlib.util.spec_from_file_location("house_demo_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the maintained Blender builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _current_path(bpy: Any) -> Path | None:
    return Path(bpy.data.filepath).resolve() if bpy.data.filepath else None


def _assert_clean(bpy: Any) -> None:
    if bpy.data.is_dirty:
        raise RuntimeError("Blender has unsaved changes; refusing the operation")


def _build_and_save(bpy: Any, target: Path) -> dict[str, Any]:
    bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True)
    if bpy.data.filepath or bpy.data.is_dirty:
        raise RuntimeError("Factory reset did not produce a clean unsaved file")
    for library in list(bpy.data.libraries):
        bpy.data.libraries.remove(library)
    source_hash = sha256_file(BUILDER)
    report = _load_builder().build_scene(bpy, source_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(target), check_existing=False)
    if _current_path(bpy) != target or bpy.data.is_dirty:
        raise RuntimeError("Blender did not save a clean canonical file")
    saved_hash = sha256_file(target)
    verified = validate_current_scene(bpy, target, saved_hash)
    return {"saved_sha256": saved_hash, "build": report, "verification": verified}


def bootstrap_new_demo(
    source_blend: str | Path,
    source_sha256: str,
    expected_blend: str | Path,
) -> dict[str, Any]:
    """Create a new demo after proving the currently open source is saved and unchanged."""
    bpy = _bpy()
    target = canonical_target(expected_blend)
    source = Path(source_blend).expanduser().resolve()
    if target.exists():
        raise RuntimeError("Canonical demo already exists; use rebuild_demo with its known hash")
    if _current_path(bpy) != source:
        raise RuntimeError("The expected source blend is not the live Blender file")
    _assert_clean(bpy)
    assert_expected_file(source, source_sha256)
    return _build_and_save(bpy, target)


def rebuild_demo(expected_blend: str | Path, expected_blend_sha256: str) -> dict[str, Any]:
    """Rebuild only when the canonical demo is open, clean, and matches a known hash."""
    bpy = _bpy()
    target = canonical_target(expected_blend)
    if _current_path(bpy) != target:
        raise RuntimeError("Open the canonical demo before rebuilding it")
    _assert_clean(bpy)
    assert_expected_file(target, expected_blend_sha256)
    return _build_and_save(bpy, target)


def validate_current_scene(
    bpy: Any, expected_blend: str | Path, expected_blend_sha256: str
) -> dict[str, Any]:
    target = canonical_target(expected_blend)
    if _current_path(bpy) != target:
        raise RuntimeError("Unexpected live blend path")
    _assert_clean(bpy)
    assert_expected_file(target, expected_blend_sha256)

    scene = bpy.context.scene
    actual_objects = set(bpy.data.objects.keys())
    if actual_objects != EXPECTED_OBJECTS:
        raise RuntimeError(
            f"Unexpected object inventory: missing={sorted(EXPECTED_OBJECTS - actual_objects)}, "
            f"extra={sorted(actual_objects - EXPECTED_OBJECTS)}"
        )
    if scene.unit_settings.system != "METRIC" or scene.unit_settings.length_unit != "METERS":
        raise RuntimeError("The model must use metric metres")
    if scene.get("status") != "illustrative_unaccepted_demo":
        raise RuntimeError("The model is missing its illustrative/unaccepted status")
    if abs(float(scene.get("external_footprint_area_m2", 0.0)) - 48.0) > 1e-9:
        raise RuntimeError("The saved 8 m x 6 m footprint area is not 48 m²")
    slab = bpy.data.objects["Slab.8x6m"]
    if any(
        abs(actual - expected) > 1e-6
        for actual, expected in zip(slab.dimensions, (8.0, 6.0, 0.2), strict=True)
    ):
        raise RuntimeError(f"Unexpected slab dimensions: {tuple(slab.dimensions)}")
    if len(bpy.data.libraries) != 0:
        raise RuntimeError("The demo must not link external Blender libraries")
    external_images = [
        image.filepath for image in bpy.data.images if image.source == "FILE" and image.filepath
    ]
    if external_images:
        raise RuntimeError(f"The demo must be self-contained; external images: {external_images}")
    if scene.get("builder_source_sha256") != sha256_file(BUILDER):
        raise RuntimeError("The saved builder source hash is stale")
    return {
        "filepath": str(target),
        "sha256": expected_blend_sha256,
        "scene": scene.name,
        "status": scene["status"],
        "external_footprint_area_m2": scene["external_footprint_area_m2"],
        "object_count": len(actual_objects),
        "linked_libraries": len(bpy.data.libraries),
        "external_images": external_images,
        "is_dirty": bpy.data.is_dirty,
    }


def verify_current(expected_blend: str | Path, expected_blend_sha256: str) -> dict[str, Any]:
    return validate_current_scene(_bpy(), expected_blend, expected_blend_sha256)


def reopen_and_verify(expected_blend: str | Path, expected_blend_sha256: str) -> dict[str, Any]:
    """Prove the live snapshot, reopen from disk, and validate the reopened file."""
    bpy = _bpy()
    target = canonical_target(expected_blend)
    validate_current_scene(bpy, target, expected_blend_sha256)
    bpy.ops.wm.open_mainfile(filepath=str(target))
    return validate_current_scene(bpy, target, expected_blend_sha256)
