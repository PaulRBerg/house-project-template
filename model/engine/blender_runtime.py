"""Blender-native application of precompiled design descriptors.

This adapter is intentionally import-safe in Blender: it imports no compiler,
schema, or geometry module and performs no host-side design interpretation.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import paths
from .furnishings import instantiate_furnishings
from .materials import apply_materials
from .mesh_descriptors import instantiate_meshes
from .persistence import atomic_write_json, evidence_fingerprint, read_json, transport_hash
from .persistence import sha256_file as _sha256
from .persistence import utc_now as _now
from .presentation import apply_presentation
from .site_components import instantiate_site_components

# `engine.runtime_bundle` writes bundles in this format; Blender rejects any other.
FORMAT_VERSION = 1


def runtime_fingerprint(bundle: Mapping[str, Any]) -> str:
    """Hash a runtime bundle without its own fingerprint and its compile-time change set."""
    return transport_hash(
        {
            key: value
            for key, value in bundle.items()
            if key not in {"runtime_fingerprint", "change_set"}
        }
    )


def read_runtime_bundle(path: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    bundle = read_json(source)
    if bundle.get("format_version") != FORMAT_VERSION:
        raise ValueError(f"Unsupported runtime bundle: {bundle.get('format_version')!r}")
    if bundle.get("runtime_fingerprint") != runtime_fingerprint(bundle):
        raise ValueError("Runtime bundle fingerprint does not match its content")
    return bundle


def _procedural_id(obj: Any) -> str | None:
    value = obj.get("procedural_id")
    return str(value) if value else None


def _remove_object(bpy: Any, obj: Any) -> None:
    data = getattr(obj, "data", None)
    object_type = getattr(obj, "type", "")
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and getattr(data, "users", 0) == 0:
        owner = {
            "MESH": bpy.data.meshes,
            "CURVE": bpy.data.curves,
            "FONT": bpy.data.curves,
            "CAMERA": bpy.data.cameras,
            "LIGHT": bpy.data.lights,
        }.get(object_type)
        if owner is not None:
            owner.remove(data)


def _reset_scene(bpy: Any) -> None:
    for obj in list(bpy.data.objects):
        _remove_object(bpy, obj)
    for scene in list(bpy.data.scenes)[1:]:
        bpy.data.scenes.remove(scene)
    scene = bpy.data.scenes[0]
    scene.name = "Procedural build"
    # The build recreates every collection its descriptors name, so a renamed or
    # retired collection must not survive, empty but still linked, from the old design.
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def _remove_changed(bpy: Any, identifiers: set[str]) -> None:
    for obj in list(bpy.data.objects):
        identifier = _procedural_id(obj)
        if not identifier:
            continue
        parts = identifier.split("/")
        if any("/".join(parts[:depth]) in identifiers for depth in range(1, len(parts) + 1)):
            _remove_object(bpy, obj)


def _selected(items: Sequence[Mapping[str, Any]], identifiers: set[str] | None):
    if identifiers is None:
        return list(items)
    return [item for item in items if item["id"] in identifiers]


def _assign_material_bindings(
    bpy: Any, materials: Mapping[str, Any], bundle: Mapping[str, Any]
) -> None:
    bindings = {
        descriptor["id"]: descriptor["material_binding"]
        for domain in ("architecture", "furnishings", "site_components")
        for descriptor in bundle.get(domain, {}).get("meshes", [])
        if "material_binding" in descriptor
    }
    for obj in bpy.data.objects:
        binding = bindings.get(obj.get("procedural_id"))
        if binding is not None:
            obj["material_id"] = binding.get("material_id") or ""
            obj["material_slot"] = binding.get("slot", "body")
        material_id = obj.get("material_id")
        if binding is None and (not material_id or material_id not in materials):
            continue
        slots = getattr(getattr(obj, "data", None), "materials", None)
        if slots is None:
            continue
        slots.clear()
        if material_id in materials:
            slots.append(materials[material_id])


def apply_runtime_bundle(
    bpy: Any,
    bundle: Mapping[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    """Apply a fresh, incremental or material-only native build."""

    root = paths.MODEL_DIR
    change = bundle["change_set"]
    if mode not in {"fresh", "incremental", "material-only"}:
        raise ValueError(f"Unsupported build mode: {mode!r}")
    started = time.monotonic()
    if mode == "fresh":
        _reset_scene(bpy)
        selected = None
        removed = 0
    else:
        changed = set(change["added"] + change["changed"] + change["removed"])
        before = len(bpy.data.objects)
        _remove_changed(bpy, changed)
        removed = before - len(bpy.data.objects)
        selected = set(change["added"] + change["changed"])
    material_library = root / bundle["libraries"]["assets"]
    materials = apply_materials(
        bpy, bundle["materials"]["materials"], library_path=material_library
    )
    created: list[Any] = []
    if mode != "material-only":
        architecture = _selected(bundle["architecture"]["meshes"], selected)
        created.extend(instantiate_meshes(bpy, architecture, materials=materials))
        furnishings = {
            **bundle["furnishings"],
            "placements": _selected(bundle["furnishings"]["placements"], selected),
            "meshes": _selected(bundle["furnishings"]["meshes"], selected),
        }
        furnishing_result = instantiate_furnishings(
            bpy, furnishings, material_library, materials=materials
        )
        created.extend(furnishing_result["asset_roots"])
        created.extend(furnishing_result["meshes"])
        created.extend(furnishing_result["lights"])
        site_components = {
            **bundle["site_components"],
            "meshes": _selected(bundle["site_components"]["meshes"], selected),
            "placements": _selected(bundle["site_components"]["placements"], selected),
            "lights": _selected(bundle["site_components"]["lights"], selected),
        }
        site_component_result = instantiate_site_components(
            bpy, site_components, library_path=material_library, materials=materials
        )
        for values in site_component_result.values():
            created.extend(values)
    # A fresh append creates independent asset material copies. Reapplying the
    # descriptors updates those tagged copies; material-only runs take this same
    # path without rebuilding or moving any object.
    materials = apply_materials(
        bpy, bundle["materials"]["materials"], library_path=material_library
    )
    _assign_material_bindings(bpy, materials, bundle)
    apply_presentation(bpy, bundle["presentation"], worlds=materials)
    return {
        "mode": mode,
        "created": len(created),
        "removed": removed,
        "runtime_fingerprint": bundle["runtime_fingerprint"],
        "seconds": round(time.monotonic() - started, 6),
    }


def export_evaluated_geometry(
    bpy: Any,
    *,
    output_path: str | Path,
) -> dict[str, Any]:
    """Export evaluated world vertices; descriptor vertices are never evidence."""

    saved = paths.BLEND
    if Path(bpy.data.filepath).resolve() != saved or (bpy.data.is_dirty and not bpy.app.background):
        raise RuntimeError("Evaluated export requires the clean saved blend")
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = []
    for source in sorted(bpy.data.objects, key=lambda item: item.name):
        component_id = source.get("Component ID") or source.get("site_component_id")
        procedural_id = _procedural_id(source)
        if source.type not in {"MESH", "CURVE", "FONT"} or not component_id or not procedural_id:
            continue
        evaluated = source.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            vertices = [
                [float(value) for value in evaluated.matrix_world @ vertex.co]
                for vertex in mesh.vertices
            ]
            faces = [list(polygon.vertices) for polygon in mesh.polygons]
        finally:
            evaluated.to_mesh_clear()
        if not vertices or not faces:
            continue
        properties = {
            str(key): source[key]
            for key in source.keys()  # noqa: SIM118 -- Blender ID supports keys(), not iteration
            if isinstance(source[key], (str, int, float, bool))
        }
        objects.append(
            {
                "id": procedural_id,
                "component_id": str(component_id),
                "kind": str(source.get("Component kind", source.get("kind", "mesh"))),
                "vertices_world": vertices,
                "faces": faces,
                "properties": properties,
                "evaluated_geometry_fingerprint": evidence_fingerprint(vertices, faces),
            }
        )
    evidence = {
        "evidence_kind": "exported_mesh",
        "coordinate_space": "world",
        "saved_blend_sha256": _sha256(saved),
        "provenance": {
            "exporter": "engine.blender_runtime.export_evaluated_geometry",
            "exported_at": _now(),
            "blender_version": bpy.app.version_string,
        },
        "objects": objects,
    }
    atomic_write_json(Path(output_path).resolve(), evidence)
    return evidence


__all__ = [
    "apply_runtime_bundle",
    "export_evaluated_geometry",
    "read_runtime_bundle",
]
