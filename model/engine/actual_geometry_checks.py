"""Independent checks over evaluated world-space candidate mesh evidence."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from shapely.ops import unary_union

from .geometry import furnishing_footprint, map_plan, wall_footprint
from .quantities import PASSAGE_OPENING_KINDS, ROOM_FLOOR_KIND, WALL_KIND, object_xy_footprint
from .transforms import apply_point, wall_point


def check_result(check_id: str, status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"id": check_id, "status": status, "message": message, "evidence": evidence}


def actual_furnishing_checks(
    design: Mapping[str, Any], evidence: Mapping[str, Any]
) -> list[dict[str, Any]]:
    rooms = {room["id"]: room for room in design["rooms"]}
    room_surfaces: dict[str, list[Any]] = defaultdict(list)
    meshes: dict[str, list[Any]] = defaultdict(list)
    for obj in evidence["objects"]:
        properties = obj.get("properties", {})
        if obj.get("kind") == ROOM_FLOOR_KIND and properties.get("Room ID"):
            room_surfaces[str(properties["Room ID"])].append(object_xy_footprint(obj))
        if obj.get("kind") == "furnishing":
            meshes[str(obj["component_id"])].append(object_xy_footprint(obj))
    actual_rooms = {room_id: unary_union(polygons) for room_id, polygons in room_surfaces.items()}
    checks = []
    for furnishing in design.get("furnishings", []):
        if furnishing.get("containment_policy", "floor") != "floor":
            checks.append(
                check_result(
                    f"actual-furnishing:{furnishing['id']}",
                    "review",
                    "This integrated or non-floor furnishing has no actual floor-containment gate.",
                    containment_policy=furnishing.get("containment_policy", "floor"),
                )
            )
            continue
        actual_parts = meshes.get(furnishing["id"], [])
        room = actual_rooms.get(furnishing["room_id"])
        if not actual_parts or room is None:
            checks.append(
                check_result(
                    f"actual-furnishing:{furnishing['id']}",
                    "fail",
                    "Actual export lacks furnishing or room-floor meshes.",
                    furnishing_mesh_count=len(actual_parts),
                    room_floor_present=room is not None,
                )
            )
            continue
        actual = unary_union(actual_parts)
        expected = map_plan(
            furnishing_footprint(rooms[furnishing["room_id"]], furnishing), design["transform"]
        )
        contained = room.buffer(0.05).covers(actual)
        expected_bounds = expected.bounds
        actual_bounds = actual.bounds
        bound_delta = max(abs(a - b) for a, b in zip(actual_bounds, expected_bounds, strict=True))
        # Captured reusable assemblies may use an asymmetric source origin (for
        # example a lamp root at its stem). The fixed authored envelope still
        # bounds that offset; 0.30 m tolerates the baseline origins while a
        # materially moved or resized assembly fails.
        placement_matches = bound_delta <= 0.3
        valid = contained and placement_matches
        checks.append(
            check_result(
                f"actual-furnishing:{furnishing['id']}",
                "pass" if valid else "fail",
                "Evaluated furnishing meshes match their fixed placement and room."
                if valid
                else "Evaluated furnishing meshes moved, changed size, or leave their room.",
                room_id=furnishing["room_id"],
                contained=contained,
                bounds_delta_m=round(bound_delta, 6),
                expected_bounds=[round(value, 6) for value in expected_bounds],
                actual_bounds=[round(value, 6) for value in actual_bounds],
            )
        )
    return checks


def actual_opening_checks(
    design: Mapping[str, Any], evidence: Mapping[str, Any]
) -> list[dict[str, Any]]:
    walls = {wall["id"]: wall for wall in design["walls"]}
    levels = {level["id"]: level for level in design["levels"]}
    wall_objects: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for obj in evidence["objects"]:
        if obj.get("kind") == WALL_KIND:
            wall_objects[str(obj["component_id"])].append(obj)
    footprints: dict[str, Any] = {}
    checks = []
    for opening in design["openings"]:
        if opening["kind"] not in PASSAGE_OPENING_KINDS:
            continue
        wall = walls[opening["wall_id"]]
        start = wall_point(wall, float(opening["offset"]))
        end = wall_point(wall, float(opening["offset"]) + float(opening["width"]))
        clear_xy = map_plan(
            wall_footprint(start, end, float(wall["thickness"]) * 1.02), design["transform"]
        )
        elevation = float(levels[wall["level_id"]]["elevation_m"])
        clear_bottom = elevation + float(opening["sill"])
        clear_top = elevation + float(opening["head"])
        intrusions = []
        for obj in wall_objects.get(wall["id"], []):
            vertices = obj["vertices_world"]
            if max(float(vertex[2]) for vertex in vertices) <= clear_bottom + 1e-5:
                continue
            if min(float(vertex[2]) for vertex in vertices) >= clear_top - 1e-5:
                continue
            if obj["id"] not in footprints:
                footprints[obj["id"]] = object_xy_footprint(obj)
            overlap = footprints[obj["id"]].intersection(clear_xy).area
            if overlap > 0.01:
                intrusions.append({"object_id": obj["id"], "overlap_m2": round(overlap, 6)})
        checks.append(
            check_result(
                f"actual-opening:{opening['id']}",
                "fail" if intrusions else "pass",
                "Generated wall geometry fills the modeled clear opening."
                if intrusions
                else "The evaluated wall meshes preserve the modeled clear opening.",
                wall_id=wall["id"],
                concept_overlap_tolerance_m2=0.01,
                intrusions=intrusions,
            )
        )
    return checks


def actual_sliding_opening_checks(
    design: Mapping[str, Any], evidence: Mapping[str, Any]
) -> list[dict[str, Any]]:
    transform = design["transform"]
    walls = {wall["id"]: wall for wall in design["walls"]}
    opening_objects: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for obj in evidence["objects"]:
        if obj.get("kind") == "opening":
            opening_objects[str(obj["component_id"])].append(obj)

    checks = []
    for opening in design["openings"]:
        if opening.get("operation") != "sliding":
            continue
        objects = opening_objects.get(opening["id"], [])
        panes = [
            obj
            for obj in objects
            if str(obj.get("properties", {}).get("Procedural child ID", ""))
            .rsplit("/", 1)[-1]
            .startswith("pane-")
        ]
        tracks = [obj for obj in objects if obj.get("properties", {}).get("Sliding track") is True]
        expected_active = 1 if opening["slide_direction"] == "toward-start" else 0
        panel_metadata = {
            int(obj.get("properties", {}).get("Sliding panel index", -1)): obj.get("properties", {})
            for obj in panes
        }
        metadata_matches = len(panes) == 2 and set(panel_metadata) == {0, 1}
        if metadata_matches:
            metadata_matches = all(
                properties.get("Opening operation") == "sliding"
                and properties.get("Slide direction") == opening["slide_direction"]
                and properties.get("Sliding leaf role")
                == ("active" if index == expected_active else "fixed")
                for index, properties in panel_metadata.items()
            )

        tangent_overlap = 0.0
        track_separation = 0.0
        if len(panes) == 2:
            wall = walls[opening["wall_id"]]
            start = apply_point(transform, (*wall["start"], 0))
            end = apply_point(transform, (*wall["end"], 0))
            dx, dy = end[0] - start[0], end[1] - start[1]
            length = math.hypot(dx, dy)
            tangent = (dx / length, dy / length)
            normal = (-tangent[1], tangent[0])

            def projected_bounds(
                obj: Mapping[str, Any], axis: tuple[float, float]
            ) -> tuple[float, float]:
                values = [
                    float(vertex[0]) * axis[0] + float(vertex[1]) * axis[1]
                    for vertex in obj["vertices_world"]
                ]
                return min(values), max(values)

            tangent_bounds = [projected_bounds(pane, tangent) for pane in panes]
            normal_bounds = [projected_bounds(pane, normal) for pane in panes]
            tangent_overlap = min(bound[1] for bound in tangent_bounds) - max(
                bound[0] for bound in tangent_bounds
            )
            normal_centers = [(lo + hi) / 2 for lo, hi in normal_bounds]
            track_separation = abs(normal_centers[0] - normal_centers[1])

        geometry_matches = tangent_overlap > 0.005 and track_separation > 0.005
        valid = metadata_matches and len(tracks) == 2 and geometry_matches
        checks.append(
            check_result(
                f"actual-sliding-opening:{opening['id']}",
                "pass" if valid else "fail",
                "Evaluated panes preserve the declared sliding leaf, direction, overlap, and tracks."
                if valid
                else "Evaluated opening geometry does not preserve the declared sliding operation.",
                pane_count=len(panes),
                track_count=len(tracks),
                active_panel=expected_active,
                slide_direction=opening["slide_direction"],
                metadata_matches=metadata_matches,
                tangent_overlap_m=round(tangent_overlap, 6),
                track_separation_m=round(track_separation, 6),
            )
        )
    return checks


def check_actual_placements_and_passages(
    design: Mapping[str, Any], evidence: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [
        *actual_furnishing_checks(design, evidence),
        *actual_opening_checks(design, evidence),
        *actual_sliding_opening_checks(design, evidence),
    ]


__all__ = [
    "actual_furnishing_checks",
    "actual_opening_checks",
    "actual_sliding_opening_checks",
    "check_actual_placements_and_passages",
]
