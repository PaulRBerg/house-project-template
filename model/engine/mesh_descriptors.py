"""Portable mesh descriptors and native Blender instantiation (stdlib only).

Coordinates are house-local; ``transform`` is a row-major local-to-world 4x4.
Material bindings deliberately do not participate in geometry fingerprints.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .persistence import transport_hash

IDENTITY = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
EXTERIOR_DETAILS = "Exterior | Details"
ELECTRIC_BLINDS = "Exterior | Electric blinds"
ROOF_CAP_SOLAR = "Roof | Cap & solar"


def level_collection(level_id: str, family: str) -> str:
    """Name a per-floor collection such as ``G | Walls low``."""
    return f"{level_id} | {family}"


def kit_part_descriptor(
    part: Mapping[str, Any],
    *,
    identity: str,
    component_id: str,
    kind: str,
    name: str,
    collection: str,
    transform: list,
    binding: Mapping[str, Any],
    properties: Mapping[str, Any],
    dependency_fingerprint: str,
    placement_fingerprint: str,
) -> dict[str, Any]:
    """Describe one generated kit role mesh with rounded coordinates and analytic normals."""
    mesh = part["mesh"]
    vertices = [[round(float(value), 5) for value in vertex] for vertex in mesh["vertices"]]
    faces = [list(face) for face in mesh["faces"]]
    normals = (
        [[round(float(value), 4) for value in normal] for normal in mesh["normals"]]
        if "normals" in mesh
        else None
    )
    descriptor = {
        "id": identity,
        "component_id": component_id,
        "kind": kind,
        "name": name,
        "collection": collection,
        "vertices": vertices,
        "faces": faces,
        "smooth": bool(part.get("smooth")) or normals is not None,
        "cast_shadow": bool(part.get("shadow", True)),
        "transform": transform,
        "material_binding": dict(binding),
        "properties": dict(properties),
        "dependency_fingerprint": dependency_fingerprint,
        "geometry_fingerprint": transport_hash(
            {
                "vertices": vertices,
                "faces": faces,
                "normals": normals,
                "placement": placement_fingerprint,
            }
        ),
    }
    if normals is not None:
        descriptor["normals"] = normals
    return descriptor


def mesh_descriptor(
    *,
    component: Mapping[str, Any],
    child_id: str,
    mesh: Mapping[str, Any],
    collection: str,
    transform: list | None = None,
    material_id: str | None = None,
    slot: str = "body",
    properties: Mapping | None = None,
    name: str | None = None,
    kind: str | None = None,
    generator_version: str = "1.0.0",
) -> dict[str, Any]:
    """Make a serializable descriptor with stable ownership and dependency evidence."""
    component_id = component["id"]
    identity = f"{component_id}/{child_id}"
    semantics = {
        "Component ID": component_id,
        "Component kind": kind or component["kind"],
        "Procedural child ID": identity,
        **dict(properties or {}),
    }
    geometry = {
        "vertices": [[float(v) for v in vertex] for vertex in mesh["vertices"]],
        "faces": [list(face) for face in mesh["faces"]],
    }
    transform = transform or IDENTITY
    fingerprint = transport_hash(
        {
            "mesh": geometry,
            "transform": transform,
            "dependency": component["fingerprint"],
            "child_id": child_id,
            "generator": generator_version,
        }
    )
    return {
        "id": identity,
        "component_id": component_id,
        "kind": kind or component["kind"],
        "name": name or identity,
        "collection": collection,
        **geometry,
        "transform": transform,
        "material_binding": {
            "target_id": component_id,
            "slot": slot,
            "material_id": material_id,
        },
        "properties": semantics,
        "dependency_fingerprint": component["fingerprint"],
        "geometry_fingerprint": fingerprint,
    }


def instantiate_meshes(
    bpy: Any,
    descriptors: list[dict],
    *,
    materials: Mapping | None = None,
) -> list[Any]:
    """Create descriptors as editable meshes; caller owns cleanup/incremental selection.

    Materials may be keyed by material ID or ``(component_id, slot)``. No asset
    library or host compiler is imported in Blender. Duplicate ownership fails
    before mutation instead of accumulating a second procedural build.
    """
    from mathutils import Matrix

    from .blender_datablocks import assign_properties, create_mesh_object, ensure_collection

    ids = [descriptor["id"] for descriptor in descriptors]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate descriptor IDs")
    occupied = {obj.get("procedural_id") for obj in bpy.data.objects}
    duplicates = occupied.intersection(ids)
    if duplicates:
        raise ValueError(f"procedural objects already exist: {sorted(duplicates)[:5]}")
    collections: dict[str, Any] = {}
    materials = {} if materials is None else materials
    objects = []
    for descriptor in descriptors:
        key = descriptor["collection"]
        collection = collections.get(key) or ensure_collection(bpy, key)
        collections[key] = collection
        binding = descriptor.get("material_binding", {})
        material = materials.get((binding.get("target_id"), binding.get("slot")))
        if material is None:
            material = materials.get(binding.get("material_id"))
        obj = create_mesh_object(
            bpy,
            collection=collection,
            name=descriptor["name"],
            vertices=descriptor["vertices"],
            faces=descriptor["faces"],
            material=material,
            component_id=descriptor["id"],
            smooth=bool(descriptor.get("smooth")),
            normals=descriptor.get("normals"),
        )
        obj.matrix_world = Matrix(descriptor["transform"])
        if descriptor.get("cast_shadow") is False:
            obj.visible_shadow = False
        assign_properties(obj, descriptor.get("properties", {}))
        obj["geometry_fingerprint"] = descriptor["geometry_fingerprint"]
        obj["dependency_fingerprint"] = descriptor["dependency_fingerprint"]
        obj["material_slot"] = binding.get("slot", "body")
        obj["material_id"] = binding.get("material_id") or ""
        objects.append(obj)
    return objects
