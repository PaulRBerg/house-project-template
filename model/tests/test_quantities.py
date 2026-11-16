from __future__ import annotations

from copy import deepcopy

import pytest

from engine.persistence import evidence_fingerprint
from engine.quantities import design_quantities, measured_mesh_quantities


def rectangle_object(
    object_id: str,
    level: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    setback: bool = False,
    kind: str = "room_floor",
    z: float = 0,
    component_id: str | None = None,
    room_id: str | None = None,
    gross_role: str | None = None,
    boundary_source: str | None = None,
):
    properties = {"Floor level": level, "Setback subject": setback}
    if kind == "room_floor":
        properties["Room ID"] = room_id or object_id
    if gross_role is not None:
        properties["Gross area role"] = gross_role
        if gross_role == "finished-exterior-boundary":
            properties["Gross boundary source"] = boundary_source or component_id or object_id
    result = {
        "id": object_id,
        "component_id": component_id or object_id,
        "kind": kind,
        "vertices_world": [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]],
        "faces": [[0, 1, 2, 3]],
        "properties": properties,
    }
    result["evaluated_geometry_fingerprint"] = evidence_fingerprint(
        result["vertices_world"], result["faces"]
    )
    return result


@pytest.fixture(scope="module")
def minimum_setback(requirements):
    return requirements["setback"]["minimum_m"]


def test_wall_body_gross_ignores_slab_polygons(design):
    quantities = design_quantities(design)
    wall_body_gross = quantities["house_wall_body_gross_m2"]
    assert sum(quantities["slabs"].values()) > quantities["house_wall_body_gross_m2"]
    assert "house_finished_gross_m2" not in quantities
    changed = deepcopy(design)
    changed["slabs"].append(
        {
            "id": "test-slab-with-hole",
            "level_id": "G",
            "base_z_m": 0,
            "thickness_m": 0.1,
            "material_id": "material-slab-concept",
            "polygon": {
                "outer": [[0, 0], [4, 0], [4, 4], [0, 4]],
                "holes": [[[1, 1], [2, 1], [2, 2], [1, 2]]],
            },
        }
    )
    quantities = design_quantities(changed)
    assert quantities["slabs"]["test-slab-with-hole"] == 15.0
    assert quantities["house_wall_body_gross_m2"] == pytest.approx(wall_body_gross)


def test_measured_quantities_require_independent_world_mesh_evidence(
    voided_design, minimum_setback
):
    design = deepcopy(voided_design)
    design["transform"] = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    void = design["voids"][0]
    void["polygon"] = {"outer": [[8.2, 6.2], [8.7, 6.2], [8.7, 6.7], [8.2, 6.7]], "holes": []}
    exterior_ids = {
        level_id: [
            wall["id"]
            for wall in design["walls"]
            if wall["level_id"] == level_id and wall["role"] == "exterior"
        ]
        for level_id in ("G", "U")
    }
    boundary = "finished-exterior-boundary"
    evidence = {
        "evidence_kind": "exported_mesh",
        "coordinate_space": "world",
        "saved_blend_sha256": "a" * 64,
        "provenance": {"exporter": "test", "exported_at": "2026-09-21T00:00:00Z"},
        "objects": [
            rectangle_object("G-room-a", "G", 7.1, 5.1, 7.8, 6.9, room_id="G-room"),
            rectangle_object("G-room-b", "G", 8.2, 5.1, 8.9, 6.9, room_id="G-room"),
            rectangle_object("U-room", "U", 8.1, 6.1, 8.2, 6.9, z=3.3),
            rectangle_object("G-living", "G", 8.2, 6.2, 8.7, 6.7, room_id=void["room_below_id"]),
            rectangle_object(
                void["id"],
                "U",
                8.2,
                6.2,
                8.7,
                6.7,
                kind="void",
                gross_role="excluded-void",
            ),
            rectangle_object("G-ceiling", "G", 7, 5, 9, 7, kind="ceiling", z=3.0),
            rectangle_object("U-ceiling", "U", 8, 6, 9, 7, kind="ceiling", z=6.0),
            rectangle_object(
                "G-wall-s",
                "G",
                7,
                5,
                9,
                5.1,
                setback=True,
                kind="wall",
                component_id=exterior_ids["G"][0],
                gross_role=boundary,
            ),
            rectangle_object(
                "G-wall-n",
                "G",
                7,
                6.9,
                9,
                7,
                kind="wall",
                component_id=exterior_ids["G"][1],
                gross_role=boundary,
            ),
            rectangle_object(
                "G-wall-w",
                "G",
                7,
                5.1,
                7.1,
                6.9,
                kind="wall",
                component_id=exterior_ids["G"][2],
                gross_role=boundary,
            ),
            rectangle_object(
                "G-wall-e",
                "G",
                8.9,
                5.1,
                9,
                6.9,
                kind="wall",
                component_id=exterior_ids["G"][3],
                gross_role=boundary,
            ),
            rectangle_object(
                "U-wall-s",
                "U",
                8,
                6,
                9,
                6.1,
                kind="wall",
                component_id=exterior_ids["U"][0],
                gross_role=boundary,
            ),
            rectangle_object(
                "U-wall-n",
                "U",
                8,
                6.9,
                9,
                7,
                kind="wall",
                component_id=exterior_ids["U"][1],
                gross_role=boundary,
            ),
            rectangle_object(
                "U-wall-w",
                "U",
                8,
                6.1,
                8.1,
                6.9,
                kind="wall",
                component_id=exterior_ids["U"][2],
                gross_role=boundary,
            ),
            rectangle_object(
                "U-wall-e",
                "U",
                8.9,
                6.1,
                9,
                6.9,
                kind="wall",
                component_id=exterior_ids["U"][3],
                gross_role=boundary,
            ),
        ],
    }
    for level_id, coordinates in {
        "G": (7, 5, 9, 5.1),
        "U": (8, 6, 9, 6.1),
    }.items():
        for index, component_id in enumerate(exterior_ids[level_id][4:], start=4):
            evidence["objects"].append(
                rectangle_object(
                    f"{level_id}-wall-extra-{index}",
                    level_id,
                    *coordinates,
                    kind="wall",
                    component_id=component_id,
                    gross_role=boundary,
                )
            )
    measured = measured_mesh_quantities(design, evidence, minimum_setback)
    assert measured["house_finished_gross_m2"] == 4.75
    assert measured["room_floor_area_m2"]["G-room"] == pytest.approx(2.52)
    assert measured["finished_clear_height_by_level_m"] == {"G": 3.0, "U": 2.7}
    assert measured["minimum_setback_m"] > 2.0
    assert measured["double_height_voids"][void["id"]] == {
        "excluded_floor_m2": 0.25,
        "finished_clear_height_m": 6.0,
        "blocked_slab_floor_m2": 0.0,
    }
    missing_void = deepcopy(evidence)
    missing_void["objects"] = [
        obj for obj in missing_void["objects"] if obj["component_id"] != void["id"]
    ]
    with pytest.raises(ValueError, match="missing evaluated exclusion mesh"):
        measured_mesh_quantities(design, missing_void, minimum_setback)
    wrong_marker = deepcopy(evidence)
    marker = next(obj for obj in wrong_marker["objects"] if obj["component_id"] == void["id"])
    for vertex in marker["vertices_world"]:
        vertex[0] += 0.01
    marker["evaluated_geometry_fingerprint"] = evidence_fingerprint(
        marker["vertices_world"], marker["faces"]
    )
    with pytest.raises(ValueError, match="evaluated exclusion differs from the authored void"):
        measured_mesh_quantities(design, wrong_marker, minimum_setback)
    for kind in ("slab", "room_floor"):
        blocked_void = deepcopy(evidence)
        blocked_void["objects"].append(
            rectangle_object(
                "uncut-surface",
                "U",
                8.2,
                6.2,
                8.7,
                6.7,
                kind=kind,
                component_id=void["cut_slab_ids"][0] if kind == "slab" else "uncut-upper-floor",
            )
        )
        with pytest.raises(ValueError, match="evaluated slab/floor still covers"):
            measured_mesh_quantities(design, blocked_void, minimum_setback)
    intended = {**evidence, "evidence_kind": "generator-descriptor"}
    with pytest.raises(ValueError, match="exported_mesh"):
        measured_mesh_quantities(design, intended, minimum_setback)

    detached = deepcopy(evidence)
    detached["objects"].append(
        rectangle_object(
            "detached-shed",
            "G",
            20,
            20,
            24,
            24,
            kind="site_component",
            component_id="site-detached-shed",
        )
    )
    assert (
        measured_mesh_quantities(design, detached, minimum_setback)["house_finished_gross_m2"]
        == 4.75
    )

    facade_finish = deepcopy(evidence)
    facade_finish["objects"].append(
        rectangle_object(
            "facade-finish",
            "G",
            7,
            5,
            9,
            5.1,
            kind="facade",
            component_id="facade-finish-g",
            gross_role=boundary,
            boundary_source=exterior_ids["G"][0],
        )
    )
    assert (
        measured_mesh_quantities(design, facade_finish, minimum_setback)["house_finished_gross_m2"]
        == 4.75
    )

    explicit_void = deepcopy(evidence)
    explicit_void["objects"].append(
        rectangle_object(
            "courtyard-void",
            "G",
            7.5,
            5.5,
            8,
            6,
            kind="site_component",
            gross_role="excluded-void",
        )
    )
    assert (
        measured_mesh_quantities(design, explicit_void, minimum_setback)["house_finished_gross_m2"]
        == 4.5
    )

    omitted = deepcopy(evidence)
    omitted["objects"] = [
        obj for obj in omitted["objects"] if obj["component_id"] != exterior_ids["G"][0]
    ]
    with pytest.raises(ValueError, match="omits finished exterior boundary sources"):
        measured_mesh_quantities(design, omitted, minimum_setback)

    interior_wall_id = next(wall["id"] for wall in design["walls"] if wall["role"] == "interior")
    mislabeled = deepcopy(evidence)
    mislabeled["objects"].append(
        rectangle_object(
            "mislabeled-inner-wall",
            "G",
            7.5,
            5.5,
            7.6,
            6.5,
            kind="wall",
            component_id=interior_wall_id,
            gross_role=boundary,
        )
    )
    with pytest.raises(ValueError, match="authored exterior wall"):
        measured_mesh_quantities(design, mislabeled, minimum_setback)
