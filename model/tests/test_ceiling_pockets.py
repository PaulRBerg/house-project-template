import math
from copy import deepcopy

import pytest
from shapely.ops import unary_union

from engine.architecture import compile_architecture
from engine.geometry import as_polygon


def _ceilings(design):
    meshes = compile_architecture(design)["meshes"]
    return {mesh["component_id"]: mesh for mesh in meshes if mesh["kind"] == "ceiling"}


def _underside_area(mesh):
    """Area of the triangulated underside cap, so a hole shows as missing area."""
    bottom = min(vertex[2] for vertex in mesh["vertices"])
    area = 0.0
    for face in mesh["faces"]:
        points = [mesh["vertices"][index] for index in face]
        if len(points) == 3 and all(abs(point[2] - bottom) < 1e-9 for point in points):
            (ax, ay, _), (bx, by, _), (cx, cy, _) = points
            area += abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) / 2
    return area


def _slab_area(design, slab_id):
    polygon = as_polygon(next(s for s in design["slabs"] if s["id"] == slab_id)["polygon"])
    voids = [
        as_polygon(v["polygon"]) for v in design.get("voids", []) if slab_id in v["cut_slab_ids"]
    ]
    return polygon.difference(unary_union(voids)).area


@pytest.fixture(scope="module")
def bare(design):
    """The design with every curtain hung from a surface track instead of a pocket."""
    changed = deepcopy(design)
    for item in changed["furnishings"]:
        if (item.get("generated") or {}).get("kind") == "curtain":
            item["generated"].setdefault("params", {}).pop("pocket", None)
    return changed


def test_curtain_without_pocket_leaves_the_ceiling_intact(bare):
    ceilings = _ceilings(bare)
    assert ceilings.keys() == {"ceiling-g", "ceiling-u"}
    for slab_id, mesh in ceilings.items():
        assert _underside_area(mesh) == pytest.approx(_slab_area(bare, slab_id))


def test_pocketed_curtain_cuts_only_its_own_level_ceiling(bare):
    changed = deepcopy(bare)
    ground = {room["id"] for room in changed["rooms"] if room["level_id"] == "G"}
    item = next(
        item
        for item in changed["furnishings"]
        if (item.get("generated") or {}).get("kind") == "curtain" and item["room_id"] in ground
    )
    item["generated"]["params"]["pocket"] = {"depth_m": 0.12}
    ceilings = _ceilings(changed)
    width, depth = item["dimensions"][:2]
    assert _underside_area(ceilings["ceiling-g"]) == pytest.approx(
        _slab_area(changed, "ceiling-g") - width * depth
    )
    room = next(room for room in changed["rooms"] if room["id"] == item["room_id"])
    angle = item["rotation"][2]
    cos, sin = math.cos(angle), math.sin(angle)
    for u, v in ((-width / 2, -depth / 2), (width / 2, depth / 2)):
        corner = [
            room["anchor"][0] + item["position"][0] + u * cos - v * sin,
            room["anchor"][1] + item["position"][1] + u * sin + v * cos,
        ]
        assert any(
            vertex[:2] == pytest.approx(corner, abs=1e-6)
            for vertex in ceilings["ceiling-g"]["vertices"]
        )
    assert ceilings["ceiling-u"] == _ceilings(bare)["ceiling-u"]
