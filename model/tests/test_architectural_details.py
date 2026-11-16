from __future__ import annotations

from copy import deepcopy

import pytest

from engine.architecture import compile_architecture
from engine.transforms import wall_frame


@pytest.fixture(scope="module")
def result(design):
    return compile_architecture(design)


def test_stair_rejects_inconsistent_risers_and_zone_overflow(design):
    changed = deepcopy(design)
    changed["stairs"][0]["riser_count"] = 17
    with pytest.raises(ValueError, match="even risers"):
        compile_architecture(changed)
    changed = deepcopy(design)
    changed["stairs"][0]["geometry"]["flight_width_m"] = 2
    with pytest.raises(ValueError, match="exceeds its zone"):
        compile_architecture(changed)


def test_stair_landing_is_a_slab_over_usable_storage(design, result):
    landing = next(m for m in result["meshes"] if m["id"] == "stair-main/landing")
    heights = [vertex[2] for vertex in landing["vertices"]]
    rise = design["levels"][1]["elevation_m"] - design["levels"][0]["elevation_m"]
    assert max(heights) == pytest.approx(rise / 2)
    assert min(heights) == pytest.approx(rise / 2 - 0.2)


def test_every_nonopen_opening_has_frames_and_native_fill(design, result):
    ids = {m["id"] for m in result["meshes"]}
    for opening in design["openings"]:
        if opening["kind"] == "open":
            continue
        assert opening["id"] + "/jamb-left" in ids
        assert (opening["id"] + ("/door-leaf" if opening["kind"] == "door" else "/pane-00")) in ids


def _parts(result, opening_id):
    return {
        mesh["id"].rsplit("/", 1)[-1]: mesh
        for mesh in result["meshes"]
        if mesh["component_id"] == opening_id
    }


def _sliding_opening(design):
    return next(item for item in design["openings"] if item.get("operation") == "sliding")


@pytest.mark.parametrize(("direction", "active_index"), [("toward-end", 0), ("toward-start", 1)])
def test_sliding_terrace_opening_has_active_leaf_overlap_and_tracks(
    design, direction, active_index
):
    changed = deepcopy(design)
    opening = _sliding_opening(changed)
    assert opening["kind"] == "terrace" and opening["panel_count"] == 2
    opening["slide_direction"] = direction
    parts = _parts(compile_architecture(changed), opening["id"])

    first = parts["pane-00"]
    second = parts["pane-01"]
    panels = [first, second]
    assert panels[active_index]["properties"]["Sliding leaf role"] == "active"
    assert panels[1 - active_index]["properties"]["Sliding leaf role"] == "fixed"
    assert all(panel["properties"]["Slide direction"] == direction for panel in panels)
    assert "sliding-track-00" in parts
    assert "sliding-track-01" in parts

    # The terrace wall runs along Y: the leaves overlap along it and sit on separate tracks.
    def along(mesh):
        return [vertex[1] for vertex in mesh["vertices"]]

    def across(mesh):
        return sum(vertex[0] for vertex in mesh["vertices"]) / len(mesh["vertices"])

    assert (
        min(max(along(first)), max(along(second))) - max(min(along(first)), min(along(second))) > 0
    )
    assert across(first) != pytest.approx(across(second))


def test_terrace_opening_without_operation_keeps_generic_glazing(design):
    changed = deepcopy(design)
    opening = _sliding_opening(changed)
    for field in ("operation", "panel_count", "slide_direction"):
        opening.pop(field)
    result = compile_architecture(changed)
    parts = _parts(result, opening["id"])
    assert not any("Opening operation" in mesh["properties"] for mesh in parts.values())
    assert not any(name.startswith("sliding-track-") for name in parts)


def test_blind_exclusion_is_explicit_in_design(design, result):
    generated = {m["component_id"] for m in result["meshes"] if m["kind"] == "blind"}
    expected = {o["id"] for o in design["openings"] if o.get("blind")}
    assert generated == expected


def test_concealed_blinds_hide_their_cassette_and_visible_ones_draw_it(design, result):
    blinds = [opening for opening in design["openings"] if opening.get("blind")]
    concealed = [opening for opening in blinds if opening.get("blind_concealed")]
    assert concealed
    for opening in concealed:
        parts = _parts(result, opening["id"])
        assert "blind-cassette" not in parts
        assert "blind-slat-00" in parts
    changed = deepcopy(design)
    for opening in changed["openings"]:
        opening.pop("blind_concealed", None)
    exposed = compile_architecture(changed)
    for opening in concealed:
        assert "blind-cassette" in _parts(exposed, opening["id"])


def test_pv_overflow_fails_instead_of_silently_omitting_modules(design):
    changed = deepcopy(design)
    changed["roofs"][0]["pv"]["columns"] = 99
    with pytest.raises(ValueError, match="outside roof"):
        compile_architecture(changed)


def test_entry_leaf_and_pull_share_reversible_exterior_pose(design, result):
    entry = next(item for item in design["openings"] if item.get("door_style") == "flush-entry")
    parts = _parts(result, entry["id"])
    for name in ("door-leaf", "handle"):
        assert parts[name]["properties"]["Exterior closed pose"] is True
        assert parts[name]["properties"]["Swing degrees"] == 90
    assert (
        parts["handle"]["properties"]["Door hinge local"]
        == parts["door-leaf"]["properties"]["Door hinge local"]
    )
    assert max(v[2] for v in parts["handle"]["vertices"]) - min(
        v[2] for v in parts["handle"]["vertices"]
    ) == pytest.approx(1.1)
    assert "Exterior closed pose" not in parts["jamb-left"]["properties"]


def test_filomuro_doors_hide_the_frame_behind_a_flush_shadow_reveal(design, result):
    walls = {wall["id"]: wall for wall in design["walls"]}
    concealed = [item for item in design["openings"] if item.get("door_style") == "flush-concealed"]
    assert concealed
    for opening in concealed:
        parts = _parts(result, opening["id"])
        assert "threshold" not in parts
        thickness = walls[opening["wall_id"]]["thickness"]
        for name in ("jamb-left", "jamb-right", "head"):
            assert parts[name]["material_binding"]["material_id"] == "mat_shadow_gap"
            xs = [vertex[0] for vertex in parts[name]["vertices"]]
            ys = [vertex[1] for vertex in parts[name]["vertices"]]
            assert min(max(xs) - min(xs), max(ys) - min(ys)) <= thickness + 1e-6
        assert parts["door-leaf"]["material_binding"]["material_id"] == opening.get(
            "door_finish", "mat_plaster_white"
        )


def _hinged_door(design):
    """A concealed hinged door in a partition running +X, hinged at its start jamb."""
    walls = {wall["id"]: wall for wall in design["walls"]}
    return next(
        item
        for item in design["openings"]
        if item.get("door_style") == "flush-concealed"
        and item.get("hinge") == "start"
        and item.get("swing_deg") == 90
        and walls[item["wall_id"]]["start"][1] == walls[item["wall_id"]]["end"][1]
        and walls[item["wall_id"]]["start"][0] < walls[item["wall_id"]]["end"][0]
    )


def test_end_hinge_swings_to_the_same_side_and_rests_by_the_near_wall(design, result):
    # The wall runs +X at Y y0: a +90 swing opens toward +Y with either hinge.
    opening = _hinged_door(design)
    wall = next(item for item in design["walls"] if item["id"] == opening["wall_id"])
    (x0, y0), width = wall["start"], opening["width"]
    start_leaf = _parts(result, opening["id"])["door-leaf"]["vertices"]
    changed = deepcopy(design)
    _hinged_door(changed)["hinge"] = "end"
    parts = _parts(compile_architecture(changed), opening["id"])
    leaf = parts["door-leaf"]["vertices"]
    hi = x0 + opening["offset"] + width
    for vertices in (start_leaf, leaf):
        assert min(v[1] for v in vertices) >= y0 - 0.03
        assert max(v[1] for v in vertices) > y0 + width - 0.2
    assert all(abs(v[0] - hi) < 0.08 for v in leaf)
    assert all(abs(v[0] - (hi - width)) < 0.08 for v in start_leaf)
    assert parts["door-leaf"]["properties"]["Door hinge"] == "end"
    handle_x = [v[0] for v in parts["handle"]["vertices"]]
    assert all(abs(x - hi) < 0.08 for x in handle_x)


def test_pocket_door_parks_inside_its_partition(design, result):
    opening = next(
        item for item in design["openings"] if item.get("door_style") == "sliding-pocket"
    )
    assert opening["slide_direction"] == "toward-start" and "swing_deg" not in opening
    wall = next(item for item in design["walls"] if item["id"] == opening["wall_id"])
    # The partition runs +Y, so the leaf slides along Y into the wall toward its start.
    assert wall["start"][0] == wall["end"][0] and wall["start"][1] < wall["end"][1]
    parts = _parts(result, opening["id"])
    assert "handle" not in parts and "threshold" not in parts
    leaf = parts["door-leaf"]
    assert leaf["properties"]["Door operation"] == "sliding-pocket"
    xs = [v[0] for v in leaf["vertices"]]
    ys = [v[1] for v in leaf["vertices"]]
    start = wall["start"][1] + opening["offset"]
    assert max(ys) < start + 0.1 and min(ys) > start - opening["width"]
    assert max(xs) - min(xs) == pytest.approx(0.04)
    assert min(xs) > wall["start"][0] - wall["thickness"] / 2


def test_standard_doors_show_a_white_frame_without_threshold(design):
    changed = deepcopy(design)
    doors = [item for item in changed["openings"] if item.get("door_style") == "flush-concealed"]
    for opening in doors[:2]:
        opening["door_style"] = "standard"
    result = compile_architecture(changed)
    for opening in doors[:2]:
        parts = _parts(result, opening["id"])
        assert "threshold" not in parts
        for name in ("jamb-left", "jamb-right", "head", "door-leaf"):
            assert parts[name]["material_binding"]["material_id"] == "mat_trim_white"


def test_membrane_roofs_keep_the_recorded_fall_and_insulation_reserve(design):
    roofs = [roof for roof in design["roofs"] if roof["material_id"] == "mat_roof_membrane"]
    assert roofs
    for roof in roofs:
        assert roof["pitch_deg"] >= 1
        assert roof["base_z_m"] - roof["deck_z_m"] >= 0.20 - 1e-9


def test_exterior_walls_get_skirting_only_on_the_interior_face(design, result):
    ids = {m["id"] for m in result["meshes"]}
    for wall in design["walls"]:
        if wall["role"] != "exterior":
            continue
        inside, outside = -wall["exterior_side"], wall["exterior_side"]
        assert f"{wall['id']}/skirting-000-{inside}" in ids
        assert f"{wall['id']}/skirting-000-{outside}" not in ids


# The hall and office share a +X partition at Y 4.4 holding the office door; the hall also
# owns the +X partition at Y 2.5, which receives a spanned accent clear of its openings.
WAINSCOT_ROOM, SIDE_ROOM = "G-HALL", "G-OFF"
SHARED_WALL, SHARED_DOOR = "wall-g-hall-north", "door-g-off"
ACCENT_WALL, ACCENT_SPAN = "wall-g-hall-south", (3.0, 4.2)


def _wall(design, wall_id):
    return next(item for item in design["walls"] if item["id"] == wall_id)


@pytest.fixture(scope="module")
def unfinished(design):
    changed = deepcopy(design)
    for room in changed["rooms"]:
        room.pop("wall_finish", None)
    return changed


@pytest.fixture(scope="module")
def finished(unfinished):
    changed = deepcopy(unfinished)
    rooms = {room["id"]: room for room in changed["rooms"]}
    rooms[SIDE_ROOM]["wall_finish"] = {
        "material_id": "mat_sage",
        "accents": [{"wall_id": SHARED_WALL, "material_id": "mat_green"}],
    }
    rooms[WAINSCOT_ROOM]["wall_finish"] = {
        "material_id": "mat_plaster_white",
        "wainscot": {"material_id": "mat_oak", "height_m": 0.9},
        "accents": [
            {
                "wall_id": ACCENT_WALL,
                "material_id": "mat_accent",
                "span_m": list(ACCENT_SPAN),
            }
        ],
    }
    return compile_architecture(changed)


def _finishes(result, room_id, wall_id=None):
    return [
        mesh
        for mesh in result["meshes"]
        if mesh["kind"] == "wall_finish"
        and mesh["component_id"] == room_id
        and wall_id in (None, mesh["properties"]["Wall ID"])
    ]


def _span(mesh, axis):
    values = [vertex[axis] for vertex in mesh["vertices"]]
    return min(values), max(values)


def test_rooms_without_wall_finish_produce_no_skins(unfinished, finished):
    bare = compile_architecture(unfinished)
    assert not any(mesh["kind"] == "wall_finish" for mesh in bare["meshes"])
    assert {m["component_id"] for m in finished["meshes"] if m["kind"] == "wall_finish"} == {
        WAINSCOT_ROOM,
        SIDE_ROOM,
    }


def test_adjoining_rooms_finish_their_own_faces_of_a_partition(design, finished):
    # The shared wall runs +X: the hall lies on its right (-Y), the office on its left (+Y).
    wall = _wall(design, SHARED_WALL)
    y, half = wall["start"][1], wall["thickness"] / 2
    hall = _finishes(finished, WAINSCOT_ROOM, SHARED_WALL)
    office = _finishes(finished, SIDE_ROOM, SHARED_WALL)
    assert hall and office
    for mesh in hall:
        assert _span(mesh, 1) == pytest.approx((y - half - 0.002, y - half))
        assert mesh["properties"]["Wall face side"] == -1
    for mesh in office:
        assert _span(mesh, 1) == pytest.approx((y + half, y + half + 0.002))
        assert mesh["material_binding"]["material_id"] == "mat_green"
        assert mesh["properties"]["Wall finish role"] == "accent"
    assert {m["material_binding"]["material_id"] for m in hall} == {"mat_oak", "mat_plaster_white"}


def test_wall_finish_skins_leave_openings_open_and_span_floor_to_wall_top(design, finished):
    opening = next(item for item in design["openings"] if item["id"] == SHARED_DOOR)
    x0 = _wall(design, SHARED_WALL)["start"][0]
    lo, hi = x0 + opening["offset"], x0 + opening["offset"] + opening["width"]
    level = next(level for level in design["levels"] if level["id"] == "G")
    skins = _finishes(finished, WAINSCOT_ROOM, SHARED_WALL)
    for mesh in skins:
        a, b = _span(mesh, 0)
        if a < hi - 1e-6 and b > lo + 1e-6:
            assert _span(mesh, 2)[0] >= opening["head"] - 1e-6
    assert min(_span(m, 2)[0] for m in skins) == pytest.approx(level["floor_top_offset_m"])
    assert max(_span(m, 2)[1] for m in skins) == pytest.approx(level["clear_height_m"])
    assert any(_span(m, 0) == pytest.approx((lo, hi)) for m in skins)


def test_wall_finish_splits_at_cutaway_and_wainscot_heights(design, finished):
    skins = _finishes(finished, WAINSCOT_ROOM, SHARED_WALL)
    for mesh in skins:
        bottom, top = _span(mesh, 2)
        band = "low" if top <= 1.05 + 1e-6 else "high"
        assert mesh["id"].endswith(f"-{band}")
        assert mesh["collection"] == f"G | Wall finishes {band}"
        if band == "high":
            assert bottom >= 1.05 - 1e-6
        material = mesh["material_binding"]["material_id"]
        assert material == ("mat_oak" if top <= 0.9 + 1e-6 else "mat_plaster_white")
    tops = {round(_span(mesh, 2)[1], 3) for mesh in skins}
    assert {
        0.9,
        1.05,
        next(level for level in design["levels"] if level["id"] == "G")["clear_height_m"],
    } <= tops


def test_accent_span_overrides_base_and_wainscot_on_its_wall_face(design, finished):
    # The accent wall runs +X; the hall lies on its left (+Y).
    wall = _wall(design, ACCENT_WALL)
    (x0, y), half = wall["start"], wall["thickness"] / 2
    lo, hi = x0 + ACCENT_SPAN[0], x0 + ACCENT_SPAN[1]
    skins = _finishes(finished, WAINSCOT_ROOM, ACCENT_WALL)
    assert skins
    for mesh in skins:
        (a, b), (y0, y1) = _span(mesh, 0), _span(mesh, 1)
        assert (y0, y1) == pytest.approx((y + half, y + half + 0.002))
        inside = lo - 1e-6 <= a and b <= hi + 1e-6
        role = mesh["properties"]["Wall finish role"]
        assert (role == "accent") == inside
        if inside:
            assert mesh["material_binding"]["material_id"] == "mat_accent"
    assert any(mesh["properties"]["Wall finish role"] == "accent" for mesh in skins)
    assert any(_span(mesh, 2)[1] <= 0.9 + 1e-6 for mesh in skins if _span(mesh, 0)[0] >= hi - 1e-6)


def test_accent_on_a_wall_that_does_not_bound_the_room_fails(design):
    changed = deepcopy(design)
    room = next(item for item in changed["rooms"] if item["id"] == WAINSCOT_ROOM)
    room["wall_finish"] = {
        "material_id": "mat_sage",
        "accents": [{"wall_id": "wall-g-liv-kitchen", "material_id": "mat_green"}],
    }
    with pytest.raises(ValueError, match="does not bound"):
        compile_architecture(changed)


FLANK = "wall-g-east"
GYM_WINDOW = "window-g-liv-east"
STONES = ["mat_exterior_travertine", "mat_exterior_plinth", "mat_stone_grey"]


@pytest.fixture(scope="module")
def clad(design):
    """One facade in ledgestone with bands, a clipped panel and one revealed window.

    The window is the wall's only opening, set at 1.72-3.12 m along the wall with a visible
    blind cassette, so the expected cell edges below stay fixed while the design evolves.
    """
    changed = deepcopy(design)
    wall = next(item for item in changed["walls"] if item["id"] == FLANK)
    wall["finish"] = {
        "style": "ledgestone",
        "material_id": "mat_metal_dark",
        "extend_top_m": 0.3,
        "stone": {
            "material_ids": STONES,
            "course_heights_m": [0.06, 0.09, 0.12],
            "length_range_m": [0.3, 0.8],
        },
        "bands": [
            {"z_m": [-0.3, 0.25], "material_id": "mat_metal_dark"},
            {"z_m": [1.2, 1.5], "material_id": "mat_metal_dark", "span_m": [0, 4]},
        ],
        "panels": [
            {
                "span_m": [4.0, 5.0],
                "z_span_m": [0.5, 2.0],
                "depth_m": 0.004,
                "material_id": "mat_dark_wood",
            }
        ],
    }
    changed["openings"] = [
        item for item in changed["openings"] if item["wall_id"] != FLANK or item["id"] == GYM_WINDOW
    ]
    opening = next(item for item in changed["openings"] if item["id"] == GYM_WINDOW)
    opening.update(offset=1.72, width=1.4, blind=True)
    opening.pop("blind_concealed", None)
    opening["reveal"] = {
        "lining_material_id": "mat_dark_wood",
        "depth_m": 0.2,
        "surround_m": 0.15,
        "surround_material_id": "mat_dark_wood",
        "pitch_m": 0.05,
        "width_m": 0.03,
    }
    return changed, compile_architecture(changed)


def _local(wall, vertex):
    """Along-wall u, outward distance from the exterior face and height of a vertex."""
    (x, y), (dx, dy) = wall["start"], wall_frame(wall)[1]
    px, py = vertex[0] - x, vertex[1] - y
    outward = wall["exterior_side"] * (px * -dy + py * dx) - wall["thickness"] / 2
    return px * dx + py * dy, outward, vertex[2]


def _rects(wall, mesh):
    """``(u0, u1, z0, z1)`` of every eight-vertex box in a (merged) mesh."""
    rects = []
    for index in range(0, len(mesh["vertices"]), 8):
        us, _, zs = zip(
            *(_local(wall, v) for v in mesh["vertices"][index : index + 8]), strict=True
        )
        rects.append((min(us), max(us), min(zs), max(zs)))
    return rects


def _overlap(a, b):
    return min(a[1], b[1]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[2], b[2]) > 1e-6


def _facade(result, slot, wall_id=FLANK):
    return [
        mesh
        for mesh in result["meshes"]
        if mesh["component_id"] == wall_id
        and mesh["kind"] == "facade"
        and mesh["material_binding"]["slot"] == slot
    ]


def test_ledgestone_courses_align_across_the_cells_beside_a_window(clad):
    design, result = clad
    wall = next(item for item in design["walls"] if item["id"] == FLANK)
    stones = [rect for mesh in _facade(result, "stone") for rect in _rects(wall, mesh)]
    assert {m["material_binding"]["material_id"] for m in _facade(result, "stone")} <= set(STONES)
    assert all(m["properties"]["Gross area role"] for m in _facade(result, "stone"))

    opening = next(item for item in design["openings"] if item["id"] == GYM_WINDOW)

    def courses(side):
        return {
            (round(z0, 6), round(z1, 6))
            for u0, u1, z0, z1 in stones
            if opening["sill"] <= z0 and z1 <= opening["head"] and side(u0, u1)
        }

    left = courses(lambda u0, u1: u1 <= 1.72 - 0.15 + 1e-6)
    right = courses(lambda u0, u1: 3.12 + 0.15 - 1e-6 <= u0 and u1 < 4.0 - 1e-6)
    assert len(left) > 5
    assert left == right


def test_facade_skins_stay_within_four_millimetres_of_the_wall_face(design, result, clad):
    for source, compiled in ((design, result), clad):
        walls = {wall["id"]: wall for wall in source["walls"]}
        for mesh in compiled["meshes"]:
            slot = mesh["material_binding"]["slot"]
            if mesh["kind"] != "facade" or slot == "accent":
                continue
            wall = walls[mesh["component_id"]]
            outward = max(_local(wall, vertex)[1] for vertex in mesh["vertices"])
            assert outward <= 0.004 + 1e-9, mesh["id"]


def test_bands_stop_at_openings_and_replace_stone_and_base(clad):
    design, result = clad
    wall = next(item for item in design["walls"] if item["id"] == FLANK)
    opening = next(item for item in design["openings"] if item["id"] == GYM_WINDOW)
    window = (
        opening["offset"],
        opening["offset"] + opening["width"],
        opening["sill"],
        opening["head"],
    )
    bands = {mesh["id"]: _rects(wall, mesh)[0] for mesh in _facade(result, "band")}
    upper = [rect for name, rect in bands.items() if "/band-1-" in name]
    assert not any(_overlap(rect, window) for rect in upper)
    assert sum((r[1] - r[0]) * (r[3] - r[2]) for r in upper) == pytest.approx((4 - 1.4) * 0.3)
    assert min(r[2] for r in bands.values()) == pytest.approx(-0.3)
    covered = [rect for mesh in _facade(result, "stone") for rect in _rects(wall, mesh)]
    covered += [_rects(wall, mesh)[0] for mesh in _facade(result, "facade")]
    assert not any(_overlap(a, b) for a in covered for b in bands.values())


def test_panels_clip_to_their_vertical_span_and_displace_the_stone(clad):
    design, result = clad
    wall = next(item for item in design["walls"] if item["id"] == FLANK)
    panels = [_rects(wall, mesh)[0] for mesh in _facade(result, "accent")]
    assert panels
    assert min(r[2] for r in panels) == pytest.approx(0.5)
    assert max(r[3] for r in panels) == pytest.approx(2.0)
    stones = [rect for mesh in _facade(result, "stone") for rect in _rects(wall, mesh)]
    assert not any(_overlap(stone, (4.0, 5.0, 0.5, 2.0)) for stone in stones)


def test_extend_top_carries_stone_and_base_over_the_slab_edge(clad):
    design, result = clad
    wall = next(item for item in design["walls"] if item["id"] == FLANK)
    base = [_rects(wall, mesh)[0] for mesh in _facade(result, "facade")]
    stones = [rect for mesh in _facade(result, "stone") for rect in _rects(wall, mesh)]
    top = (
        next(level for level in design["levels"] if level["id"] == "G")["clear_height_m"]
        + wall["finish"]["extend_top_m"]
    )
    assert max(r[3] for r in base) == pytest.approx(top)
    assert top - 0.12 < max(r[3] for r in stones) <= top + 1e-9
    # The span above the window head reaches the wall top, so it is raised too.
    assert any(r[0] >= 1.72 - 1e-6 and r[1] <= 3.12 + 1e-6 and r[3] > top - 0.12 for r in stones)


def test_spanned_extend_top_raises_only_its_range_of_the_wall(clad):
    changed = deepcopy(clad[0])
    wall = next(item for item in changed["walls"] if item["id"] == FLANK)
    wall["finish"]["extend_top_m"] = [{"span_m": [5.0, 7.0], "height_m": 0.84}]
    result = compile_architecture(changed)
    base = [_rects(wall, mesh)[0] for mesh in _facade(result, "facade")]
    stones = [rect for mesh in _facade(result, "stone") for rect in _rects(wall, mesh)]
    wall_top = next(level for level in changed["levels"] if level["id"] == "G")["clear_height_m"]
    raised = [r for r in base + stones if r[3] > wall_top + 1e-6]
    assert raised
    assert all(5.0 - 1e-6 <= r[0] and r[1] <= 7.0 + 1e-6 for r in raised)
    assert max(r[3] for r in base) == pytest.approx(wall_top + 0.84)
    assert wall_top + 0.72 < max(r[3] for r in stones) <= wall_top + 0.84 + 1e-9


def test_reveal_moves_the_frame_back_and_lines_the_reveal(clad):
    design, result = clad
    wall = next(item for item in design["walls"] if item["id"] == FLANK)
    parts = _parts(result, GYM_WINDOW)

    def depth(name):
        values = [_local(wall, vertex)[1] for vertex in parts[name]["vertices"]]
        return min(values), max(values)

    # The exterior face is outward 0; the frame plane stands 0.2 m behind it.
    for name in ("jamb-left", "head", "threshold", "pane-00"):
        low, high = depth(name)
        assert (low + high) / 2 == pytest.approx(-0.2)
    assert depth("jamb-left") == pytest.approx((-0.24, -0.16))
    for name in ("reveal-jamb-left", "reveal-jamb-right", "reveal-head"):
        assert depth(name) == pytest.approx((-0.16, 0))
        assert parts[name]["material_binding"]["material_id"] == "mat_dark_wood"
    assert "reveal-sill" not in parts
    assert depth("stone-sill") == pytest.approx((-0.2, 0.06))
    opening = next(item for item in design["openings"] if item["id"] == GYM_WINDOW)
    u0, u1, z0, z1 = _rects(wall, parts["reveal-jamb-left"])[0]
    assert (u0, u1, z0, z1) == pytest.approx((1.72, 1.732, opening["sill"], opening["head"]))
    for name in ("blind-guide-0", "blind-guide-1", "blind-cassette"):
        low, high = depth(name)
        assert -0.16 <= low and high <= 0
        u0, u1, _, top = _rects(wall, parts[name])[0]
        assert 1.732 - 1e-6 <= u0 and u1 <= 3.108 + 1e-6 and top <= opening["head"] - 0.012 + 1e-6
    for mesh in result["meshes"]:
        if mesh["component_id"] == GYM_WINDOW and mesh["kind"] == "blind":
            assert all(-0.16 <= _local(wall, v)[1] <= 0 for v in mesh["vertices"])


def test_surround_rings_the_opening_in_flush_slats(clad):
    design, result = clad
    wall = next(item for item in design["walls"] if item["id"] == FLANK)
    surrounds = _facade(result, "surround")
    assert {mesh["properties"]["Opening ID"] for mesh in surrounds} == {GYM_WINDOW}
    rects = [_rects(wall, mesh)[0] for mesh in surrounds]
    opening = next(item for item in design["openings"] if item["id"] == GYM_WINDOW)
    window = (
        opening["offset"],
        opening["offset"] + opening["width"],
        opening["sill"],
        opening["head"],
    )
    assert not any(_overlap(rect, window) for rect in rects)
    assert all(rect[1] - rect[0] <= 0.03 + 1e-9 for rect in rects)
    assert min(r[0] for r in rects) == pytest.approx(1.57)
    wall_top = next(level for level in design["levels"] if level["id"] == wall["level_id"])[
        "clear_height_m"
    ]
    surround_top = min(opening["head"] + 0.15, wall_top)
    assert (min(r[2] for r in rects), max(r[3] for r in rects)) == pytest.approx(
        (opening["sill"] - 0.15, surround_top)
    )
    stones = [rect for mesh in _facade(result, "stone") for rect in _rects(wall, mesh)]
    assert not any(
        _overlap(stone, (1.57, 3.27, opening["sill"] - 0.15, surround_top)) for stone in stones
    )


def test_reveal_too_shallow_for_its_blind_fails(clad):
    changed = deepcopy(clad[0])
    opening = next(item for item in changed["openings"] if item["id"] == GYM_WINDOW)
    opening["reveal"]["depth_m"] = 0.1
    with pytest.raises(ValueError, match="reveal depth_m below"):
        compile_architecture(changed)
