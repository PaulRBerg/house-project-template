"""Small deterministic Blender datablock helpers: collections, properties, meshes, lights, appends.

No scene, collection, material, or context is implicit.  Importing the module is
safe outside Blender; callers explicitly pass the Blender module and destination
collection.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def ensure_collection(bpy: Any, name: str, *, link_existing: bool = False) -> Any:
    """Return the named collection, creating it under the scene root when missing.

    ``link_existing`` also links an existing collection to the scene root when absent,
    for assemblies whose floor exclusions rely on top-level membership.
    """
    collection = bpy.data.collections.get(name)
    root = bpy.context.scene.collection
    if collection is None:
        collection = bpy.data.collections.new(name)
        root.children.link(collection)
    elif link_existing and collection not in root.children[:]:
        root.children.link(collection)
    return collection


def assign_properties(obj: Any, properties: Mapping[str, Any]) -> None:
    """Store custom properties, serializing non-scalar values as canonical JSON."""
    for key, value in properties.items():
        obj[key] = (
            value
            if isinstance(value, (str, int, float, bool))
            else json.dumps(value, ensure_ascii=False, sort_keys=True)
        )


def append_objects(
    bpy: Any, library: str | Path, names: Sequence[str], error: type[Exception]
) -> dict[str, Any]:
    """Append *names* from a library blend, keyed by source name despite copy suffixes."""
    names = list(names)
    with bpy.data.libraries.load(str(Path(library).resolve()), link=False) as (available, loaded):
        missing = sorted(set(names) - set(available.objects))
        if missing:
            raise error(f"{Path(library).name} is missing objects: {missing[:5]}")
        # Blender replaces the assigned list's names with loaded IDs in place; keep ours intact.
        loaded.objects = list(names)
    return {name: obj for name, obj in zip(names, loaded.objects, strict=True) if obj is not None}


def configure_light(data: Any, spec: Mapping[str, Any]) -> None:
    """Apply kit or presentation emitter settings, including colour temperature."""
    data.energy = float(spec["energy"])
    if "temperature" in spec:
        data.use_temperature = True
        data.temperature = float(spec["temperature"])
        data.color = (1.0, 1.0, 1.0)
    else:
        data.use_temperature = False
        data.color = tuple(float(value) for value in spec.get("color", (1.0, 1.0, 1.0)))
    if data.type == "AREA":
        data.shape = spec.get("shape", "SQUARE")
        data.size = float(spec.get("size", 0.1))
        if data.shape in {"RECTANGLE", "ELLIPSE"}:
            data.size_y = float(spec.get("size_y", data.size))
        if "spread" in spec:
            data.spread = float(spec["spread"])
    elif "radius" in spec:
        data.shadow_soft_size = float(spec["radius"])
    if data.type == "SPOT":
        data.spot_size = float(spec.get("spot_size", 0.9))
        data.spot_blend = float(spec.get("spot_blend", 0.5))
        data.show_cone = False


def create_mesh_object(
    bpy: Any,
    *,
    collection: Any,
    name: str,
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    component_id: str,
    material: Any | None = None,
    smooth: bool = False,
    normals: Sequence[Sequence[float]] | None = None,
) -> Any:
    """Create and link a native mesh object with optional material and soft shading.

    ``normals`` are analytic per-vertex normals for rounded kit parts; smooth
    parts without them use Blender's averaged vertex normals.
    """
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(vertex) for vertex in vertices], [], [tuple(face) for face in faces])
    mesh.update()
    if smooth:
        mesh.shade_smooth()
    if normals is not None:
        mesh.normals_split_custom_set_from_vertices([tuple(normal) for normal in normals])
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if material is not None:
        mesh.materials.append(material)
    obj["procedural_id"] = component_id
    return obj
