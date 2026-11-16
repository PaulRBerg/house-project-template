from __future__ import annotations

import pytest
from shapely.geometry import Point, box

from engine.circulation_checks import (
    actual_bath_access_check,
    actual_corridor_checks,
    narrowest_neck_m,
)

IDENTITY = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
WALL = 0.16
INSET = WALL / 2


def prism(identifier, component, kind, x0, y0, x1, y1, z0=0.0, z1=0.0, **properties):
    return {
        "id": identifier,
        "component_id": component,
        "kind": kind,
        "vertices_world": [
            [x0, y0, z0],
            [x1, y0, z0],
            [x1, y1, z0],
            [x0, y1, z0],
            [x0, y0, z1],
            [x1, y0, z1],
            [x1, y1, z1],
            [x0, y1, z1],
        ],
        "faces": [[0, 1, 2, 3], [4, 5, 6, 7]],
        "properties": properties,
    }


def room(identifier, x0, y0, x1, y1):
    zone = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    return {"id": identifier, "level_id": "G", "zone": {"outer": zone, "holes": []}}


def floor(room_id, x0, y0, x1, y1, z=0.0):
    return prism(
        f"floor-{room_id}", room_id, "room_floor", x0, y0, x1, y1, z, z, **{"Room ID": room_id}
    )


def wall(identifier, start, end):
    return {"id": identifier, "level_id": "G", "start": start, "end": end, "thickness": WALL}


def corridor_case(width, *, furnishings=(), objects=(), open_end=False, corner_door=0.3):
    """A 6 m hall with a door near each end and an optional wall-less neighbour beyond it."""

    depth = width + WALL
    walls = [wall("wall-front", [0, 0], [6, 0]), wall("wall-back", [0, depth], [6, depth])]
    rooms = [room("G-HALL", 0, 0, 6, depth)]
    evidence = [floor("G-HALL", INSET, INSET, 6 - INSET, depth - INSET)]
    if open_end:
        rooms.append(room("G-NEXT", 6, 0, 9, depth))
        evidence.append(floor("G-NEXT", 6 + INSET, INSET, 9 - INSET, depth - INSET))
    else:
        walls.append(wall("wall-end", [6, 0], [6, depth]))
    design = {
        "transform": IDENTITY,
        "levels": [{"id": "G", "elevation_m": 0}],
        "rooms": rooms,
        "walls": walls,
        "openings": [
            {
                "id": "door-a",
                "wall_id": "wall-front",
                "kind": "door",
                "offset": 4.8,
                "width": 0.9,
                "sill": 0,
            },
            {
                "id": "door-b",
                "wall_id": "wall-back",
                "kind": "door",
                "offset": corner_door,
                "width": 0.9,
                "sill": 0,
            },
        ],
        "furnishings": list(furnishings),
    }
    catalog = {
        "corridor_width": {
            "minimum_m": 1.2,
            "room_ids": ["G-HALL"],
            "source": "test",
            "requirement_ids": ["LAY-05"],
        }
    }
    opening_rooms = {"door-a": ["G-HALL"], "door-b": ["G-HALL"]}
    return design, catalog, {"objects": [*evidence, *objects]}, opening_rooms


def test_neck_counts_dead_end_routes_only_through_targets():
    stub = box(0, 0, 3, 3).union(box(3, 0, 6, 1.0))

    assert narrowest_neck_m(stub) == pytest.approx(3.0, abs=0.002)
    route = [(Point(0, 1.5), 0.0), (Point(6, 0.5), 0.0)]
    assert narrowest_neck_m(stub, route) == pytest.approx(1.0, abs=0.002)


@pytest.mark.parametrize(("width", "status"), [(1.0, "fail"), (1.22, "review"), (1.25, "pass")])
def test_corridor_status_follows_the_measured_floor_width(width, status):
    check = actual_corridor_checks(*corridor_case(width))[0]

    assert check["id"] == "corridor:legea114:G-HALL"
    assert check["status"] == status
    assert check["evidence"]["measured_min_width_m"] == pytest.approx(width, abs=0.002)
    assert check["evidence"]["route_targets"] == ["door-a", "door-b"]


def test_door_beside_a_corner_is_reached_across_its_span():
    check = actual_corridor_checks(*corridor_case(1.3, corner_door=0.0))[0]

    assert check["evidence"]["measured_min_width_m"] == pytest.approx(1.3, abs=0.002)


def test_low_furnishings_and_columns_narrow_the_corridor_but_mats_do_not():
    furnishings = [
        {"id": "bench", "room_id": "G-HALL"},
        {"id": "mat", "room_id": "G-HALL"},
    ]
    objects = [
        prism("bench/body", "bench", "furnishing", 2.0, INSET, 3.0, INSET + 0.4, 0.0, 0.45),
        prism("mat/body", "mat", "furnishing", 1.0, INSET, 5.0, INSET + 1.4, 0.0, 0.01),
    ]
    check = actual_corridor_checks(*corridor_case(1.5, furnishings=furnishings, objects=objects))[0]
    assert check["status"] == "fail"
    assert check["evidence"]["measured_min_width_m"] == pytest.approx(1.1, abs=0.002)
    assert check["evidence"]["obstacle_ids"] == ["bench"]

    column = prism("column-a/body", "column-a", "column", 3.0, 1.38, 3.3, 1.88, 0.0, 3.0)
    check = actual_corridor_checks(*corridor_case(1.5, objects=[column]))[0]
    assert check["evidence"]["measured_min_width_m"] == pytest.approx(1.3, abs=0.002)
    assert check["evidence"]["obstacle_ids"] == ["column-a"]


def test_wall_less_mouth_bridges_the_floor_inset_into_the_neighbour():
    check = actual_corridor_checks(*corridor_case(1.3, open_end=True))[0]

    assert check["status"] == "pass"
    assert check["evidence"]["route_targets"] == ["G-NEXT", "door-a", "door-b"]
    assert check["evidence"]["measured_min_width_m"] == pytest.approx(1.3, abs=0.002)


def test_bath_access_reports_clear_square_beside_the_tub_and_door_width():
    design = {
        "transform": IDENTITY,
        "rooms": [room("U-BATH", 0, 0, 3.0, 2.5)],
        "openings": [
            {
                "id": "bath-door",
                "wall_id": "wall-front",
                "kind": "door",
                "offset": 2.0,
                "width": 0.9,
                "sill": 0,
            }
        ],
        "furnishings": [
            {"id": "tub", "room_id": "U-BATH", "purpose": "bathtub"},
            {"id": "wc", "room_id": "U-BATH", "purpose": "toilet"},
        ],
    }
    objects = [
        floor("U-BATH", 0, 0, 3.0, 2.5),
        prism("tub/body", "tub", "furnishing", 0, 1.75, 1.7, 2.5, 0.0, 0.6),
        prism("wc/body", "wc", "furnishing", 2.4, 1.8, 3.0, 2.5, 0.1, 0.5),
    ]
    catalog = {
        "main_bathroom_access": {
            "room_id": "U-BATH",
            "reference_square_m": 1.5,
            "reference_door_clear_width_m": 0.8,
            "source": "test",
            "requirement_ids": ["RM-UBATH-01"],
        }
    }
    check = actual_bath_access_check(
        design, catalog, {"objects": objects}, {"bath-door": ["U-BATH"]}
    )

    assert check["id"] == "bath-access:legea114:U-BATH"
    assert check["status"] == "review"
    assert check["evidence"]["largest_clear_square_m"] == pytest.approx(1.75, abs=0.002)
    assert check["evidence"]["door_opening_widths_m"] == {"bath-door": 0.9}
    assert check["evidence"]["obstacle_ids"] == ["tub", "wc"]
