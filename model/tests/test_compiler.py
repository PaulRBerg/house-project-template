from __future__ import annotations

import math
from copy import deepcopy

import pytest
from shapely.geometry import Polygon

from engine.compiler import (
    compile_design,
    frame_member_measures,
    frame_totals,
    make_component,
    stable_hash,
)


def test_stable_hash_normalizes_mapping_order() -> None:
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})
    assert stable_hash([1, 2]) != stable_hash([2, 1])


def test_component_dependency_fingerprint_propagates() -> None:
    first = make_component("level", "level", {"height": 3})
    second = make_component("level", "level", {"height": 4})
    child_a = make_component("room", "room", {"zone": []}, [first])
    child_b = make_component("room", "room", {"zone": []}, [second])
    assert child_a["dependencies"] == ["level"]
    assert child_a["fingerprint"] != child_b["fingerprint"]


def test_compile_is_deterministic_and_reports_quantities(design) -> None:
    first = compile_design(design)
    reordered = deepcopy(design)
    reordered["rooms"].reverse()
    reordered["walls"].reverse()
    reordered["openings"].reverse()
    second = compile_design(reordered)
    assert first["components"] == second["components"]
    assert first["fingerprint"] == second["fingerprint"]
    # The parcel area is measured from the polygon, which matches its reported area.
    assert first["quantities"]["parcel_area_m2"] == pytest.approx(
        Polygon(design["parcel"]["polygon"]["outer"]).area
    )
    assert first["quantities"]["parcel_area_m2"] == pytest.approx(
        design["parcel"]["reported_area_m2"], rel=0.01
    )
    assert {c["id"] for c in first["components"] if c["kind"] == "room"} == {
        room["id"] for room in design["rooms"]
    }


def test_wall_fingerprint_includes_sorted_opening_parameters(design) -> None:
    baseline = compile_design(design)
    changed = deepcopy(design)
    changed["openings"][0]["width"] -= 0.1
    compiled = compile_design(changed)
    wall_id = changed["openings"][0]["wall_id"]
    before = next(c for c in baseline["components"] if c["id"] == wall_id)
    after = next(c for c in compiled["components"] if c["id"] == wall_id)
    assert before["fingerprint"] != after["fingerprint"]


def test_material_change_updates_binding_without_rebuilding_mesh(design) -> None:
    changed = deepcopy(design)
    room_id = "G-LIV"
    first = compile_design(changed)
    next(item for item in changed["materials"] if item["id"] == "material-floor-oak")["color"] = [
        0,
        0,
        0,
        1,
    ]
    # Nested wall-finish materials stay out of the room's geometry fingerprint too.
    next(room for room in changed["rooms"] if room["id"] == room_id)["wall_finish"][
        "material_id"
    ] = "material-floor-oak"
    second = compile_design(changed)
    first_room = next(c for c in first["components"] if c["id"] == room_id)
    second_room = next(c for c in second["components"] if c["id"] == room_id)
    first_binding = next(c for c in first["components"] if c["id"] == f"binding-{room_id}-material")
    second_binding = next(
        c for c in second["components"] if c["id"] == f"binding-{room_id}-material"
    )
    assert first_room["fingerprint"] == second_room["fingerprint"]
    assert first_binding["fingerprint"] != second_binding["fingerprint"]


def test_furnishing_uses_room_and_asset_digest(design) -> None:
    changed = deepcopy(design)
    changed["furnishings"] = [{"id": "chair", "room_id": "G-LIV", "asset_id": "chair-asset"}]
    first = compile_design(changed, {"assets": [{"id": "chair-asset", "revision": 1}]})
    second = compile_design(changed, {"assets": [{"id": "chair-asset", "revision": 2}]})
    a = next(c for c in first["components"] if c["id"] == "chair")
    b = next(c for c in second["components"] if c["id"] == "chair")
    assert "G-LIV" in a["dependencies"]
    assert a["fingerprint"] != b["fingerprint"]


def test_frame_members_compile_deterministically_with_frame_quantities(design) -> None:
    first = compile_design(design)
    reordered = deepcopy(design)
    reordered["structure"].reverse()
    second = compile_design(reordered)

    def members(compiled):
        return [c for c in compiled["components"] if c["kind"] == "structural_member"]

    frame = [member for member in design["structure"] if member["kind"] != "axis"]
    assert members(first) == members(second)
    assert [c["id"] for c in members(first)] == sorted(member["id"] for member in frame)
    assert all(c["dependencies"] == [c["payload"]["level_id"]] for c in members(first))
    component_ids = {c["id"] for c in first["components"]}
    assert all(f"binding-{member['id']}-material" in component_ids for member in frame)
    assert not any(c["id"].startswith("axis-") for c in first["components"])

    quantities = first["quantities"]
    assert quantities["structure_column_count"] == sum(m["kind"] == "column" for m in frame)
    assert quantities["structure_beam_length_m"] == pytest.approx(
        sum(math.dist(m["start"], m["end"]) for m in frame if m["kind"] == "beam"), abs=1e-6
    )
    assert quantities["structure_concrete_m3"] == pytest.approx(
        sum(frame_member_measures(m)["volume_m3"] for m in frame), abs=1e-6
    )


def test_frame_totals_measure_nominal_sections() -> None:
    column = {
        "kind": "column",
        "section_m": [0.3, 0.6],
        "bottom_z_m": 0.0,
        "top_z_m": 3.0,
    }
    beam = {
        "kind": "beam",
        "start": [0, 0],
        "end": [4, 0],
        "width_m": 0.3,
        "bottom_z_m": 2.73,
        "top_z_m": 3.18,
    }
    assert frame_totals([column, beam]) == {
        "structure_column_count": 1,
        "structure_beam_length_m": 4.0,
        "structure_concrete_m3": pytest.approx(0.54 + 0.54),
    }
