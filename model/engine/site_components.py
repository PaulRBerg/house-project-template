"""Parameterized site-component compilation using Blender-safe descriptors."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from itertools import pairwise
from pathlib import Path
from typing import Any

from .assets import asset_index
from .kit_geometry import centered_box
from .mesh_descriptors import kit_part_descriptor
from .persistence import transport_hash
from .transforms import finite_vector, rotation_translation

# The parcel ground sits below the paving datum, so flush site parts never z-fight with it.
PARCEL_GROUND_Z_M = -0.18
# The setback outline is a flat band just above the paving datum.
SETBACK_OUTLINE_Z_M = 0.08
SETBACK_OUTLINE_WIDTH_M = 0.05
PARCEL_GROUND_COLLECTION = "00 | Site & landscape"
SETBACK_OUTLINE_COLLECTION = "Site | Annotations"


class SiteComponentError(ValueError):
    pass


def _numbers(value: Any, size: int, field: str) -> list[float]:
    return finite_vector(value, size, field, SiteComponentError)


def _box(dimensions: Sequence[float]) -> tuple[list[list[float]], list[list[int]]]:
    x, y, z = dimensions
    if x <= 0 or y <= 0 or z < 0:
        raise SiteComponentError("box dimensions require positive X/Y and nonnegative Z")
    if z == 0:
        hx, hy = x / 2, y / 2
        return [[-hx, -hy, 0], [hx, -hy, 0], [hx, hy, 0], [-hx, hy, 0]], [[0, 1, 2, 3]]
    mesh = centered_box((x, y, z))
    return mesh["vertices"], mesh["faces"]


def _prism(
    outline: Sequence[Sequence[float]], height: float
) -> tuple[list[list[float]], list[list[int]]]:
    points = [_numbers(point, 2, "outline point") for point in outline]
    if len(points) < 3 or height < 0:
        raise SiteComponentError("prism requires at least three points and nonnegative height")
    vertices = [[*point, 0] for point in points]
    if height == 0:
        return vertices, [list(range(len(points)))]
    vertices += [[*point, height] for point in points]
    count = len(points)
    faces = [list(reversed(range(count))), list(range(count, count * 2))]
    faces += [[i, (i + 1) % count, (i + 1) % count + count, i + count] for i in range(count)]
    return vertices, faces


def _mesh_descriptor(
    component: Mapping[str, Any],
    part: Mapping[str, Any],
    dependency_fingerprint: str,
) -> dict[str, Any]:
    primitive = part.get("primitive", "box")
    if primitive == "box":
        dimensions = _numbers(part.get("dimensions"), 3, f"{part.get('id')}.dimensions")
        vertices, faces = _box(dimensions)
    elif primitive == "prism":
        vertices, faces = _prism(part.get("outline", []), float(part.get("height", 0)))
    else:
        raise SiteComponentError(f"{part.get('id')}: unsupported primitive {primitive!r}")
    position = _numbers(part.get("position", component.get("position", [0, 0, 0])), 3, "position")
    rotation = _numbers(part.get("rotation", component.get("rotation", [0, 0, 0])), 3, "rotation")
    identifier = part.get("id", component["id"])
    material_id = part.get("material_id", component.get("material_id"))
    geometry = {
        "primitive": primitive,
        "vertices": vertices,
        "faces": faces,
        "transform": rotation_translation(position, rotation),
    }
    return {
        "id": identifier,
        "component_id": component["id"],
        "kind": component.get("kind", "site"),
        "name": part.get("name", component.get("name", identifier)),
        "collection": component.get("collection", "Site"),
        "vertices": vertices,
        "faces": faces,
        "transform": geometry["transform"],
        "material_binding": {
            "target_id": identifier,
            "slot": "body",
            "material_id": material_id,
        },
        "properties": {
            "site_component_id": component["id"],
            **({"Setback subject": True} if component.get("setback_subject") else {}),
            "source_classification": component.get("source_classification", "generated_site"),
        },
        "dependency_fingerprint": dependency_fingerprint,
        "geometry_fingerprint": transport_hash(geometry),
    }


def _kit_descriptors(
    component: Mapping[str, Any],
    part: Mapping[str, Any],
    dependency_fingerprint: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Expand a ``generated`` kit part (fixture, plant) into role meshes and owned lights."""
    from .furnishings import generate_kit, kit_light_matrix

    identifier = part["id"]
    dimensions = _numbers(part.get("dimensions"), 3, f"{identifier}.dimensions")
    position = _numbers(part.get("position", [0, 0, 0]), 3, f"{identifier}.position")
    rotation = _numbers(part.get("rotation", [0, 0, 0]), 3, f"{identifier}.rotation")
    transform = rotation_translation(position, rotation)
    kit_parts, kit_lights = generate_kit(
        {"id": identifier, "generated": part["generated"], "dimensions": dimensions}
    )
    name = part.get("name", identifier)
    collection = component.get("collection", "Site")
    properties = {
        "site_component_id": component["id"],
        "generated_kind": part["generated"]["kind"],
        **({"Setback subject": True} if component.get("setback_subject") else {}),
        "source_classification": component.get("source_classification", "generated_site"),
    }
    placement = transport_hash(
        {"generated": part["generated"], "dimensions": dimensions, "transform": transform}
    )
    meshes = [
        kit_part_descriptor(
            kit,
            identity=f"{identifier}/{kit['child']}",
            component_id=component["id"],
            kind=component.get("kind", "site"),
            name=f"{name} / {kit['child']}",
            collection=collection,
            transform=transform,
            binding={
                "target_id": f"{identifier}/{kit['child']}",
                "slot": "body",
                "material_id": kit["material_id"],
            },
            properties=properties,
            dependency_fingerprint=dependency_fingerprint,
            placement_fingerprint=placement,
        )
        for kit in kit_parts
    ]
    lights = []
    for index, light in enumerate(kit_lights):
        spec = kit_light_matrix(light, transform)
        lights.append(
            {
                **spec,
                "id": f"{identifier}/light-{index:02d}-{light['name']}",
                "component_id": component["id"],
                "name": f"{name} / {light['name']} light",
                "collection": collection,
                "dependency_fingerprint": dependency_fingerprint,
                "geometry_fingerprint": transport_hash(spec),
            }
        )
    return meshes, lights


def _parcel_descriptors(
    design: Mapping[str, Any], setback_m: float | None, dependency_fingerprint: str
) -> list[dict[str, Any]]:
    """Ground over the parcel polygon and the setback outline, for each material the parcel names.

    Parcel vertices are site coordinates, so neither mesh takes the house transform.
    """
    from shapely.geometry import Polygon

    parcel = design["parcel"]
    outline = parcel["polygon"]["outer"]
    descriptors = []
    if material_id := parcel.get("ground_material_id"):
        ground = {"id": parcel["id"], "kind": "parcel", "collection": PARCEL_GROUND_COLLECTION}
        part = {
            "id": f"{parcel['id']}/ground",
            "name": "Parcel / ground",
            "primitive": "prism",
            "outline": outline,
            "height": 0,
            "position": [0, 0, PARCEL_GROUND_Z_M],
            "material_id": material_id,
        }
        descriptors.append(_mesh_descriptor(ground, part, dependency_fingerprint))
    if (material_id := parcel.get("setback_material_id")) and setback_m:
        band = {"id": parcel["id"], "kind": "parcel", "collection": SETBACK_OUTLINE_COLLECTION}
        inset = Polygon(outline).buffer(-setback_m, join_style="mitre")
        # A narrow parcel can split its inset into parts or leave none.
        rings = [polygon.exterior.coords for polygon in getattr(inset, "geoms", [inset])]
        width = SETBACK_OUTLINE_WIDTH_M
        edges = [edge for ring in rings for edge in pairwise(ring)]
        for index, (start, end) in enumerate(edges):
            length = math.dist(start, end)
            part = {
                "id": f"{parcel['id']}/setback-{index:02d}",
                "name": f"Parcel / {setback_m:g} m setback",
                "primitive": "box",
                # Each band overlaps its neighbours by half a width to close the corners.
                "dimensions": [length + width, width, 0],
                "position": [
                    (start[0] + end[0]) / 2,
                    (start[1] + end[1]) / 2,
                    SETBACK_OUTLINE_Z_M,
                ],
                "rotation": [0, 0, math.atan2(end[1] - start[1], end[0] - start[0])],
                "material_id": material_id,
            }
            descriptors.append(_mesh_descriptor(band, part, dependency_fingerprint))
    return descriptors


def compile_site_components(
    design: Mapping[str, Any],
    catalog: Mapping[str, Any] | None = None,
    compiled: Mapping[str, Any] | None = None,
    *,
    setback_m: float | None = None,
) -> dict[str, Any]:
    """Compile the parcel ground, setback outline, site meshes and reusable asset placements."""
    assets = asset_index(catalog) if catalog is not None else {}
    components = {item["id"]: item for item in (compiled or {}).get("components", [])}
    parcel = design["parcel"]
    meshes = _parcel_descriptors(
        design,
        setback_m,
        components.get(parcel["id"], {}).get("fingerprint", transport_hash(parcel)),
    )
    placements: list[dict[str, Any]] = []
    lights: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = [mesh["material_binding"] for mesh in meshes]
    for source in sorted(design.get("site_components", []), key=lambda item: item["id"]):
        item = dict(source)
        position = _numbers(item.get("position", [0, 0, 0]), 3, f"{item['id']}.position")
        rotation = _numbers(item.get("rotation", [0, 0, 0]), 3, f"{item['id']}.rotation")
        dependency = components.get(item["id"], {}).get("fingerprint", transport_hash(item))
        if item.get("asset_id"):
            asset = assets.get(item["asset_id"])
            if asset is None:
                raise SiteComponentError(f"{item['id']}: unknown asset_id {item['asset_id']!r}")
            dimensions = _numbers(item.get("dimensions"), 3, f"{item['id']}.dimensions")
            if any(
                not math.isclose(a, float(b), abs_tol=1e-6)
                # Both are validated 3-element [x, y, z] triplets.
                for a, b in zip(dimensions, asset["dimensions"], strict=True)
            ):
                raise SiteComponentError(f"{item['id']}: reusable site asset dimensions are fixed")
            placements.append(
                {
                    "id": item["id"],
                    "component_id": item["id"],
                    "kind": "asset",
                    "name": item.get("name", asset["name"]),
                    "collection": item.get("collection", asset["collection"]),
                    "asset_id": item["asset_id"],
                    "source_origin": list(asset["origin"]),
                    "members": list(asset["members"]),
                    "dimensions": dimensions,
                    "transform": rotation_translation(position, rotation),
                    "dependency_fingerprint": dependency,
                    "geometry_fingerprint": transport_hash(
                        {
                            "asset": item["asset_id"],
                            "dimensions": dimensions,
                            "position": position,
                            "rotation": rotation,
                        }
                    ),
                }
            )
            continue
        parts = item.get("parts") or [item]
        for part in parts:
            if part.get("generated"):
                kit_meshes, kit_lights = _kit_descriptors(item, part, dependency)
                meshes.extend(kit_meshes)
                lights.extend(kit_lights)
                bindings.extend(mesh["material_binding"] for mesh in kit_meshes)
                continue
            descriptor = _mesh_descriptor(item, part, dependency)
            meshes.append(descriptor)
            if descriptor["material_binding"]["material_id"]:
                bindings.append(descriptor["material_binding"])
    return {
        "generator": {"id": "engine.site_components", "version": "1.0.0"},
        "meshes": meshes,
        "placements": placements,
        "lights": lights,
        "material_bindings": bindings,
        "coverage": {
            "component_count": len(design.get("site_components", [])),
            "mesh_count": len(meshes),
            "asset_count": len(placements),
            "light_count": len(lights),
        },
        "fingerprint": transport_hash(
            {
                "meshes": meshes,
                "placements": placements,
                "lights": lights,
                "bindings": bindings,
            }
        ),
    }


def instantiate_site_components(
    bpy: Any,
    result: Mapping[str, Any],
    *,
    library_path: str | Path,
    materials: Mapping[str, Any] | None = None,
) -> dict[str, list[Any]]:
    """Build native site meshes and kit lights; append only referenced reusable assets."""
    from .furnishings import append_furnishings, create_fixture_light
    from .mesh_descriptors import instantiate_meshes

    objects = instantiate_meshes(bpy, result["meshes"], materials=materials)
    placements = [{**item, "room_id": "SITE"} for item in result["placements"]]
    roots = append_furnishings(bpy, placements, library_path)
    lights = []
    for spec in result.get("lights", []):
        obj = create_fixture_light(
            bpy, spec, identity=spec["id"], name=spec["name"], component_id=spec["component_id"]
        )
        obj["site_component_id"] = spec["component_id"]
        lights.append(obj)
    return {"meshes": objects, "lights": lights, "asset_roots": roots}
