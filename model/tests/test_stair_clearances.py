"""Spatial regressions for the stair, its under-stair storage and the frame around it."""

from copy import deepcopy

import pytest
from shapely.geometry import MultiPoint

from engine.architecture import compile_architecture
from engine.furnishings import compile_furnishings
from engine.geometry import as_polygon
from engine.transforms import apply_point


def _bounds(mesh):
    vertices = [apply_point(mesh["transform"], vertex) for vertex in mesh["vertices"]]
    return (
        MultiPoint([vertex[:2] for vertex in vertices]).convex_hull,
        min(vertex[2] for vertex in vertices),
        max(vertex[2] for vertex in vertices),
    )


@pytest.fixture(scope="module")
def stair_architecture(design):
    return compile_architecture(design)


def _stair_room(design, stair):
    zone = as_polygon(stair["zone"])
    return next(
        room
        for room in design["rooms"]
        if room["level_id"] == stair["from_level_id"] and as_polygon(room["zone"]).covers(zone)
    )


def test_under_stair_furnishings_clear_the_landing_and_return_flight(
    design, asset_catalog, stair_architecture
):
    stair = next(item for item in design["stairs"] if item["id"] == "stair-main")
    room = _stair_room(design, stair)
    selected = deepcopy(design)
    selected["furnishings"] = [
        item for item in selected["furnishings"] if item["room_id"] == room["id"]
    ]
    storage_ids = {
        item["id"]
        for item in selected["furnishings"]
        if (item.get("generated") or {}).get("kind") == "joinery"
    }
    assert storage_ids
    furnishings = compile_furnishings(selected, asset_catalog)["meshes"]
    overhead = [
        _bounds(mesh)
        for mesh in stair_architecture["meshes"]
        if mesh["id"] == "stair-main/landing" or mesh["id"].startswith("stair-main/flight-2-riser-")
    ]
    assert overhead
    checked = set()
    for mesh in furnishings:
        footprint, _, top = _bounds(mesh)
        for stair_footprint, underside, _ in overhead:
            if footprint.intersection(stair_footprint).area > 1e-8:
                checked.add(mesh["component_id"])
                assert top < underside, mesh["id"]
    assert storage_ids <= checked


def test_stair_hole_beams_clear_the_return_flight_and_its_arrival_band(design, stair_architecture):
    meshes = stair_architecture["meshes"]
    stair = next(item for item in design["stairs"] if item["id"] == "stair-main")
    upper = next(level for level in design["levels"] if level["id"] == stair["to_level_id"])
    arrival = upper["elevation_m"] + upper["floor_top_offset_m"]
    beams = {
        member["id"]
        for member in design["structure"]
        if member["kind"] == "beam" and member["level_id"] == stair["from_level_id"]
    }
    return_steps = [mesh for mesh in meshes if mesh["id"].startswith("stair-main/flight-2-riser-")]
    assert return_steps
    beam_meshes = [mesh for mesh in meshes if mesh["component_id"] in beams]
    assert beam_meshes
    for beam in beam_meshes:
        footprint, bottom, top = _bounds(beam)
        for step in return_steps:
            step_footprint, underside, surface = _bounds(step)
            assert surface < arrival
            if bottom < arrival and top > underside:
                assert footprint.intersection(step_footprint).area == pytest.approx(0, abs=1e-8), (
                    beam["id"]
                )
