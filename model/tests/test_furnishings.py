import math
from copy import deepcopy

import pytest

from engine.compiler import compile_design
from engine.furnishings import (
    FurnishingError,
    compile_furnishings,
    validate_furnishings,
)
from engine.persistence import strip_copy_suffix


def _with_asset_furnishing(design, asset_catalog, room_id="G-LIV"):
    """A copy of the design holding one catalog furniture asset placed in ``room_id``.

    The demo furnishes every room with generated kits, so asset placements are synthetic.
    Asset furnishings swap the catalog's x and y extents for the house basis.
    """
    asset = next(
        item for item in asset_catalog["assets"] if item["classification"] == "reusable_furniture"
    )
    x, y, z = asset["dimensions"]
    changed = deepcopy(design)
    changed["furnishings"].append(
        {
            "id": "asset-test",
            "room_id": room_id,
            "anchor": "room",
            "position": [0.4, 0.3, z / 2],
            "rotation": [0, 0, 0.3],
            "dimensions": [y, x, z],
            "clearance_m": {"front": 0, "back": 0, "left": 0, "right": 0},
            "asset_id": asset["id"],
        }
    )
    return changed


def _asset_furnishing(design):
    return next(item for item in design["furnishings"] if item.get("asset_id"))


def test_every_room_asset_has_one_fixed_size_placement(design, asset_catalog):
    design = _with_asset_furnishing(design, asset_catalog)
    result = compile_furnishings(design, asset_catalog, compile_design(design, asset_catalog))
    authored = design["furnishings"]
    assert sorted(item["id"] for item in result["placements"]) == sorted(
        item["id"] for item in authored
    )
    assert result["coverage"] == {
        "furnishing_count": len(authored),
        "asset_count": sum(bool(item.get("asset_id")) for item in authored),
        "generated_count": sum(bool(item.get("generated")) for item in authored),
    }
    assets = {item["id"]: item for item in asset_catalog["assets"]}
    placed = [item for item in result["placements"] if item.get("asset_id")]
    assert placed
    for item in placed:
        source = assets[item["asset_id"]]["dimensions"]
        assert item["dimensions"] == [source[1], source[0], source[2]]
        assert item["source_dimensions"] == source
        assert item["transform"][3] == [0, 0, 0, 1]


def test_blender_collision_suffix_keeps_logical_source_material_binding():
    assert strip_copy_suffix("03 · Pale natural oak.003") == strip_copy_suffix(
        "03 · Pale natural oak.002"
    )


def test_room_anchor_shift_moves_asset_without_scaling(design, asset_catalog):
    baseline = compile_furnishings(design, asset_catalog)
    changed = deepcopy(design)
    room = next(room for room in changed["rooms"] if room["id"] == "G-LIV")
    room["anchor"][0] += 0.2
    moved = compile_furnishings(changed, asset_catalog)
    before = next(item for item in baseline["placements"] if item["room_id"] == "G-LIV")
    after = next(item for item in moved["placements"] if item["id"] == before["id"])
    assert before["dimensions"] == after["dimensions"]
    assert after["transform"][1][3] - before["transform"][1][3] == pytest.approx(-0.2)
    assert before["geometry_fingerprint"] != after["geometry_fingerprint"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("room_id", "missing", "unknown room_id"),
        ("rotation", [0, 0, math.inf], "finite"),
        ("dimensions", [9, 9, 9], "differ from catalog"),
    ],
)
def test_rejects_missing_room_nonfinite_rotation_and_resizing(
    design, asset_catalog, field, value, message
):
    changed = _with_asset_furnishing(design, asset_catalog)
    changed["furnishings"] = [_asset_furnishing(changed)]
    changed["furnishings"][0][field] = value
    with pytest.raises(FurnishingError, match=message):
        validate_furnishings(changed, asset_catalog)


def test_generated_cabinetry_requires_explicit_positive_dimensions(design, asset_catalog):
    changed = deepcopy(design)
    changed["furnishings"] = [
        {
            "id": "cabinet",
            "room_id": "G-KIT",
            "anchor": "room",
            "position": [0, 0, 1],
            "rotation": [0, 0, 0],
            "dimensions": [1.2, 0.6, 2.0],
            "clearance_m": {"front": 0.8, "back": 0, "left": 0, "right": 0},
            "generated": {"kind": "cabinetry"},
            "adjustable": True,
        }
    ]
    assert validate_furnishings(changed, asset_catalog)[0]["dimensions"] == [1.2, 0.6, 2.0]
    generated = compile_furnishings(changed, asset_catalog)
    assert len(generated["meshes"]) == 1
    mesh = generated["meshes"][0]
    assert mesh["properties"] == {
        "Component ID": "cabinet",
        "Component kind": "furnishing",
        "Procedural child ID": "cabinet/body",
        "Floor level": "G",
        "room_id": "G-KIT",
        "generated_kind": "cabinetry",
        "adjustable": True,
    }
    assert mesh["properties"]["Component ID"] == mesh["component_id"]
    assert mesh["properties"]["Procedural child ID"] == mesh["id"]
    changed["furnishings"][0]["dimensions"][0] = 0
    with pytest.raises(FurnishingError, match="positive"):
        validate_furnishings(changed, asset_catalog)


@pytest.mark.parametrize(
    ("rotation_z", "expected_xy"),
    [(0.0, (1.0, 0.55)), (math.pi / 2, (0.55, 1.0))],
)
def test_generated_furnishing_uses_house_basis_and_local_rotation(
    design, asset_catalog, rotation_z, expected_xy
):
    changed = deepcopy(design)
    room = next(room for room in changed["rooms"] if room["id"] == "G-KIT")
    changed["furnishings"] = [
        {
            "id": "generated-cabinet",
            "room_id": room["id"],
            "anchor": "room",
            "position": [0.2, 0.3, 1.225],
            "rotation": [0, 0, rotation_z],
            "dimensions": [0.55, 1.0, 2.45],
            "clearance_m": {"front": 0, "back": 0, "left": 0, "right": 0},
            "generated": {"kind": "cabinetry"},
        }
    ]

    result = compile_furnishings(changed, asset_catalog)
    mesh = result["meshes"][0]
    transform = mesh["transform"]
    world_vertices = [
        [
            sum(float(transform[row][column]) * float((*vertex, 1)[column]) for column in range(4))
            for row in range(3)
        ]
        for vertex in mesh["vertices"]
    ]
    extents = tuple(
        max(vertex[axis] for vertex in world_vertices)
        - min(vertex[axis] for vertex in world_vertices)
        for axis in (0, 1)
    )

    assert extents == pytest.approx(expected_xy)
    assert result["placements"][0]["transform"] == transform


def test_captured_asset_keeps_world_oriented_source_frame(design, asset_catalog):
    changed = _with_asset_furnishing(design, asset_catalog)
    source = _asset_furnishing(changed)
    source["rotation"] = [0, 0, 0]
    changed["furnishings"] = [source]

    transform = compile_furnishings(changed, asset_catalog)["placements"][0]["transform"]
    for actual, expected in zip(transform[:3], [[1, 0, 0], [0, 1, 0], [0, 0, 1]], strict=True):
        assert actual[:3] == pytest.approx(expected)


def test_one_library_asset_can_compile_in_two_rooms(design, asset_catalog):
    changed = _with_asset_furnishing(design, asset_catalog)
    source = _asset_furnishing(changed)
    copy = deepcopy(source)
    copy["id"] += "-second-instance"
    copy["room_id"] = "U-CHILD"
    copy["position"] = [0.5, 0.5, 0.0]
    changed["furnishings"] = [source, copy]
    placements = compile_furnishings(changed, asset_catalog)["placements"]
    assert [item["asset_id"] for item in placements] == [source["asset_id"], source["asset_id"]]
    assert placements[0]["transform"] != placements[1]["transform"]
    assert placements[0]["dimensions"] == placements[1]["dimensions"]
    assert {item["room_id"] for item in placements} == {"G-LIV", "U-CHILD"}


def test_append_objects_keys_prototypes_by_source_name():
    from contextlib import contextmanager
    from types import SimpleNamespace

    from engine.blender_datablocks import append_objects

    @contextmanager
    def load(path, link):
        loaded = SimpleNamespace(objects=[])
        yield SimpleNamespace(objects=["a", "b"]), loaded
        # Blender swaps the assigned names for loaded IDs in the same list object.
        loaded.objects[:] = [SimpleNamespace(name=f"{name}.001") for name in loaded.objects]

    bpy = SimpleNamespace(data=SimpleNamespace(libraries=SimpleNamespace(load=load)))
    prototypes = append_objects(bpy, "library.blend", ["a", "b"], FurnishingError)
    assert {key: obj.name for key, obj in prototypes.items()} == {"a": "a.001", "b": "b.001"}
