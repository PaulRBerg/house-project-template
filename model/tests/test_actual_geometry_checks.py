from __future__ import annotations

from copy import deepcopy

import pytest

from engine.actual_geometry_checks import (
    actual_furnishing_checks,
    actual_opening_checks,
    actual_sliding_opening_checks,
)


def rectangle(identifier, component, kind, x0, y0, x1, y1, z0=0.0, z1=0.1, **properties):
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
        "faces": [[0, 1, 2, 3], [4, 5, 6, 7], [0, 4, 5, 1]],
        "properties": properties,
    }


@pytest.fixture(scope="module")
def design():
    return {
        "transform": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        "levels": [{"id": "G", "elevation_m": 0}],
        "rooms": [
            {
                "id": "G-ROOM",
                "level_id": "G",
                "anchor": [0, 0],
                "zone": {"outer": [[0, 0], [4, 0], [4, 4], [0, 4]], "holes": []},
            }
        ],
        "walls": [
            {
                "id": "wall-a",
                "level_id": "G",
                "start": [0, 0],
                "end": [4, 0],
                "thickness": 0.2,
            }
        ],
        "openings": [
            {
                "id": "opening-a",
                "wall_id": "wall-a",
                "kind": "door",
                "offset": 1.5,
                "width": 1,
                "sill": 0,
                "head": 2.1,
            }
        ],
        "furnishings": [
            {
                "id": "chair-a",
                "room_id": "G-ROOM",
                "position": [1, 1, 0],
                "rotation": [0, 0, 0],
                "dimensions": [1, 1, 1],
                "containment_policy": "floor",
            }
        ],
    }


def test_moved_furnishing_mesh_fails_even_with_same_component_id(design) -> None:
    evidence = {
        "objects": [
            rectangle("room", "G-ROOM", "room_floor", 0, 0, 4, 4, **{"Room ID": "G-ROOM"}),
            rectangle("chair", "chair-a", "furnishing", 0.5, 0.5, 1.5, 1.5),
        ]
    }
    assert actual_furnishing_checks(design, evidence)[0]["status"] == "pass"
    moved = deepcopy(evidence)
    for vertex in moved["objects"][1]["vertices_world"]:
        vertex[0] += 2
    assert actual_furnishing_checks(design, moved)[0]["status"] == "fail"


def test_filled_opening_fails_even_with_same_wall_component_id(design) -> None:
    clear = {
        "objects": [
            rectangle("left", "wall-a", "wall", 0, -0.1, 1.5, 0.1, 0, 2.7),
            rectangle("right", "wall-a", "wall", 2.5, -0.1, 4, 0.1, 0, 2.7),
        ]
    }
    assert actual_opening_checks(design, clear)[0]["status"] == "pass"
    filled = deepcopy(clear)
    filled["objects"].append(rectangle("filled", "wall-a", "wall", 1.5, -0.1, 2.5, 0.1, 0, 2.1))
    assert actual_opening_checks(design, filled)[0]["status"] == "fail"


def test_sliding_opening_requires_resolved_leaf_semantics_overlap_and_tracks(design) -> None:
    changed = deepcopy(design)
    opening = changed["openings"][0]
    opening.update(
        kind="terrace",
        operation="sliding",
        panel_count=2,
        slide_direction="toward-end",
    )
    evidence = {
        "objects": [
            rectangle(
                "opening-a/pane-00",
                "opening-a",
                "opening",
                1.55,
                -0.034,
                2.025,
                -0.016,
                **{
                    "Procedural child ID": "opening-a/pane-00",
                    "Opening operation": "sliding",
                    "Sliding panel index": 0,
                    "Sliding leaf role": "active",
                    "Slide direction": "toward-end",
                },
            ),
            rectangle(
                "opening-a/pane-01",
                "opening-a",
                "opening",
                1.975,
                0.016,
                2.45,
                0.034,
                **{
                    "Procedural child ID": "opening-a/pane-01",
                    "Opening operation": "sliding",
                    "Sliding panel index": 1,
                    "Sliding leaf role": "fixed",
                    "Slide direction": "toward-end",
                },
            ),
            rectangle(
                "opening-a/sliding-track-00",
                "opening-a",
                "opening",
                1.5,
                -0.032,
                2.5,
                -0.018,
                **{"Sliding track": True},
            ),
            rectangle(
                "opening-a/sliding-track-01",
                "opening-a",
                "opening",
                1.5,
                0.018,
                2.5,
                0.032,
                **{"Sliding track": True},
            ),
        ]
    }
    check = actual_sliding_opening_checks(changed, evidence)[0]
    assert check["status"] == "pass"
    assert check["evidence"]["tangent_overlap_m"] == pytest.approx(0.05)

    wrong_leaf = deepcopy(evidence)
    wrong_leaf["objects"][0]["properties"]["Sliding leaf role"] = "fixed"
    assert actual_sliding_opening_checks(changed, wrong_leaf)[0]["status"] == "fail"
