"""Room-relative furnishing compilation and editable Blender asset appending.

The JSON position is measured in metres from the room anchor.  Rotation is an
XYZ Euler delta in radians in house-local axes.  Catalog dimensions are fixed:
library assets are moved and rotated as an editable hierarchy, never scaled.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .assets import asset_index
from .blender_datablocks import append_objects, configure_light
from .fixture_kit import FIXTURES
from .furniture_kit import TEMPLATES
from .kit_parts import BOOK_ROLE_COUNT
from .mesh_descriptors import kit_part_descriptor
from .persistence import strip_copy_suffix, transport_hash
from .transforms import (
    affine_inverse_rigid,
    apply_point,
    determinant3,
    finite_vector,
    multiply,
    rotation_xyz,
    translation,
)

KIT = {**TEMPLATES, **FIXTURES}

# Style material for each kit role; a furnishing overrides roles with
# ``generated.materials``. ``body`` binds the first of ``material_ids``.
ROLE_MATERIALS = {
    "wood": "mat_oak",
    "front": "mat_oak",
    "carcass": "mat_oak",
    "niche": "mat_oak",
    "frame": "mat_oak",
    "plinth": "mat_shadow_gap",
    "base": "mat_oak",
    "metal": "mat_metal_dark",
    "track": "mat_trim_white",
    "trim": "mat_trim_white",
    "upholstery": "mat_fabric_neutral",
    "cushion": "mat_fabric_neutral",
    "headboard": "mat_fabric_neutral",
    "accent": "mat_green",
    "throw": "mat_throw_wool",
    "stone": "mat_stone_grey",
    "basin": "mat_basin_steel",
    "appliance": "mat_black_glass",
    "glass": "mat_glass",
    "mirror": "mat_mirror",
    "led": "mat_led_2700",
    "glow": "mat_glow_2700",
    "shade": "mat_shade_linen",
    "ceramic": "mat_ceramic_white",
    "pot": "mat_pot_terracotta",
    "soil": "mat_soil",
    "leaf": "mat-baseline-20-foliage-1-002",
    "leaf2": "mat-baseline-20-foliage-3-002",
    "stem": "mat_tree_bark",
    "dried": "mat_dried_stems",
    "paper": "mat_art_paper",
    "canvas": "mat_art_oat",
    "art_a": "mat_accent",
    "art_b": "mat_sage",
    **{f"book{index}": f"mat-baseline-book-cloth-{index}-002" for index in range(BOOK_ROLE_COUNT)},
    "rug": "mat_rug_wool",
    "rug_border": "mat_rug_jute",
    "sheer": "mat_sheer",
    "dimout": "mat_curtain_linen",
    "blackout": "mat_curtain_taupe",
    "pocket": "mat_plaster_white",
    "linen": "mat_bed_linen",
    "bedding": "mat_bed_linen",
    "pillow": "mat_bed_linen",
    "towel": "mat_towel_oat",
    "panel": "mat_plaster_white",
}


class FurnishingError(ValueError):
    """Raised when a furnishing cannot be compiled without changing its size."""


def _triplet(value: Any, field: str) -> tuple[float, float, float]:
    return tuple(finite_vector(value, 3, field, FurnishingError))


def validate_furnishings(
    design: Mapping[str, Any], catalog: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Validate fixed sizes, room references and placement fields."""
    rooms = {room["id"]: room for room in design.get("rooms", [])}
    assets = asset_index(catalog)
    normalized: list[dict[str, Any]] = []
    for source in design.get("furnishings", []):
        item = dict(source)
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise FurnishingError("furnishing id is required")
        room_id = item.get("room_id")
        if room_id not in rooms:
            raise FurnishingError(f"{identifier}: unknown room_id {room_id!r}")
        if item.get("anchor") != "room":
            raise FurnishingError(f"{identifier}: anchor must be 'room'")
        position = _triplet(item.get("position"), f"{identifier}.position")
        rotation = _triplet(item.get("rotation"), f"{identifier}.rotation")
        dimensions = _triplet(item.get("dimensions"), f"{identifier}.dimensions")
        clearance = item.get("clearance_m")
        if not isinstance(clearance, Mapping) or set(clearance) != {
            "front",
            "back",
            "left",
            "right",
        }:
            raise FurnishingError(
                f"{identifier}.clearance_m must define front, back, left and right"
            )
        if any(
            not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
            for value in clearance.values()
        ):
            raise FurnishingError(f"{identifier}.clearance_m values must be finite and nonnegative")
        asset_id = item.get("asset_id")
        generated = item.get("generated")
        if bool(asset_id) == bool(generated):
            raise FurnishingError(f"{identifier}: choose exactly one of asset_id or generated")
        if asset_id:
            asset = assets.get(asset_id)
            if asset is None:
                raise FurnishingError(f"{identifier}: unknown asset_id {asset_id!r}")
            source_dimensions = _triplet(asset.get("dimensions"), f"{asset_id}.dimensions")
            expected = (
                source_dimensions[1],
                source_dimensions[0],
                source_dimensions[2],
            )
            zero_sized = all(value == 0 for value in source_dimensions)
            if zero_sized:
                expected = (0.0, 0.0, 0.0)
            elif min(dimensions) <= 0:
                raise FurnishingError(f"{identifier}.dimensions values must be positive")
            if any(
                not math.isclose(a, b, abs_tol=1e-6)
                for a, b in zip(dimensions, expected, strict=True)
            ):
                raise FurnishingError(
                    f"{identifier}: fixed asset dimensions {dimensions!r} differ from catalog-derived local extents {expected!r}"
                )
            if item.get("adjustable"):
                raise FurnishingError(f"{identifier}: library assets cannot be adjustable")
        elif min(dimensions) <= 0:
            raise FurnishingError(f"{identifier}.dimensions values must be positive")
        elif not isinstance(generated, Mapping) or generated.get("kind") not in KIT:
            raise FurnishingError(f"{identifier}: unsupported generated furnishing")
        elif not isinstance(generated.get("params", {}), Mapping) or not isinstance(
            generated.get("materials", {}), Mapping
        ):
            raise FurnishingError(f"{identifier}: generated params and materials must be objects")
        item["position"] = list(position)
        item["rotation"] = list(rotation)
        item["dimensions"] = list(dimensions)
        normalized.append(item)
    return sorted(normalized, key=lambda entry: entry["id"])


def compile_furnishings(
    design: Mapping[str, Any],
    catalog: Mapping[str, Any],
    compiled: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile validated furnishings into append and primitive descriptors."""
    items = validate_furnishings(design, catalog)
    rooms = {room["id"]: room for room in design["rooms"]}
    levels = {level["id"]: level for level in design["levels"]}
    assets = asset_index(catalog)
    components = {
        component["id"]: component for component in (compiled or {}).get("components", [])
    }
    house_transform = design["transform"]
    house_inverse = affine_inverse_rigid(house_transform)
    placements: list[dict[str, Any]] = []
    meshes: list[dict[str, Any]] = []
    for item in items:
        room = rooms[item["room_id"]]
        level = levels[room["level_id"]]
        local = [
            room["anchor"][0] + item["position"][0],
            room["anchor"][1] + item["position"][1],
            level["elevation_m"] + item["position"][2],
        ]
        local_delta = rotation_xyz(*item["rotation"])
        asset = assets.get(item.get("asset_id"))
        if asset:
            world_delta = multiply(multiply(house_transform, local_delta), house_inverse)
            world_delta[0][3] = world_delta[1][3] = world_delta[2][3] = 0.0
            item_transform = multiply(
                translation(*apply_point(house_transform, local)), world_delta
            )
        else:
            item_transform = multiply(house_transform, multiply(translation(*local), local_delta))
        component = components.get(item["id"])
        descriptor = {
            "id": item["id"],
            "component_id": item["id"],
            "kind": "asset" if asset else "generated",
            "name": item.get("name", asset.get("name") if asset else item["id"]),
            "collection": item.get(
                "collection", asset.get("collection") if asset else "Furnishings"
            ),
            "room_id": item["room_id"],
            "asset_id": item.get("asset_id"),
            "source_origin": list(asset["origin"]) if asset else [0, 0, 0],
            "members": list(asset["members"]) if asset else [],
            "materials": list(asset["materials"]) if asset else item.get("material_ids", []),
            "dimensions": item["dimensions"],
            "source_dimensions": list(asset["dimensions"]) if asset else item["dimensions"],
            "clearance_m": item["clearance_m"],
            "clearance_status": item.get("clearance_status", "authored"),
            "purpose": item.get("purpose", "furnishing"),
            "containment_policy": item.get("containment_policy", "floor"),
            "transform": item_transform,
            "generated": item.get("generated"),
            "dependency_fingerprint": component.get("fingerprint")
            if component
            else transport_hash(item),
        }
        descriptor["geometry_fingerprint"] = transport_hash(
            {
                key: value
                for key, value in descriptor.items()
                if key not in {"materials", "dependency_fingerprint"}
            }
        )
        if not asset:
            parts, lights = generate_kit(item)
            descriptor["lights"] = [kit_light_matrix(light, item_transform) for light in lights]
            descriptor["geometry_fingerprint"] = transport_hash(
                {"placement": descriptor["geometry_fingerprint"], "lights": descriptor["lights"]}
            )
            for part in parts:
                meshes.append(_part_descriptor(item, room, part, descriptor, item_transform))
        placements.append(descriptor)
    return {
        "generator": {"id": "engine.furnishings", "version": "1.0.0"},
        "placements": placements,
        "meshes": meshes,
        "coverage": {
            "furnishing_count": len(placements),
            "asset_count": sum(item["kind"] == "asset" for item in placements),
            "generated_count": sum(item["kind"] == "generated" for item in placements),
        },
        "fingerprint": transport_hash(placements),
    }


def _seed(identifier: str, generated: Mapping[str, Any]) -> random.Random:
    digest = int(hashlib.sha256(identifier.encode()).hexdigest()[:12], 16)
    return random.Random(digest ^ int(generated.get("seed", 0)))


def generate_kit(item: Mapping[str, Any]) -> tuple[list[dict], list[dict]]:
    """Run the kit template and bind every part role to a style material ID."""
    generated = item["generated"]
    parts, lights = KIT[generated["kind"]](
        item["dimensions"], generated.get("params", {}), _seed(item["id"], generated)
    )
    roles = {**ROLE_MATERIALS, **generated.get("materials", {})}
    body = next(iter(item.get("material_ids", [])), None)
    for part in parts:
        role = part["role"]
        if role == "body":
            part["material_id"] = roles.get("body", body)
        elif role in roles:
            part["material_id"] = roles[role]
        else:
            raise FurnishingError(f"{item['id']}: no material for kit role {role!r}")
        part["child"] = part["name"] if part["name"] == role else f"{part['name']}-{role}"
    children = [part["child"] for part in parts]
    if len(children) != len(set(children)):
        raise FurnishingError(f"{item['id']}: duplicate kit part names {children}")
    return parts, lights


def kit_light_matrix(light: Mapping[str, Any], item_transform: Sequence[Sequence[float]]) -> dict:
    """World matrix for a kit emitter, re-orthonormalized to a proper rotation.

    The house transform mirrors local plan axes; lights keep a positive determinant
    so area sizes and spot cones never inherit a negative scale.
    """
    local = multiply(
        translation(*light["position"]), rotation_xyz(*light.get("rotation", (0.0, 0.0, 0.0)))
    )
    world = multiply(item_transform, local)
    axes = [[world[row][column] for row in range(3)] for column in range(3)]
    if determinant3(world) < 0:
        axes[0] = [-value for value in axes[0]]
    matrix = [[axes[column][row] for column in range(3)] + [world[row][3]] for row in range(3)]
    matrix.append([0.0, 0.0, 0.0, 1.0])
    spec = {key: value for key, value in light.items() if key not in {"position", "rotation"}}
    return {**spec, "matrix": [[round(value, 6) for value in row] for row in matrix]}


def _part_descriptor(
    item: Mapping[str, Any],
    room: Mapping[str, Any],
    part: Mapping[str, Any],
    placement: Mapping[str, Any],
    item_transform: Sequence[Sequence[float]],
) -> dict[str, Any]:
    identity = f"{item['id']}/{part['child']}"
    name = item.get("name", item["id"])
    properties = {
        "Component ID": item["id"],
        "Component kind": "furnishing",
        "Procedural child ID": identity,
        "Floor level": room["level_id"],
        "room_id": item["room_id"],
        "generated_kind": item["generated"]["kind"],
        "adjustable": bool(item.get("adjustable")),
    }
    if item.get("cutaway_hidden"):
        properties["Cutaway hidden"] = True
    return kit_part_descriptor(
        part,
        identity=identity,
        component_id=item["id"],
        kind="furnishing",
        name=name if part["child"] == "body" else f"{name} / {part['child']}",
        collection=item.get("collection", "Furnishings"),
        transform=item_transform,
        binding={
            "target_id": item["id"],
            "slot": part["child"],
            "material_id": part["material_id"],
        },
        properties=properties,
        dependency_fingerprint=placement["dependency_fingerprint"],
        placement_fingerprint=placement["geometry_fingerprint"],
    )


def append_furnishings(
    bpy: Any,
    descriptors: Sequence[Mapping[str, Any]],
    library_path: str | Path,
    *,
    materials: Mapping[str, Any] | None = None,
) -> list[Any]:
    """Append only referenced catalog objects and parent them under stable roots."""
    from mathutils import Matrix  # type: ignore

    names = tuple(
        dict.fromkeys(
            name for item in descriptors if item["kind"] == "asset" for name in item["members"]
        )
    )
    prototypes = append_objects(bpy, library_path, names, FurnishingError)
    source_material_ids = {
        strip_copy_suffix(str(material.get("source_name"))): identifier
        for identifier, material in (materials or {}).items()
        if material.get("source_name")
    }
    roots: list[Any] = []
    for item in descriptors:
        if item["kind"] != "asset":
            continue
        destination = furnishing_collection(bpy, item["collection"])
        root = bpy.data.objects.new(item["name"], None)
        destination.objects.link(root)
        root.empty_display_type = "PLAIN_AXES"
        root["procedural_id"] = item["id"]
        root["room_id"] = item["room_id"]
        root["asset_id"] = item["asset_id"]
        root["fixed_dimensions_m"] = list(item["dimensions"])
        root.matrix_world = Matrix(item["transform"])
        source_frame = Matrix.Translation(item["source_origin"])
        members = [prototypes[name] for name in item["members"]]
        member_set = set(members)
        instances = {prototype: prototype.copy() for prototype in members}
        material_copies: dict[Any, Any] = {}
        for prototype, obj in instances.items():
            if prototype.data is not None:
                obj.data = prototype.data.copy()
                obj_materials = getattr(obj.data, "materials", None)
                if obj_materials is not None:
                    for index, material in enumerate(list(obj_materials)):
                        if material is not None:
                            if material not in material_copies:
                                copy = material.copy()
                                source_id = source_material_ids.get(
                                    strip_copy_suffix(material.name)
                                )
                                if source_id:
                                    copy["procedural_source_material_id"] = source_id
                                    copy["procedural_source_material_name"] = material.name
                                material_copies[material] = copy
                            obj_materials[index] = material_copies[material]
            destination.objects.link(obj)
        for member_name in item["members"]:
            prototype = prototypes[member_name]
            obj = instances[prototype]
            if prototype.parent in member_set:
                obj.parent = instances[prototype.parent]
                obj.matrix_parent_inverse = prototype.matrix_parent_inverse.copy()
                obj.matrix_basis = prototype.matrix_basis.copy()
            else:
                obj.parent = root
                obj.matrix_parent_inverse = Matrix.Identity(4)
                obj.matrix_basis = source_frame.inverted() @ prototype.matrix_basis
            obj["procedural_id"] = f"{item['id']}/{member_name}"
            obj["asset_member"] = member_name
            obj["Component ID"] = item["component_id"]
            obj["Component kind"] = "furnishing"
            obj["dependency_fingerprint"] = item["dependency_fingerprint"]
            obj["geometry_fingerprint"] = item["geometry_fingerprint"]
        roots.append(root)
    for prototype in prototypes.values():
        bpy.data.objects.remove(prototype, do_unlink=True)
    return roots


def instantiate_furnishings(
    bpy: Any,
    result: Mapping[str, Any],
    library_path: str | Path,
    *,
    materials: Mapping[str, Any] | None = None,
) -> dict[str, list[Any]]:
    """Instantiate fixed library assets and explicit generated cabinetry meshes."""
    from .mesh_descriptors import instantiate_meshes

    roots = append_furnishings(bpy, result["placements"], library_path, materials=materials)
    meshes = instantiate_meshes(bpy, result["meshes"], materials=materials)
    lights = instantiate_fixture_lights(bpy, result["placements"])
    return {"asset_roots": roots, "meshes": meshes, "lights": lights}


def create_fixture_light(
    bpy: Any, spec: Mapping[str, Any], *, identity: str, name: str, component_id: str
) -> Any:
    """Create one kit emitter in its owner's collection, tagged with that owner."""
    from mathutils import Matrix  # type: ignore

    data = bpy.data.lights.new(identity, spec["type"])
    configure_light(data, spec)
    obj = bpy.data.objects.new(name, data)
    furnishing_collection(bpy, spec["collection"]).objects.link(obj)
    obj.matrix_world = Matrix(spec["matrix"])
    obj["procedural_id"] = identity
    obj["Component ID"] = component_id
    obj["Component kind"] = "fixture-light"
    return obj


def instantiate_fixture_lights(bpy: Any, placements: Sequence[Mapping[str, Any]]) -> list[Any]:
    """Create each kit fixture's emitters beside its meshes, owned by the furnishing."""
    created = []
    for item in placements:
        for index, spec in enumerate(item.get("lights", [])):
            obj = create_fixture_light(
                bpy,
                {**spec, "collection": item["collection"]},
                identity=f"{item['id']}/light-{index:02d}-{spec['name']}",
                name=f"{item['name']} / {spec['name']} light",
                component_id=item["id"],
            )
            obj["room_id"] = item["room_id"]
            created.append(obj)
    return created


def furnishing_collection(bpy: Any, name: str) -> Any:
    """Keep assemblies in their declared collection so floor exclusions apply."""
    from .blender_datablocks import ensure_collection

    return ensure_collection(bpy, name, link_existing=True)


def relink_furnishings(
    bpy: Any, placements: Sequence[Mapping[str, Any]], assets: Mapping[str, Any]
) -> int:
    """Repair saved assembly links without changing objects, parents or transforms."""
    overrides = {item["id"]: item for item in placements}
    count = 0
    for root in list(bpy.data.objects):
        asset_id = root.get("asset_id")
        if asset_id not in assets:
            continue
        item = overrides.get(root.get("procedural_id"), {})
        destination = furnishing_collection(
            bpy, item.get("collection") or assets[asset_id]["collection"]
        )
        for obj in (root, *root.children_recursive):
            if destination not in obj.users_collection:
                destination.objects.link(obj)
            for old in list(obj.users_collection):
                if old != destination:
                    old.objects.unlink(obj)
            count += 1
    return count
