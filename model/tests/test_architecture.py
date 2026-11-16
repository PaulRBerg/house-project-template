from __future__ import annotations

import math
from copy import deepcopy

import pytest

from engine.architecture import FRAME_FACE_INSET_M, compile_architecture
from engine.compiler import frame_member_measures
from engine.design_package import DesignValidationError
from engine.geometry import roof_covering_z
from engine.mesh_descriptors import ROOF_CAP_SOLAR


@pytest.fixture(scope="module")
def result(design):
    return compile_architecture(design)


def test_current_room_areas_are_generated_without_using_historical_evidence(design, result):
    changed = deepcopy(design)
    room_id = changed["rooms"][0]["id"]
    changed["baseline_evidence"] = {
        "source_revision": "synthetic",
        "room_finished_floors": [
            {
                "room_id": room_id,
                "area_m2": 1,
                "polygon": {"outer": [[0, 0], [1, 0], [1, 1], [0, 1]], "holes": []},
            }
        ],
    }
    compared = compile_architecture(changed)
    assert result["meshes"] == compared["meshes"]
    generated = result["quantities"]["rooms"][room_id]["area_m2"]
    assert compared["coverage"]["baseline_comparison"] == {
        room_id: {"baseline_m2": 1, "generated_m2": generated, "delta_m2": generated - 1}
    }


def test_changed_room_retains_concavity_and_hole(design):
    design = deepcopy(design)
    room = design["rooms"][0]
    room.update(
        zone={
            "outer": [[30, 30], [35, 30], [35, 32], [33, 32], [33, 35], [30, 35]],
            "holes": [[[31, 31], [32, 31], [32, 32], [31, 32]]],
        },
        floor_inset_m=0,
        anchor=[30.5, 30.5],
    )
    # The moved zone no longer meets the walls its finish names.
    room.pop("wall_finish", None)
    generated = compile_architecture(design)
    assert generated["quantities"]["rooms"][room["id"]]["area_m2"] == pytest.approx(18)
    (polygon,) = generated["quantities"]["rooms"][room["id"]]["polygons"]
    assert len(polygon["holes"]) == 1


def test_angled_wall_opening_is_cut_and_moving_opening_propagates(design, signed_volume, subtests):
    design = deepcopy(design)
    wall = {
        "id": "wall-angle",
        "name": "angle",
        "level_id": "G",
        "start": [25, 25],
        "end": [28, 29],
        "thickness": 0.2,
        "material_id": "material-partition-concept",
        "role": "interior",
    }
    opening = {
        "id": "opening-angle",
        "wall_id": wall["id"],
        "kind": "window",
        "offset": 1,
        "width": 1.2,
        "sill": 0.5,
        "head": 2,
    }
    design["walls"].append(wall)
    design["openings"].append(opening)
    first = compile_architecture(design)
    target = [m for m in first["meshes"] if m["component_id"] == wall["id"] and m["kind"] == "wall"]
    assert sum(signed_volume(m) for m in target) == pytest.approx(
        (5 * design["levels"][0]["clear_height_m"] - 1.2 * 1.5) * 0.2
    )
    for mesh in target:
        mid = [sum(v[i] for v in mesh["vertices"]) / len(mesh["vertices"]) for i in range(3)]
        u = (mid[0] - 25) * 0.6 + (mid[1] - 25) * 0.8
        with subtests.test(mesh_id=mesh["id"]):
            assert not (1 < u < 2.2 and 0.5 < mid[2] < 2)
    opening["offset"] = 2
    second = compile_architecture(design)
    old = {m["id"]: m["geometry_fingerprint"] for m in first["meshes"]}
    new = {m["id"]: m["geometry_fingerprint"] for m in second["meshes"]}
    assert old[wall["id"] + "/span-000-0-low"] != new[wall["id"] + "/span-000-0-low"]
    floor = next(room["id"] for room in design["rooms"] if room["level_id"] != "G") + "/floor-00"
    assert old[floor] == new[floor]


def test_material_only_change_preserves_geometry_and_mesh_identity(design):
    design = deepcopy(design)
    a = compile_architecture(design)
    next(item for item in design["materials"] if item["id"] == "material-floor-oak")["color"] = [
        0,
        0,
        1,
        1,
    ]
    room = next(room for room in design["rooms"] if "wall_finish" in room)
    room["material_id"] = "material-floor-stone"
    room["wall_finish"]["material_id"] = "material-floor-oak"
    b = compile_architecture(design)
    assert any(
        m["material_binding"]["material_id"] == "material-floor-oak"
        for m in b["meshes"]
        if m["kind"] == "wall_finish"
    )
    assert {m["id"]: m["geometry_fingerprint"] for m in a["meshes"]} == {
        m["id"]: m["geometry_fingerprint"] for m in b["meshes"]
    }


def test_determinism_and_semantic_ownership(design, result, subtests):
    design = deepcopy(design)
    for key in ["rooms", "walls", "openings", "roofs", "slabs", "stairs"]:
        design[key].reverse()
    assert result["meshes"] == compile_architecture(design)["meshes"]
    assert len(result["meshes"]) == len({m["id"] for m in result["meshes"]})
    for mesh in result["meshes"]:
        with subtests.test(mesh_id=mesh["id"]):
            assert mesh["transform"] == design["transform"]
            assert mesh["properties"]["Component ID"] == mesh["component_id"]
            assert len(mesh["geometry_fingerprint"]) == 64


def test_explicit_exterior_roles_cover_sources_without_tagging_overhangs(design, result, subtests):
    exterior = {wall["id"] for wall in design["walls"] if wall["role"] == "exterior"}
    assert exterior
    tagged = [
        mesh
        for mesh in result["meshes"]
        if mesh["properties"].get("Gross area role") == "finished-exterior-boundary"
    ]
    assert {mesh["properties"]["Gross boundary source"] for mesh in tagged} == exterior
    for mesh in tagged:
        with subtests.test(mesh_id=mesh["id"]):
            assert mesh["kind"] in ("wall", "facade")
            assert mesh["properties"]["Wall role"] == "exterior"
            assert mesh["properties"]["Gross area role"] == "finished-exterior-boundary"
            assert mesh["properties"]["Gross boundary source"] == mesh["component_id"]
            assert mesh["properties"]["Floor level"] in ("G", "U")
    for mesh in result["meshes"]:
        if mesh["kind"] in ("roof", "roof_trim", "skirting", "slab"):
            with subtests.test(mesh_id=mesh["id"]):
                assert "Gross area role" not in mesh["properties"]


def test_boundary_classification_is_independent_of_material_and_wall_name(design, result):
    design = deepcopy(design)
    for wall in design["walls"]:
        wall["material_id"] = "mat_glass"
        wall["name"] = "Unrelated material-neutral name"
    changed = compile_architecture(design)

    def tags(r):
        return {mesh["id"]: mesh["properties"].get("Gross boundary source") for mesh in r["meshes"]}

    assert tags(result) == tags(changed)
    assert {mesh["id"]: (mesh["vertices"], mesh["faces"]) for mesh in result["meshes"]} == {
        mesh["id"]: (mesh["vertices"], mesh["faces"]) for mesh in changed["meshes"]
    }


def test_wall_role_is_required_and_exterior_requires_authored_side(design):
    missing_role = deepcopy(design)
    del missing_role["walls"][0]["role"]
    with pytest.raises(DesignValidationError, match="role"):
        compile_architecture(missing_role)
    missing_side = deepcopy(design)
    exterior = next(wall for wall in missing_side["walls"] if wall["role"] == "exterior")
    del exterior["exterior_side"]
    with pytest.raises(DesignValidationError, match="exterior_side"):
        compile_architecture(missing_side)


def test_floor_top_offset_can_align_levels(design, result, subtests):
    aligned = deepcopy(design)
    elevations = {level["id"]: level["elevation_m"] for level in aligned["levels"]}
    for level in aligned["levels"]:
        level["floor_top_offset_m"] = 0
    changed = compile_architecture(aligned)
    for mesh in changed["meshes"]:
        if mesh["kind"] == "room_floor":
            with subtests.test(mesh_id=mesh["id"]):
                elevation = elevations[mesh["properties"]["Floor level"]]
                assert max(vertex[2] for vertex in mesh["vertices"]) == pytest.approx(elevation)
                assert min(vertex[2] for vertex in mesh["vertices"]) == pytest.approx(
                    elevation - 0.002
                )
    assert (
        result["quantities"]["totals"]["heated_floor_face_m2"]
        == changed["quantities"]["totals"]["heated_floor_face_m2"]
    )


def test_frame_members_are_inset_nominal_boxes_in_frame_collections(design, result, signed_volume):
    inset = 2 * FRAME_FACE_INSET_M
    frame = {m["id"]: m for m in design["structure"] if m["kind"] != "axis"}
    meshes = [mesh for mesh in result["meshes"] if mesh["component_id"] in frame]
    assert sorted(mesh["component_id"] for mesh in meshes) == sorted(frame)
    for mesh in meshes:
        member = frame[mesh["component_id"]]
        properties = mesh["properties"]
        assert mesh["collection"] == f"{member['level_id']} | Frame"
        assert mesh["kind"] == properties["Component kind"] == member["kind"]
        assert properties["Structure mark"] == member["mark"]
        assert "Setback subject" not in properties
        assert "Gross area role" not in properties
        depth = member["top_z_m"] - member["bottom_z_m"]
        if member["kind"] == "column":
            sx, sy = member["section_m"]
            expected = (sx - inset) * (sy - inset) * (depth - inset)
            assert "Structure placement" not in properties
        else:
            length = math.dist(member["start"], member["end"])
            expected = (length - inset) * (member["width_m"] - inset) * (depth - inset)
            assert properties["Structure placement"] == member["placement"]
        assert signed_volume(mesh) == pytest.approx(expected)
        assert result["quantities"]["structure"][member["id"]] == {
            "kind": member["kind"],
            "level_id": member["level_id"],
            "mark": member["mark"],
            **frame_member_measures(member),
        }
    by_id = {mesh["component_id"]: mesh["properties"] for mesh in meshes}
    column = next(member for member in frame.values() if member["kind"] == "column")
    sx, sy = column["section_m"]
    assert by_id[column["id"]]["Structure section"] == f"{round(sx * 100)}×{round(sy * 100)}"
    member = next(member for member in frame.values() if member["kind"] == "beam")
    assert (
        by_id[member["id"]]["Structure section"]
        == f"{round(member['width_m'] * 100)}×{round((member['top_z_m'] - member['bottom_z_m']) * 100)}"
    )
    assert result["quantities"]["totals"]["structure_column_count"] == sum(
        member["kind"] == "column" for member in frame.values()
    )


def test_roof_body_fills_the_build_up_from_deck_to_covering(design, result, subtests):
    bodies = {mesh["component_id"]: mesh for mesh in result["meshes"] if mesh["kind"] == "roof"}
    for roof in design["roofs"]:
        with subtests.test(roof=roof["id"]):
            vertices = bodies[roof["id"]]["vertices"]
            deck = [v for v in vertices if v[2] == pytest.approx(roof["deck_z_m"])]
            covering = [v for v in vertices if v not in deck]
            assert len(deck) == len(covering)
            for vertex in covering:
                assert vertex[2] == pytest.approx(roof_covering_z(roof, vertex))
    roof_slabs = {slab["id"] for slab in design["slabs"] if slab.get("role") == "roof"}
    assert roof_slabs
    for mesh in result["meshes"]:
        if mesh["component_id"] in roof_slabs:
            assert mesh["collection"] == ROOF_CAP_SOLAR
