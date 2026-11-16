"""Legea 114/1996 Anexa nr. 1 corridor-width and main-bathroom access checks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from shapely import line_merge
from shapely.geometry import JOIN_STYLE, LineString
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .actual_geometry_checks import check_result
from .geometry import as_polygon, map_plan, wall_footprint
from .quantities import PASSAGE_OPENING_KINDS, ROOM_FLOOR_KIND, object_xy_footprint
from .transforms import affine_inverse_rigid, apply_point, wall_point

# A furnishing obstructs circulation when it starts low enough to block a wheelchair footrest
# and rises above floor coverings; wall-hung vanities, shelves and art leave the floor free.
OBSTACLE_MAX_BOTTOM_M = 0.25
OBSTACLE_MIN_TOP_M = 0.05
# Concept floor faces carry no plaster or tiling; widths within this allowance of the legal
# minimum may close once finishes are applied, so they need architect review.
FINISH_ALLOWANCE_M = 0.04
SEARCH_RESOLUTION_M = 0.001
CONTACT_TOLERANCE_M = 0.02
MIN_MOUTH_M = 0.5
# Half-width of the strip that bridges the floor-face inset across a wall-less zone edge.
MOUTH_BRIDGE_M = 0.15


def narrowest_neck_m(
    free: BaseGeometry, targets: Sequence[tuple[BaseGeometry, float]] = ()
) -> float:
    """Return the widest disc diameter that can travel through the free floor.

    Without targets the eroded floor must stay one piece, which measures the narrowest passage
    between its wide parts. With targets, one eroded piece must instead come within each target's
    own offset plus the disc radius, so dead-end stretches leading to a door also count. A single
    target constrains no route, so it falls back to the one-piece rule.
    """

    if len(targets) < 2:
        targets = ()

    def connected(radius: float) -> bool:
        eroded = free.buffer(-radius)
        if eroded.is_empty:
            return False
        if not targets:
            return eroded.geom_type == "Polygon"
        return any(
            all(
                piece.distance(point) <= offset + radius + CONTACT_TOLERANCE_M
                for point, offset in targets
            )
            for piece in getattr(eroded, "geoms", [eroded])
        )

    low, high = 0.0, max(free.bounds[2] - free.bounds[0], free.bounds[3] - free.bounds[1]) / 2
    if not connected(SEARCH_RESOLUTION_M):
        return 0.0
    while high - low > SEARCH_RESOLUTION_M / 2:
        middle = (low + high) / 2
        low, high = (middle, high) if connected(middle) else (low, middle)
    return round(2 * low, 3)


def largest_adjoining_square_m(free: BaseGeometry, target: BaseGeometry) -> float:
    """Return the side of the largest axis-aligned clear square touching the target footprint.

    Both inputs are in the rectilinear local plan frame, where a mitred erosion by half a side
    yields exactly the centres of the squares that fit.
    """

    def fits(side: float) -> bool:
        centres = free.buffer(-side / 2, join_style=JOIN_STYLE.mitre)
        reach = target.buffer(side / 2 + CONTACT_TOLERANCE_M, join_style=JOIN_STYLE.mitre)
        return not centres.is_empty and centres.intersects(reach)

    low, high = 0.0, max(free.bounds[2] - free.bounds[0], free.bounds[3] - free.bounds[1])
    while high - low > SEARCH_RESOLUTION_M / 2:
        middle = (low + high) / 2
        low, high = (middle, high) if fits(middle) else (low, middle)
    return round(low, 3)


def _room_floors(evidence: Mapping[str, Any]) -> dict[str, tuple[BaseGeometry, float]]:
    """Return every room's floor face and finished floor level from the actual export."""

    floors: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for obj in evidence["objects"]:
        room_id = obj.get("properties", {}).get("Room ID")
        if obj.get("kind") == ROOM_FLOOR_KIND and room_id:
            floors[str(room_id)].append(obj)
    return {
        room_id: (
            unary_union([object_xy_footprint(obj) for obj in objects]),
            max(float(vertex[2]) for obj in objects for vertex in obj["vertices_world"]),
        )
        for room_id, objects in floors.items()
    }


def _obstacles(
    design: Mapping[str, Any], evidence: Mapping[str, Any], room_id: str, floor_z: float
) -> dict[str, list[BaseGeometry]]:
    """Return low furnishings of the room and frame columns at its level, by component ID."""

    furnishing_ids = {
        item["id"] for item in design.get("furnishings", []) if item["room_id"] == room_id
    }
    obstacles: dict[str, list[BaseGeometry]] = defaultdict(list)
    for obj in evidence["objects"]:
        if obj.get("kind") == "column":
            low_band = (0.0, OBSTACLE_MAX_BOTTOM_M)
        elif obj.get("kind") == "furnishing" and obj["component_id"] in furnishing_ids:
            low_band = (OBSTACLE_MIN_TOP_M, OBSTACLE_MAX_BOTTOM_M)
        else:
            continue
        heights = [float(vertex[2]) - floor_z for vertex in obj["vertices_world"]]
        if min(heights) <= low_band[1] and max(heights) >= low_band[0]:
            obstacles[str(obj["component_id"])].append(object_xy_footprint(obj))
    return obstacles


def _free_floor(
    area: BaseGeometry, obstacles: Mapping[str, list[BaseGeometry]]
) -> tuple[BaseGeometry, list[str]]:
    """Subtract the obstacles that reach into the area and name them."""

    blocking = [
        (component_id, unary_union(parts))
        for component_id, parts in sorted(obstacles.items())
        if area.intersects(unary_union(parts))
    ]
    free = area.difference(unary_union([footprint for _, footprint in blocking]))
    return free, [component_id for component_id, _ in blocking]


def _open_mouths(design: Mapping[str, Any], room_id: str) -> list[tuple[str, BaseGeometry]]:
    """Return local zone edges that the room shares with a neighbour without any wall between."""

    rooms = {room["id"]: room for room in design["rooms"]}
    level_id = rooms[room_id]["level_id"]
    zone = as_polygon(rooms[room_id]["zone"])
    walls = unary_union(
        [
            as_polygon(wall_footprint(wall["start"], wall["end"], float(wall["thickness"])))
            for wall in design["walls"]
            if wall["level_id"] == level_id
        ]
    )
    mouths = []
    for other_id, other in rooms.items():
        if other_id == room_id or other["level_id"] != level_id:
            continue
        shared = zone.boundary.intersection(as_polygon(other["zone"]).boundary).difference(walls)
        if shared.length >= MIN_MOUTH_M:
            mouths.append((other_id, shared))
    return mouths


def _circulation(
    design: Mapping[str, Any],
    evidence: Mapping[str, Any],
    floors: Mapping[str, tuple[BaseGeometry, float]],
    room_id: str,
    opening_rooms: Mapping[str, Sequence[str]],
) -> tuple[BaseGeometry, list[tuple[BaseGeometry, float]], list[str], list[str]]:
    """Return the corridor's free floor, the doorways and mouths to reach, and the obstacles.

    Floor faces stop short of every zone edge, including wall-less ones, so each open mouth is
    bridged into the neighbouring floor; otherwise the inset would read as a false narrowing.
    Each doorway is its span on the wall centreline, carrying its distance from the floor, so a
    disc touching the wall face anywhere across the door reaches it, even beside a corner.
    """

    transform = design["transform"]
    floor, floor_z = floors[room_id]
    region = [floor]
    obstacles = _obstacles(design, evidence, room_id, floor_z)
    targets, labels = [], []
    for other_id, local_mouth in _open_mouths(design, room_id):
        if other_id not in floors:
            continue
        mouth = line_merge(map_plan(local_mouth, transform))
        region += [
            mouth.buffer(MOUTH_BRIDGE_M, cap_style="flat", join_style="mitre"),
            floors[other_id][0],
        ]
        obstacles.update(_obstacles(design, evidence, other_id, floors[other_id][1]))
        targets.append((mouth, 0.0))
        labels.append(other_id)
    walls = {wall["id"]: wall for wall in design["walls"]}
    for opening in design["openings"]:
        if (
            opening["kind"] not in PASSAGE_OPENING_KINDS
            or float(opening["sill"]) > 0.05
            or room_id not in opening_rooms[opening["id"]]
        ):
            continue
        wall = walls[opening["wall_id"]]
        span = LineString(
            apply_point(transform, (*wall_point(wall, offset), 0))[:2]
            for offset in (opening["offset"], opening["offset"] + opening["width"])
        )
        targets.append((span, floor.distance(span)))
        labels.append(opening["id"])
    free, obstacle_ids = _free_floor(unary_union(region), obstacles)
    return free, targets, labels, obstacle_ids


def _corridor_status(width: float, minimum: float) -> str:
    if width < minimum:
        return "fail"
    return "review" if width < minimum + FINISH_ALLOWANCE_M else "pass"


def authored_corridor_checks(
    design: Mapping[str, Any], catalog: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Report authored corridor zone widths so candidates see the legal rule before a build."""

    rule = catalog.get("corridor_width")
    if rule is None:
        return []
    zones = {room["id"]: as_polygon(room["zone"]) for room in design["rooms"]}
    return [
        check_result(
            f"corridor:authored:{room_id}",
            "review",
            "Authored zones run to wall centrelines; only the measured floor face is width evidence.",
            zone_min_width_m=narrowest_neck_m(zones[room_id]),
            minimum_m=rule["minimum_m"],
            source=rule["source"],
            requirement_ids=rule["requirement_ids"],
        )
        for room_id in rule["room_ids"]
    ]


def actual_corridor_checks(
    design: Mapping[str, Any],
    catalog: Mapping[str, Any],
    evidence: Mapping[str, Any],
    opening_rooms: Mapping[str, Sequence[str]],
) -> list[dict[str, Any]]:
    rule = catalog.get("corridor_width")
    if rule is None:
        return []
    minimum = float(rule["minimum_m"])
    floors = _room_floors(evidence)
    checks = []
    for room_id in rule["room_ids"]:
        if room_id not in floors:
            checks.append(
                check_result(
                    f"corridor:legea114:{room_id}",
                    "fail",
                    "Actual export lacks this corridor's floor face.",
                    requirement_ids=rule["requirement_ids"],
                )
            )
            continue
        free, targets, target_ids, obstacle_ids = _circulation(
            design, evidence, floors, room_id, opening_rooms
        )
        width = narrowest_neck_m(free, targets)
        status = _corridor_status(width, minimum)
        checks.append(
            check_result(
                f"corridor:legea114:{room_id}",
                status,
                {
                    "pass": "Measured clear corridor width meets the legal minimum with finish allowance.",
                    "review": "Measured clear corridor width meets the legal minimum only before finishes.",
                    "fail": "Measured clear corridor width is below the legal minimum.",
                }[status],
                measured_min_width_m=width,
                minimum_m=minimum,
                finish_allowance_m=FINISH_ALLOWANCE_M,
                route_targets=target_ids,
                obstacle_ids=obstacle_ids,
                method="widest disc reaching every doorway and open mouth over the floor face, "
                "bridged into open neighbours, minus low furnishings",
                source=rule["source"],
                requirement_ids=rule["requirement_ids"],
            )
        )
    return checks


def actual_bath_access_check(
    design: Mapping[str, Any],
    catalog: Mapping[str, Any],
    evidence: Mapping[str, Any],
    opening_rooms: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Report the wheelchair approach beside the main bathtub; the law sets no number to pass."""

    rule = catalog["main_bathroom_access"]
    room_id = rule["room_id"]
    check_id = f"bath-access:legea114:{room_id}"
    floors = _room_floors(evidence)
    tub_ids = {
        item["id"]
        for item in design.get("furnishings", [])
        if item["room_id"] == room_id and item.get("purpose") == "bathtub"
    }
    floor, floor_z = floors.get(room_id, (None, 0.0))
    obstacles = _obstacles(design, evidence, room_id, floor_z)
    tub_parts = [part for tub_id in tub_ids for part in obstacles.get(tub_id, [])]
    if floor is None or not tub_parts:
        return check_result(
            check_id,
            "fail",
            "Actual export lacks the main bathroom floor face or its bathtub.",
            requirement_ids=rule["requirement_ids"],
        )
    local = affine_inverse_rigid(design["transform"])
    free, obstacle_ids = _free_floor(floor, obstacles)
    door_widths = {
        opening["id"]: opening["width"]
        for opening in design["openings"]
        if opening["kind"] == "door" and room_id in opening_rooms[opening["id"]]
    }
    return check_result(
        check_id,
        "review",
        "Legea 114/1996 names no manoeuvre dimension; compare the clear square beside the bathtub "
        "and the door width with the NP 057-02 wheelchair references.",
        largest_clear_square_m=largest_adjoining_square_m(
            map_plan(free, local), map_plan(unary_union(tub_parts), local)
        ),
        reference_square_m=rule["reference_square_m"],
        door_opening_widths_m=door_widths,
        reference_door_clear_width_m=rule["reference_door_clear_width_m"],
        obstacle_ids=obstacle_ids,
        method="largest axis-aligned square of floor face minus low furnishings touching the bathtub",
        source=rule["source"],
        requirement_ids=rule["requirement_ids"],
    )


__all__ = [
    "actual_bath_access_check",
    "actual_corridor_checks",
    "authored_corridor_checks",
    "largest_adjoining_square_m",
    "narrowest_neck_m",
]
