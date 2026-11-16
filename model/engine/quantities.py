"""Geometry-derived quantities for design comparison and budget proposals."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union

from .double_height import cut_voids, measured_voids
from .geometry import as_polygon, wall_footprint
from .persistence import evidence_fingerprint

ROOM_FLOOR_KIND = "room_floor"
WALL_KIND = "wall"
PASSAGE_OPENING_KINDS = frozenset({"door", "open", "terrace"})


def _rounded(value: float) -> float:
    return round(float(value), 6)


def design_quantities(design: Mapping[str, Any]) -> dict[str, Any]:
    """Measure authored polygons without treating baseline evidence as an input.

    ``house_finished_gross_m2`` is intentionally absent until a saved, evaluated
    mesh export is audited. Each level's closed exterior-wall outline, grown by half
    the wall thickness, provides the wall-body comparison basis, including
    non-rectangular outlines.
    """

    room_areas = {room["id"]: _rounded(as_polygon(room["zone"]).area) for room in design["rooms"]}
    room_total = _rounded(sum(room_areas.values()))
    slab_areas = {
        slab["id"]: _rounded(
            cut_voids(design, as_polygon(slab["polygon"]), slab_id=slab["id"]).area
        )
        for slab in design["slabs"]
    }
    gross_by_level: dict[str, float] = {}
    envelope_by_level: dict[str, float] = {}
    for level in design["levels"]:
        level_id = level["id"]
        exterior_walls = [
            wall
            for wall in design["walls"]
            if wall["level_id"] == level_id and wall["role"] == "exterior"
        ]
        outlines = list(
            polygonize([LineString([wall["start"], wall["end"]]) for wall in exterior_walls])
        )
        if not outlines:
            raise ValueError(f"{level_id}: exterior walls do not form a closed gross-area outline")
        # Interior primary-wall lines may split the outer ring into multiple
        # polygonized faces. Unioning all bounded faces reconstructs the full
        # non-rectangular envelope without using a global bounding box or hull.
        outline = unary_union(outlines)
        thicknesses = {float(wall["thickness"]) for wall in exterior_walls}
        if len(thicknesses) != 1:
            raise ValueError(
                f"{level_id}: gross-area exterior wall thickness must be explicit and uniform"
            )
        envelope = outline.buffer(thicknesses.pop() / 2, join_style="mitre")
        envelope_by_level[level_id] = envelope.area
        gross_by_level[level_id] = cut_voids(design, envelope, level_id=level_id).area
    wall_footprints = {
        wall["id"]: as_polygon(wall_footprint(wall["start"], wall["end"], wall["thickness"]))
        for wall in design["walls"]
    }
    wall_footprint_area = _rounded(unary_union(list(wall_footprints.values())).area)
    opening_areas = {
        opening["id"]: _rounded(opening["width"] * (opening["head"] - opening["sill"]))
        for opening in design["openings"]
    }
    result: dict[str, Any] = {
        "rooms": room_areas,
        "room_zone_total_m2": room_total,
        "slabs": slab_areas,
        "house_wall_body_envelope_m2": _rounded(sum(envelope_by_level.values())),
        "house_wall_body_gross_m2": _rounded(sum(gross_by_level.values())),
        "house_wall_body_gross_by_level_m2": {
            key: _rounded(value) for key, value in sorted(gross_by_level.items())
        },
        "wall_footprint_union_m2": wall_footprint_area,
        "opening_area_m2": opening_areas,
        "opening_area_total_m2": _rounded(sum(opening_areas.values())),
        "opening_count": len(design["openings"]),
        "furnishing_count": len(design.get("furnishings", [])),
        "bathroom_fixture_count": sum(
            furnishing.get("purpose")
            in {"washlet", "toilet", "bidet", "shower", "bathtub", "bathroom-vanity"}
            for furnishing in design.get("furnishings", [])
        ),
    }
    return result


def _face_projection(vertices: Sequence[Sequence[float]], face: Sequence[int]) -> Polygon | None:
    points = [(float(vertices[index][0]), float(vertices[index][1])) for index in face]
    if len(set(points)) < 3:
        return None
    polygon = Polygon(points)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    return polygon if not polygon.is_empty and polygon.area > 1e-10 else None


def object_xy_footprint(obj: Mapping[str, Any]) -> Polygon:
    """Project evaluated world-space mesh faces to XY and union their areas."""

    vertices = obj.get("vertices_world")
    faces = obj.get("faces")
    if not isinstance(vertices, list) or not isinstance(faces, list):
        raise TypeError(
            f"{obj.get('id', '<object>')}: actual export needs vertices_world and faces"
        )
    polygons = [_face_projection(vertices, face) for face in faces]
    usable = [polygon for polygon in polygons if polygon is not None]
    if not usable:
        raise ValueError(f"{obj.get('id', '<object>')}: mesh has no XY footprint")
    return unary_union(usable)


def _filled_exterior_shell(polygons: Sequence[Polygon]) -> Polygon:
    """Fill closed exterior-boundary rings while retaining their actual outline."""

    merged = unary_union(polygons)
    if not isinstance(merged, Polygon) or merged.is_empty:
        raise ValueError("finished exterior boundary meshes do not form one closed connected shell")
    return Polygon(merged.exterior)


def measured_mesh_quantities(
    design: Mapping[str, Any], evidence: Mapping[str, Any], minimum_setback_m: float
) -> dict[str, Any]:
    """Measure independent, evaluated world-space mesh evidence.

    Gross-floor evidence must carry Floor level and a Gross area role of
    finished-exterior-boundary. Those evaluated meshes must collectively form
    the actual closed exterior wall/finish shell; their outer rings are filled
    so stairs and internal room gaps do not reduce gross area. Courtyards or
    other legitimate exclusions require independent evaluated meshes tagged
    excluded-void. Setback subjects are tagged with boolean Setback subject.
    """

    if evidence.get("evidence_kind") != "exported_mesh":
        raise ValueError("post-build evidence_kind must be 'exported_mesh'")
    if evidence.get("coordinate_space") != "world":
        raise ValueError("post-build mesh vertices must be evaluated world coordinates")
    if not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("saved_blend_sha256", ""))):
        raise ValueError("post-build evidence needs a lowercase saved_blend_sha256")
    provenance = evidence.get("provenance")
    if (
        not isinstance(provenance, Mapping)
        or not provenance.get("exporter")
        or not provenance.get("exported_at")
    ):
        raise ValueError("post-build evidence needs saved_blend_sha256 and provenance")
    objects = evidence.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("post-build evidence needs a non-empty objects array")

    wall_ids = {str(wall["id"]) for wall in design["walls"]}
    exterior_wall_levels = {
        wall["id"]: str(wall["level_id"]) for wall in design["walls"] if wall["role"] == "exterior"
    }
    covered_exterior_walls: set[str] = set()
    envelope_by_level: dict[str, list[Polygon]] = defaultdict(list)
    voids_by_level: dict[str, list[Polygon]] = defaultdict(list)
    floor_tops: dict[str, list[float]] = defaultdict(list)
    ceiling_undersides: dict[str, list[float]] = defaultdict(list)
    setbacks: list[tuple[str, Polygon]] = []
    room_footprints: dict[str, list[Polygon]] = defaultdict(list)
    component_ids: set[str] = set()
    for obj in objects:
        component_id = obj.get("component_id")
        if not isinstance(component_id, str) or not component_id:
            raise ValueError(f"{obj.get('id', '<object>')}: actual export needs component_id")
        component_ids.add(component_id)
        expected_fingerprint = evidence_fingerprint(obj.get("vertices_world"), obj.get("faces"))
        if obj.get("evaluated_geometry_fingerprint") != expected_fingerprint:
            raise ValueError(
                f"{obj.get('id', '<object>')}: evaluated geometry fingerprint is missing or stale"
            )
        properties = obj.get("properties", {})
        level_id = properties.get("Floor level")
        kind = obj.get("kind")
        gross_role = properties.get("Gross area role")
        needs_footprint = (
            kind in {ROOM_FLOOR_KIND, WALL_KIND, "facade"}
            or properties.get("Setback subject") is True
            or gross_role
            in {
                "finished-exterior-boundary",
                "excluded-void",
            }
        )
        footprint = object_xy_footprint(obj) if needs_footprint else None
        if gross_role in {"finished-exterior-boundary", "excluded-void"}:
            if level_id is None:
                raise ValueError(
                    f"{obj.get('id', '<object>')}: gross-area evidence needs Floor level"
                )
            if gross_role == "finished-exterior-boundary":
                source_id = properties.get("Gross boundary source")
                if not isinstance(source_id, str) or not source_id:
                    raise ValueError(
                        f"{obj.get('id', '<object>')}: Gross boundary source must be explicit"
                    )
                if component_id in wall_ids and source_id != component_id:
                    raise ValueError(
                        f"{obj.get('id', '<object>')}: an authored wall boundary must "
                        "reference its own component_id"
                    )
                source_level = exterior_wall_levels.get(str(source_id))
                if source_level is None:
                    raise ValueError(
                        f"{obj.get('id', '<object>')}: gross boundary does not reference "
                        "an authored exterior wall"
                    )
                if str(level_id) != source_level:
                    raise ValueError(
                        f"{obj.get('id', '<object>')}: gross boundary Floor level "
                        "does not match its exterior-wall source"
                    )
                covered_exterior_walls.add(str(source_id))
            assert footprint is not None
            target = (
                envelope_by_level if gross_role == "finished-exterior-boundary" else voids_by_level
            )
            target[str(level_id)].append(footprint)
        room_id = properties.get("Room ID")
        if room_id and kind == ROOM_FLOOR_KIND:
            assert footprint is not None
            room_footprints[str(room_id)].append(footprint)
        z_values = [float(vertex[2]) for vertex in obj["vertices_world"]]
        if level_id is not None and kind == ROOM_FLOOR_KIND:
            floor_tops[str(level_id)].append(max(z_values))
        if level_id is not None and kind == "ceiling":
            ceiling_undersides[str(level_id)].append(min(z_values))
        if properties.get("Setback subject") is True:
            assert footprint is not None
            setbacks.append((str(obj.get("id")), footprint))
    levels = {str(level["id"]) for level in design["levels"]}
    missing_exterior_walls = sorted(set(exterior_wall_levels) - covered_exterior_walls)
    if missing_exterior_walls:
        raise ValueError(
            "actual mesh evidence omits finished exterior boundary sources: "
            + ", ".join(missing_exterior_walls)
        )
    if set(envelope_by_level) != levels:
        raise ValueError(
            "actual mesh evidence is missing a finished exterior gross boundary for a design level"
        )
    if not setbacks:
        raise ValueError("actual mesh evidence has no objects tagged 'Setback subject'")

    void_measurements = measured_voids(design, objects, object_xy_footprint)
    gross_by_level = {}
    envelope_areas = {}
    for level, polygons in envelope_by_level.items():
        envelope = _filled_exterior_shell(polygons)
        envelope_areas[level] = envelope.area
        if voids_by_level[level]:
            excluded = unary_union(voids_by_level[level])
            if not envelope.covers(excluded):
                raise ValueError(f"{level}: an explicit gross-area void falls outside its envelope")
            envelope = envelope.difference(excluded)
        gross_by_level[level] = _rounded(envelope.area)
    room_areas = {
        room_id: _rounded(unary_union(polygons).area)
        for room_id, polygons in room_footprints.items()
    }
    if set(floor_tops) != levels or set(ceiling_undersides) != levels:
        raise ValueError(
            "actual mesh evidence is missing finished-floor or ceiling surfaces for clear-height checks"
        )
    clear_heights = {
        level: _rounded(min(ceiling_undersides[level]) - max(floor_tops[level]))
        for level in sorted(levels)
    }
    # Parcel vertices are already authored in world/site coordinates. The design
    # transform places house-local geometry into that parcel and must not be
    # applied a second time to the cadastral reconstruction.
    parcel = as_polygon(design["parcel"]["polygon"])
    allowed = parcel.buffer(-float(minimum_setback_m))
    setback_results = []
    for object_id, footprint in setbacks:
        clearance = footprint.distance(parcel.boundary)
        setback_results.append(
            {
                "object_id": object_id,
                "clearance_m": _rounded(clearance),
                "inside_inset": bool(allowed.covers(footprint)),
            }
        )
    return {
        "house_finished_envelope_m2": _rounded(sum(envelope_areas.values())),
        "double_height_voids": void_measurements,
        "house_finished_gross_m2": _rounded(sum(gross_by_level.values())),
        "house_finished_gross_by_level_m2": gross_by_level,
        "room_floor_area_m2": dict(sorted(room_areas.items())),
        "finished_clear_height_by_level_m": clear_heights,
        "minimum_setback_m": _rounded(min(item["clearance_m"] for item in setback_results)),
        "setbacks": sorted(setback_results, key=lambda item: item["object_id"]),
        "saved_blend_sha256": evidence["saved_blend_sha256"],
        "component_ids": sorted(component_ids),
    }
