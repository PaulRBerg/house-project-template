import math
import random
from collections import Counter
from copy import deepcopy

import pytest
from shapely.geometry import Point, Polygon

from engine.furnishings import (
    KIT,
    FurnishingError,
    compile_furnishings,
    generate_kit,
    kit_light_matrix,
)
from engine.kit_geometry import rectangular_bowl
from engine.kit_parts import WARM_WHITE_K
from engine.plant_kit import _SPECIES
from engine.transforms import multiply, rotation_xyz, translation

ENVELOPES = {
    "joinery": (
        (1.8, 0.6, 2.4),
        {
            "columns": [
                {
                    "cells": [
                        {"type": "drawer"},
                        {"type": "open", "led": True, "shelves": 1},
                        {"type": "door"},
                    ]
                },
                {"cells": [{"type": "oven"}]},
            ],
            "handle": "bar",
        },
    ),
    "worktop": (
        (2.0, 0.65, 0.04),
        {"sinks": [{"x": 0.3}], "taps": [{"x": 0.3}], "hobs": [{"x": -0.5}]},
    ),
    "shelving": ((1.2, 0.34, 2.0), {"shelves": 5, "books": 0.7, "led": True}),
    "sofa": (
        (3.0, 1.6, 0.8),
        {"chaise": "left", "main_depth": 1.0, "pillows": [{"x": 0.5}], "throw": {"side": "right"}},
    ),
    "lounge_chair": ((0.85, 0.9, 1.05), {"throw": {}, "pillows": [{}]}),
    "ottoman": ((0.55, 0.45, 0.42), {"leg_height": 0.08}),
    "chair": ((0.44, 0.44, 0.88), {"seat_height": 0.65}),
    "bench": ((1.4, 0.4, 0.45), {"cushion": True}),
    "table": ((1.2, 0.7, 0.36), {"shape": "oval", "base": "block"}),
    "bed": (
        (2.0, 2.24, 1.1),
        {"headboard": "channels", "frame": "floating", "cushions": [{"x": 0.1}]},
    ),
    "rug": ((2.0, 1.4, 0.014), {"border": 0.05}),
    "curtain": (
        (3.0, 0.2, 2.8),
        {"layers": [{"role": "sheer", "panels": [[-1.5, -1.0]]}, {"role": "dimout"}]},
    ),
    "panel": ((2.0, 0.05, 2.8), {"style": "slats"}),
    "pendant": ((0.45, 0.45, 1.2), {"shape": "dome"}),
    "floor_lamp": ((0.3, 0.8, 1.55), {"style": "reading"}),
    "table_lamp": ((0.36, 0.36, 0.56), {}),
    "sconce": ((0.18, 0.4, 0.5), {"style": "arm"}),
    "led_line": ((2.0, 0.04, 0.02), {"concealed": True}),
    "downlight": ((0.08, 0.08, 0.02), {"tilt": 20}),
    "mirror": ((0.8, 0.03, 0.9), {"corner_radius": 0.12, "halo": True, "frame": True}),
    "basin": ((0.42, 0.5, 0.3), {}),
    "towel_rail": ((0.5, 0.06, 1.2), {}),
    "towel_stack": ((0.3, 0.28, 0.2), {}),
    "glass_screen": ((1.0, 0.3, 2.0), {}),
    "shower_set": ((0.3, 0.42, 2.3), {}),
    "artwork": ((1.0, 0.04, 1.2), {"motif": "arches"}),
    "vessel": ((0.16, 0.16, 0.6), {"stems": 5}),
    "books": ((0.3, 0.24, 0.16), {"bowl": True}),
    "tray": ((0.4, 0.3, 0.03), {}),
    "plant": ((0.6, 0.6, 1.7), {"species": "olive"}),
    "cabinetry": ((1.0, 0.5, 0.8), {}),
    "soft_box": ((0.4, 0.14, 0.4), {"bulge": 0.03}),
}


# Style variants of a template, checked against the same envelope contract.
STYLE_CASES = {
    "joinery:fluted": (
        "joinery",
        (0.9, 0.5, 0.34),
        {"fluted": True, "plinth": 0.0, "columns": [{"cells": [{"type": "drawer"}]}]},
    ),
    "panel:flutes": ("panel", (2.0, 0.021, 2.8), {"style": "flutes", "backing_role": "panel"}),
    "chair:shell": ("chair", (0.5, 0.52, 0.8), {"style": "shell"}),
    "chair:shell-stool": (
        "chair",
        (0.46, 0.46, 0.9),
        {"style": "shell", "seat_height": 0.65, "arm_height": 0.12},
    ),
    "bench:slats": ("bench", (0.42, 0.3, 0.45), {"style": "slats"}),
    "floor_lamp:lantern": ("floor_lamp", (0.42, 0.42, 1.6), {"style": "lantern"}),
    "sofa:layered-pillows": (
        "sofa",
        (3.0, 1.08, 0.8),
        {"pillows": [{"x": 1.0, "size": 0.46}, {"x": 1.1, "size": 0.4, "forward": 0.08}]},
    ),
}
CASES = {
    **{kind: (kind, *case) for kind, case in ENVELOPES.items()},
    **STYLE_CASES,
}


def _kit(case: str):
    kind, size, params = CASES[case]
    return KIT[kind](size, params, random.Random(3))


def _bounds(mesh, axis):
    values = [vertex[axis] for vertex in mesh["vertices"]]
    return min(values), max(values)


def _face_normal(a, b, c):
    ab, ac = ([v - u for u, v in zip(a, end, strict=True)] for end in (b, c))
    return (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )


def _vertical_hits(mesh, x, y):
    """Intersect a vertical sightline with face interiors, retaining winding."""
    hits = []
    for face in mesh["faces"]:
        points = [mesh["vertices"][index] for index in face]
        if not Polygon([(v[0], v[1]) for v in points]).contains(Point(x, y)):
            continue
        a, b, c = points[:3]
        normal = _face_normal(a, b, c)
        if abs(normal[2]) > 1e-12:
            z = a[2] - (normal[0] * (x - a[0]) + normal[1] * (y - a[1])) / normal[2]
            hits.append((z, normal[2]))
    return sorted(hits)


@pytest.mark.parametrize("radius", [0, 0.03])
def test_rectangular_bowl_is_a_closed_shell_with_open_mouth_and_inward_walls(radius):
    mesh = rectangular_bowl((0.5, 0.4, 0.2), radius=radius)
    for axis, half in enumerate((0.25, 0.2, 0.1)):
        assert _bounds(mesh, axis) == pytest.approx((-half, half))
    edges = Counter(
        (a, b) for face in mesh["faces"] for a, b in zip(face, face[1:] + face[:1], strict=True)
    )
    assert all(count == 1 and edges[b, a] == 1 for (a, b), count in edges.items())
    [underside, floor] = _vertical_hits(mesh, 0.001, 0.002)
    assert underside[0] == pytest.approx(-0.1) and underside[1] < 0
    assert floor[0] == pytest.approx(-0.092) and floor[1] > 0
    # The sloping inner wall faces the opening, and is below the open rim.
    [_, inner_wall] = _vertical_hits(mesh, 0.23, 0.002)
    assert floor[0] < inner_wall[0] < 0.1 and inner_wall[1] > 0
    for cap, normal in ((mesh["faces"][0], [0, 0, -1]), (mesh["faces"][-1], [0, 0, 1])):
        assert all(mesh["normals"][index] == normal for index in cap)
    for face in mesh["faces"]:
        normal = _face_normal(*(mesh["vertices"][index] for index in face[:3]))
        assert sum(value * value for value in normal) > 0
        assert all(
            sum(n * v for n, v in zip(normal, mesh["normals"][index], strict=True)) > 0
            for index in face
        )


def test_worktop_openings_expose_both_bowl_floors_without_stone_caps():
    sinks = [{"x": -0.3, "y": -0.1}, {"x": 0.3, "y": 0.05, "width": 0.4, "depth": 0.35}]
    parts, _ = KIT["worktop"]((2.0, 0.8, 0.04), {"sinks": sinks}, random.Random(3))
    by_name = {part["name"]: part for part in parts}
    assert by_name["top"]["role"] == "stone" and by_name["basin"]["role"] == "basin"
    for sink in sinks:
        x, y = sink["x"] + 0.001, sink["y"] + 0.002
        assert _vertical_hits(by_name["top"]["mesh"], x, y) == []
        [underside, floor] = _vertical_hits(by_name["basin"]["mesh"], x, y)
        assert underside[0] == pytest.approx(-0.18)
        assert floor[0] == pytest.approx(-0.172) and floor[1] > 0
    assert max(z for z, _ in _vertical_hits(by_name["top"]["mesh"], 0.8, 0.11)) == pytest.approx(
        0.02
    )
    assert _bounds(by_name["basin"]["mesh"], 2) == pytest.approx((-0.18, 0.0215))


def test_rectangular_fixture_basin_exposes_its_floor_inside_existing_envelope():
    parts, _ = KIT["basin"]((0.5, 0.5, 0.3), {"shape": "rectangular"}, random.Random(3))
    bowl = next(part for part in parts if part["name"] == "basin")
    assert bowl["role"] == "ceramic"
    assert _bounds(bowl["mesh"], 0) == pytest.approx((-0.25, 0.25))
    assert _bounds(bowl["mesh"], 1) == pytest.approx((-0.24, 0.14))
    assert _bounds(bowl["mesh"], 2) == pytest.approx((-0.15, -0.02))
    [underside, floor] = _vertical_hits(bowl["mesh"], 0.001, -0.048)
    assert underside[0] == pytest.approx(-0.15)
    assert floor[0] == pytest.approx(-0.142) and floor[1] > 0


def test_every_kit_template_has_an_envelope_case():
    assert set(ENVELOPES) == set(KIT)


@pytest.mark.parametrize("case", sorted(CASES))
def test_template_parts_stay_inside_the_fixed_envelope(case):
    kind, size, params = CASES[case]
    parts, lights = KIT[kind](size, params, random.Random(3))
    assert parts
    slack = 0.08 if kind in {"plant", "curtain", "vessel", "lounge_chair", "sofa", "bed"} else 0.03
    for part in parts:
        mesh = part["mesh"]
        assert mesh["faces"] and all(len(face) >= 3 for face in mesh["faces"])
        for axis in (0, 1) if kind == "worktop" else range(3):
            values = [vertex[axis] for vertex in mesh["vertices"]]
            assert min(values) >= -size[axis] / 2 - slack, (case, part["name"], axis)
            assert max(values) <= size[axis] / 2 + slack, (case, part["name"], axis)
        if "normals" in mesh:
            assert len(mesh["normals"]) == len(mesh["vertices"])
    for light in lights:
        assert light["type"] in {"POINT", "SPOT", "AREA"}
        assert light["energy"] > 0 and 1000 <= light["temperature"] <= 6500


@pytest.mark.parametrize("species", sorted(_SPECIES))
def test_every_plant_species_keeps_its_foliage_inside_the_envelope(species):
    size = (0.7, 0.7, 1.3)
    parts, _ = KIT["plant"](size, {"species": species}, random.Random(5))
    for part in parts:
        for axis in (0, 1):
            values = [vertex[axis] for vertex in part["mesh"]["vertices"]]
            assert max(abs(value) for value in values) <= size[axis] / 2 + 0.08, (
                species,
                part["name"],
            )


def test_fixture_lights_keep_a_proper_rotation_under_the_mirrored_house_transform(design):
    item_transform = multiply(
        design["transform"], multiply(translation(2, 3, 2.9), rotation_xyz(0, 0, math.pi / 2))
    )
    matrix = kit_light_matrix(
        {"position": [0.1, 0.0, -0.01], "rotation": [0.3, 0.0, 0.0], "energy": 5}, item_transform
    )["matrix"]
    x, y, z = ([matrix[row][column] for row in range(3)] for column in range(3))
    determinant = (
        x[0] * (y[1] * z[2] - y[2] * z[1])
        - x[1] * (y[0] * z[2] - y[2] * z[0])
        + x[2] * (y[0] * z[1] - y[1] * z[0])
    )
    assert determinant == pytest.approx(1.0, abs=1e-5)


def test_design_kit_parts_bind_existing_materials_and_presentation_flags(design, asset_catalog):
    result = compile_furnishings(design, asset_catalog)
    material_ids = {item["id"] for item in design["materials"]}
    generated = list(result["meshes"])
    assert generated
    assert {mesh["material_binding"]["material_id"] for mesh in generated} <= material_ids | {None}
    hidden = {item["id"] for item in design["furnishings"] if item.get("cutaway_hidden")}
    for mesh in generated:
        assert mesh["properties"].get("Cutaway hidden", False) == (mesh["component_id"] in hidden)
    linear = {
        item["id"]
        for item in design["furnishings"]
        if item.get("generated", {}).get("params", {}).get("shape") == "linear"
    }
    shades = [
        mesh
        for mesh in generated
        if mesh["properties"]["generated_kind"] == "pendant"
        and "/shade" in mesh["id"]
        and mesh["component_id"] not in linear
    ]
    assert shades and all(mesh["cast_shadow"] is False for mesh in shades)
    lit = [item for item in result["placements"] if item.get("lights")]
    assert lit and all(len(light["matrix"]) == 4 for item in lit for light in item["lights"])


def test_unknown_role_material_is_rejected(design, asset_catalog):
    changed = deepcopy(design)
    item = next(
        item for item in changed["furnishings"] if item.get("generated", {}).get("kind") == "sofa"
    )
    changed["furnishings"] = [item]
    item["generated"]["params"] = {
        **item["generated"].get("params", {}),
        "pillows": [{"x": 0.0, "role": "velvet"}],
    }
    with pytest.raises(FurnishingError, match="no material for kit role 'velvet'"):
        compile_furnishings(changed, asset_catalog)


POCKET_SIZE = (2.0, 0.2, 2.7)
POCKET_DEPTH = 0.12


def _curtain_parts(params):
    parts, lights = KIT["curtain"](POCKET_SIZE, params, random.Random(3))
    return {part["name"]: part for part in parts}, lights


def test_curtain_pocket_recesses_a_lit_track_above_the_ceiling_line():
    w, d, h = POCKET_SIZE
    parts, lights = _curtain_parts(
        {
            "pocket": {"depth_m": POCKET_DEPTH},
            "layers": [{"role": "sheer"}, {"role": "blackout", "panels": [[-0.95, -0.6]]}],
        }
    )
    top = h / 2 + POCKET_DEPTH
    for part in parts.values():
        mesh = part["mesh"]
        assert -w / 2 < _bounds(mesh, 0)[0] and _bounds(mesh, 0)[1] < w / 2, part["name"]
        assert -d / 2 < _bounds(mesh, 1)[0] and _bounds(mesh, 1)[1] < d / 2, part["name"]
        assert _bounds(mesh, 2)[1] <= top + 1e-9, part["name"]
    assert parts["pocket"]["role"] == "pocket"
    assert _bounds(parts["pocket"]["mesh"], 2) == pytest.approx((h / 2, top))
    track_low, track_high = _bounds(parts["track"]["mesh"], 2)
    assert h / 2 < track_low and track_high < top
    for name in ("layer-0", "layer-1"):
        low, high = _bounds(parts[name]["mesh"], 2)
        assert low == pytest.approx(-h / 2) and h / 2 < high < track_low
    assert parts["layer-1"]["role"] == "blackout"
    [led] = lights
    assert led["name"] == "pocket-led" and led["temperature"] == WARM_WHITE_K
    assert h / 2 < led["position"][2] < top


@pytest.mark.parametrize(("roller", "bottom"), [(True, 0.0), ({"bottom_m": 0.8}, 0.8)])
def test_curtain_roller_retracts_into_its_pocket_between_side_channels(roller, bottom):
    w, d, h = POCKET_SIZE
    parts, _ = _curtain_parts(
        {"pocket": {"depth_m": POCKET_DEPTH}, "roller": roller, "layers": [{"role": "sheer"}]}
    )
    assert {name for name in parts if name.startswith("layer-")} == {"layer-0"}
    cassette, channels = parts["roller-cassette"], parts["roller-channels"]
    assert cassette["role"] == "metal" and _bounds(cassette["mesh"], 2)[0] > h / 2
    assert channels["role"] == "trim"
    assert _bounds(channels["mesh"], 0) == pytest.approx((-w / 2, w / 2))
    assert _bounds(channels["mesh"], 2) == pytest.approx((-h / 2 + bottom, h / 2))
    # Two side channels, plus the sill channel between them when the roller stops short.
    assert len(channels["mesh"]["vertices"]) == 8 * (3 if bottom else 2)
    assert _bounds(channels["mesh"], 1)[1] < _bounds(parts["layer-0"]["mesh"], 1)[0]


def test_curtain_roller_needs_a_pocket():
    with pytest.raises(ValueError, match="ceiling pocket"):
        KIT["curtain"](POCKET_SIZE, {"roller": True}, random.Random(3))


def test_curtain_pocket_and_blackout_roles_bind_style_materials():
    parts, _ = generate_kit(
        {
            "id": "curtain",
            "dimensions": list(POCKET_SIZE),
            "generated": {
                "kind": "curtain",
                "params": {
                    "pocket": {"depth_m": POCKET_DEPTH},
                    "roller": {"bottom_m": 0.8},
                    "layers": [{"role": "blackout"}],
                },
            },
        }
    )
    materials = {part["role"]: part["material_id"] for part in parts}
    assert materials["blackout"] == "mat_curtain_taupe"
    assert materials["pocket"] == "mat_plaster_white"
    assert materials["trim"] == "mat_trim_white"


def test_fluted_joinery_reeds_sit_within_the_front_thickness():
    parts, _ = _kit("joinery:fluted")
    by_name = {part["name"]: part for part in parts}
    front_y = -0.25
    assert _bounds(by_name["reeds"]["mesh"], 1)[0] == pytest.approx(front_y)
    assert _bounds(by_name["fronts"]["mesh"], 1)[0] == pytest.approx(front_y + 0.008)
    assert by_name["reeds"]["role"] == by_name["fronts"]["role"] == "front"


def test_fluted_panel_stands_oak_reeds_on_its_backing():
    parts, _ = _kit("panel:flutes")
    by_name = {part["name"]: part for part in parts}
    assert by_name["reeds"]["role"] == "wood" and by_name["backing"]["role"] == "panel"
    assert _bounds(by_name["reeds"]["mesh"], 1) == pytest.approx((-0.0105, 0.0045))
    reeds = len(by_name["reeds"]["mesh"]["faces"]) // 11
    assert reeds == round(2.0 / 0.03)


def test_shell_chair_wraps_an_upholstered_back_and_rings_high_seats():
    parts, _ = _kit("chair:shell")
    roles = {part["name"]: part["role"] for part in parts}
    assert roles == {"frame": "wood", "shell": "upholstery", "seat": "cushion"}
    low = {part["name"]: part for part in parts}["frame"]["mesh"]
    high = {part["name"]: part for part in _kit("chair:shell-stool")[0]}["frame"]["mesh"]
    assert len(high["vertices"]) > len(low["vertices"])


def test_slatted_bench_top_has_open_gaps():
    parts, _ = _kit("bench:slats")
    (top,) = parts
    z_top = max(vertex[2] for vertex in top["mesh"]["vertices"])
    assert z_top == pytest.approx(0.225)
    assert not any(
        abs(vertex[1]) < 0.003 and vertex[2] > z_top - 0.01 for vertex in top["mesh"]["vertices"]
    )


def test_lantern_floor_lamp_glows_inside_a_shadowless_shade():
    parts, lights = _kit("floor_lamp:lantern")
    shade = next(part for part in parts if part["name"] == "shade")
    assert shade["shadow"] is False and shade["role"] == "shade"
    (light,) = lights
    low, high = _bounds(shade["mesh"], 2)
    assert low < light["position"][2] < high


def test_sofa_pillows_layer_forward():
    parts, _ = _kit("sofa:layered-pillows")
    by_name = {part["name"]: part for part in parts}
    back = sum(_bounds(by_name["pillow-0"]["mesh"], 1)) / 2
    front = sum(_bounds(by_name["pillow-1"]["mesh"], 1)) / 2
    assert back - front == pytest.approx(0.08, abs=0.03)
