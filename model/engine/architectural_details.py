"""Parameterized architectural assemblies, compiled to portable mesh descriptors."""

from __future__ import annotations

import math
from itertools import pairwise

from shapely.geometry import Polygon

from .architecture import CUTAWAY_HEIGHT_M, wall_cells
from .facade_finishes import REVEAL_KINDS, exterior_finish
from .geometry import (
    as_polygon,
    merge_intervals,
    rectangle_mesh,
    roof_covering_z,
    subtract_intervals,
    wall_box,
)
from .kit_geometry import rod
from .mesh_descriptors import ELECTRIC_BLINDS, EXTERIOR_DETAILS, ROOF_CAP_SOLAR, level_collection
from .transforms import wall_frame, wall_point

DEFAULT_DOOR_SWING_DEG = 72
# Windows with a sill above this height get an exterior stone sill.
STONE_SILL_MIN_M = 0.15
# A revealed window frame is this deep; its timber lining and blind sit in front of it.
REVEAL_FRAME_DEPTH_M = 0.08
REVEAL_LINING_M = 0.012
# The blind's centre stands this far behind the exterior face, inside a revealed opening.
REVEAL_BLIND_INSET_M = 0.05
# A finished-floor edge belongs to a wall face when it lies this close to it.
FACE_TOLERANCE_M = 0.005


def _box(builder, entity, child, center, size, collection, *, material, kind):
    x, y, z = center
    w, d, h = size
    return builder.add(
        entity,
        child,
        rectangle_mesh(x - w / 2, y - d / 2, x + w / 2, y + d / 2, z - h / 2, z + h / 2),
        collection,
        material=material,
        kind=kind,
        slot=kind,
    )


def _rotate_about_z(mesh, pivot, angle):
    cos, sin = math.cos(angle), math.sin(angle)
    for vertex in mesh["vertices"]:
        x, y = vertex[0] - pivot[0], vertex[1] - pivot[1]
        vertex[:2] = [pivot[0] + x * cos - y * sin, pivot[1] + x * sin + y * cos]


def _dark_finish(entity):
    return "mat_dark_wood" if entity.get("finish") == "timber" else "mat_metal_dark"


def _openings(builder):
    walls = {wall["id"]: wall for wall in builder.design["walls"]}
    for opening in sorted(builder.design["openings"], key=lambda item: item["id"]):
        wall = walls[opening["wall_id"]]
        level = wall["level_id"]
        base = builder.levels[level]["elevation_m"]
        lo, width, sill, head = (opening[k] for k in ("offset", "width", "sill", "head"))
        hi, thickness = lo + width, wall["thickness"]
        collection = level_collection(level, "Openings")
        is_door = opening["kind"] == "door"
        style = opening.get("door_style")
        flush_entry = style == "flush-entry"
        pocket = style == "sliding-pocket"
        standard = style == "standard"
        # Filomuro-type flush and pocket doors: the frame hides in the plaster behind a shadow reveal.
        concealed = style == "flush-concealed" or pocket
        if standard:
            material = "mat_trim_white"
        elif is_door and not (flush_entry or concealed):
            material = "mat_oak"
        else:
            material = "mat_metal_dark"

        def part(
            child,
            a,
            b,
            bottom,
            top,
            depth,
            offset=0,
            mat=material,
            kind="opening",
            *,
            opening=opening,
            wall=wall,
            base=base,
            collection=collection,
            level=level,
            properties=None,
        ):
            semantics = {
                "Floor level": level,
                "Opening ID": opening["id"],
                "Wall ID": wall["id"],
            }
            semantics.update(properties or {})
            return builder.add(
                opening,
                child,
                wall_box(wall, a, b, offset, depth, base + bottom, base + top),
                collection if kind == "opening" else ELECTRIC_BLINDS,
                material=mat,
                kind=kind,
                slot=mat,
                properties=semantics,
            )

        if opening["kind"] == "open":
            continue
        frame = 0.012 if concealed else opening.get("frame_width_m", 0.07)
        if 2 * frame >= width or 2 * frame >= head - sill:
            raise ValueError(f"{opening['id']}: frame consumes opening")
        outward = wall.get("exterior_side", -1)
        # A reveal moves the frame plane from the wall centre to depth_m behind the exterior face.
        reveal = (
            opening.get("reveal")
            if wall["role"] == "exterior" and opening["kind"] in REVEAL_KINDS
            else None
        )
        if reveal:
            minimum = REVEAL_FRAME_DEPTH_M / 2 + (
                2 * REVEAL_BLIND_INSET_M if opening.get("blind") else REVEAL_LINING_M
            )
            if reveal["depth_m"] < minimum:
                raise ValueError(f"{opening['id']}: reveal depth_m below {minimum:g} m")
            plane = outward * (thickness / 2 - reveal["depth_m"])
            frame_depth = REVEAL_FRAME_DEPTH_M
        else:
            plane, frame_depth = 0, thickness + 0.06
        if concealed:
            for side, a in [("left", lo), ("right", hi - frame)]:
                part(f"jamb-{side}", a, a + frame, sill, head, thickness, mat="mat_shadow_gap")
            part("head", lo, hi, head - frame, head, thickness, mat="mat_shadow_gap")
        else:
            for side, a in [("left", lo), ("right", hi - frame)]:
                part(f"jamb-{side}", a, a + frame, sill, head, frame_depth, plane)
            part("head", lo, hi, head - frame, head, frame_depth, plane)
            if not standard:
                part("threshold", lo, hi, sill, sill + frame, frame_depth, plane)
        for index, trim in enumerate(opening.get("surround", [])):
            u = lo + width * trim["fraction"] + trim.get("offset_m", 0)
            w, depth, h = trim["size"]
            descriptor = part(
                f"surround-{index}",
                u - w / 2,
                u + w / 2,
                trim["center_z_m"] - h / 2,
                trim["center_z_m"] + h / 2,
                depth,
                trim["wall_offset_m"],
                _dark_finish(trim),
            )
            descriptor["properties"]["Architectural family"] = "entry surround"
        if is_door and pocket:
            # Parked open inside the partition, leaving a finger-pull edge in the opening.
            inset = frame + 0.002
            shift = (width - 0.06) * (-1 if opening["slide_direction"] == "toward-start" else 1)
            leaf = wall_box(
                wall,
                lo + inset + shift,
                hi - inset + shift,
                0,
                0.04,
                base + sill + 0.008,
                base + head - inset,
            )
            builder.add(
                opening,
                "door-leaf",
                leaf,
                collection,
                material=opening.get("door_finish", "mat_plaster_white"),
                kind="opening",
                slot="door",
                properties={
                    "Floor level": level,
                    "Opening ID": opening["id"],
                    "Door operation": "sliding-pocket",
                    "Slide direction": opening["slide_direction"],
                },
            )
        elif is_door:
            # swing_deg > 0 opens to the left of the wall's start-to-end vector for either hinge.
            hinge_end = opening.get("hinge") == "end"
            swing = opening.get("swing_deg", DEFAULT_DOOR_SWING_DEG)
            angle = math.radians(-swing if hinge_end else swing)
            inset = frame + 0.002 if concealed else 0.05
            leaf = wall_box(
                wall,
                lo + inset,
                hi - inset,
                0,
                0.045,
                base + sill + (0.008 if concealed else 0.04),
                base + head - (frame + 0.002 if concealed else 0.06),
            )
            pivot = wall_point(wall, hi - inset if hinge_end else lo + inset)
            door_properties = {
                "Floor level": level,
                "Opening ID": opening["id"],
                "Swing degrees": swing,
                "Door hinge": "end" if hinge_end else "start",
            }
            if flush_entry:
                door_properties.update(
                    {"Exterior closed pose": True, "Door hinge local": [*pivot, base]}
                )
            _rotate_about_z(leaf, pivot, angle)
            builder.add(
                opening,
                "door-leaf",
                leaf,
                collection,
                material="mat_dark_wood"
                if flush_entry
                else opening.get("door_finish", "mat_plaster_white")
                if concealed
                else "mat_trim_white"
                if standard
                else "mat_oak",
                kind="opening",
                slot="door",
                properties=door_properties,
            )
            # Handle spans are measured back from the latch jamb, opposite the hinge.
            if flush_entry:
                near, far, offset, depth, bottom, top = 0.155, 0.19, -0.075, 0.055, 0.72, 1.82
            elif concealed:
                near, far, offset, depth, bottom, top = 0.08, 0.2, -0.04, 0.035, 1.022, 1.036
            else:
                near, far, offset, depth, bottom, top = 0.16, 0.28, -0.046, 0.045, 1.019, 1.041
            a, b = (lo + near, lo + far) if hinge_end else (hi - far, hi - near)
            handle = wall_box(wall, a, b, offset, depth, base + bottom, base + top)
            _rotate_about_z(handle, pivot, angle)
            builder.add(
                opening,
                "handle",
                handle,
                collection,
                material="mat_metal_dark",
                kind="opening",
                slot="handle",
                properties=door_properties,
            )
        else:
            if opening.get("operation") == "sliding":
                direction = opening["slide_direction"]
                active_panel = 1 if direction == "toward-start" else 0
                split = lo + width / 2
                overlap = min(0.05, width * 0.02)
                track_offsets = (-0.025, 0.025)
                panes = (
                    (lo + 0.0275, split + overlap / 2),
                    (split - overlap / 2, hi - 0.0275),
                )
                for index, (a, b) in enumerate(panes):
                    role = "active" if index == active_panel else "fixed"
                    semantics = {
                        "Opening operation": "sliding",
                        "Sliding panel index": index,
                        "Sliding leaf role": role,
                        "Slide direction": direction,
                    }
                    part(
                        f"pane-{index:02d}",
                        a,
                        b,
                        sill + 0.05,
                        head - 0.05,
                        0.018,
                        plane + track_offsets[index],
                        mat="mat_glass",
                        properties=semantics,
                    )
                    meeting = b if index == 0 else a
                    part(
                        f"mullion-01-{role}",
                        meeting - 0.024,
                        meeting + 0.024,
                        sill,
                        head,
                        0.04,
                        plane + track_offsets[index],
                        properties=semantics,
                    )
                for index, offset in enumerate(track_offsets):
                    part(
                        f"sliding-track-{index:02d}",
                        lo + frame,
                        hi - frame,
                        sill + 0.035,
                        sill + 0.055,
                        0.014,
                        plane + offset,
                        properties={
                            "Opening operation": "sliding",
                            "Sliding track": True,
                            "Sliding track index": index,
                            "Slide direction": direction,
                        },
                    )
                pull_center = split + (-0.03 if active_panel == 0 else 0.03)
                part(
                    "access-pull",
                    pull_center - 0.012,
                    pull_center + 0.012,
                    0.875,
                    1.225,
                    0.035,
                    plane + track_offsets[active_panel] - 0.04,
                    properties={
                        "Opening operation": "sliding",
                        "Sliding panel index": active_panel,
                        "Sliding leaf role": "active",
                        "Slide direction": direction,
                    },
                )
            else:
                count = opening.get(
                    "panel_count",
                    max(2 if opening["kind"] == "double" else 1, round(width / 1.25)),
                )
                for index in range(count):
                    a, b = lo + index * width / count, lo + (index + 1) * width / count
                    part(
                        f"pane-{index:02d}",
                        a + 0.0275,
                        b - 0.0275,
                        sill + 0.05,
                        head - 0.05,
                        0.018,
                        plane,
                        mat="mat_glass",
                    )
                    if index:
                        part(
                            f"mullion-{index:02d}",
                            a - 0.024,
                            a + 0.024,
                            sill,
                            head,
                            min(0.1, frame_depth),
                            plane,
                        )
            stone_sill = sill > STONE_SILL_MIN_M
            if stone_sill:
                # A revealed sill runs from the frame plane out past the exterior face.
                outer = thickness / 2 + 0.06
                inner = thickness / 2 - reveal["depth_m"] if reveal else -outer
                part(
                    "stone-sill",
                    lo - 0.06,
                    hi + 0.06,
                    sill - 0.0525,
                    sill + 0.0025,
                    outer - inner,
                    outward * (outer + inner) / 2,
                    mat="mat_stone_grey",
                )
            if opening["kind"] == "terrace" and opening.get("operation") != "sliding":
                part("access-pull", hi - 0.152, hi - 0.128, 0.875, 1.225, 0.035, plane - 0.07)
            if reveal:
                # Linings cover the four reveal faces from the frame to the exterior face.
                frame_face = thickness / 2 - reveal["depth_m"] + REVEAL_FRAME_DEPTH_M / 2
                lining = (thickness / 2 - frame_face, outward * (thickness / 2 + frame_face) / 2)
                edge = REVEAL_LINING_M
                faces = [
                    ("jamb-left", lo, lo + edge, sill, head),
                    ("jamb-right", hi - edge, hi, sill, head),
                    ("head", lo + edge, hi - edge, head - edge, head),
                ]
                if not stone_sill:
                    faces.append(("sill", lo + edge, hi - edge, sill, sill + edge))
                for name, a, b, bottom, top in faces:
                    part(
                        f"reveal-{name}",
                        a,
                        b,
                        bottom,
                        top,
                        *lining,
                        mat=reveal["lining_material_id"],
                    )
        if opening.get("blind", False):
            # A concealed cassette sits in the insulation above the head and is not drawn.
            concealed = opening.get("blind_concealed", False)
            if reveal:
                # Inside the reveal, clear of its lining and in front of the frame.
                edge = REVEAL_LINING_M
                offset = outward * (thickness / 2 - REVEAL_BLIND_INSET_M)
                cassette = (lo + edge, hi - edge, head - 0.2, head - edge, 2 * REVEAL_BLIND_INSET_M)
                guide_starts = (lo + edge, hi - edge - 0.032)
                guide_bottom, guide_top = sill + edge, head - edge
            else:
                offset = outward * 0.26
                cassette = (lo - 0.05, hi + 0.05, head - 0.2, head, 0.18)
                guide_starts, guide_bottom, guide_top = (lo - 0.001, hi - 0.031), sill, head
            if not concealed:
                part("blind-cassette", *cassette, offset, "mat_metal_dark", "blind")
            for index, a in enumerate(guide_starts):
                part(
                    f"blind-guide-{index}",
                    a,
                    a + 0.032,
                    guide_bottom,
                    guide_top,
                    0.045,
                    offset,
                    "mat_metal_dark",
                    "blind",
                )
            drop = opening.get(
                "blind_drop_m",
                0.28 if head - sill > 2.3 else min(0.75, (head - sill) * 0.45),
            )
            # Venetian slat tilt around the arbitrary wall tangent, not a world axis.
            theta = math.radians(25)
            center = wall_point(wall, (lo + hi) / 2, offset)
            _, tangent, _ = wall_frame(wall)
            for index in range(max(3, round(drop / 0.065))):
                z = head - (0.04 if concealed else 0.24) - index * 0.065
                slat = wall_box(
                    wall,
                    lo + 0.025,
                    hi - 0.025,
                    offset,
                    0.085,
                    base + z - 0.0065,
                    base + z + 0.0065,
                )
                for vertex in slat["vertices"]:
                    normal = (
                        -(vertex[0] - center[0]) * tangent[1] + (vertex[1] - center[1]) * tangent[0]
                    )
                    dz = vertex[2] - (base + z)
                    shift = normal * (math.cos(theta) - 1) - dz * math.sin(theta)
                    vertex[0] -= tangent[1] * shift
                    vertex[1] += tangent[0] * shift
                    vertex[2] = base + z + normal * math.sin(theta) + dz * math.cos(theta)
                builder.add(
                    opening,
                    f"blind-slat-{index:02d}",
                    slat,
                    ELECTRIC_BLINDS,
                    material="mat_metal_dark",
                    kind="blind",
                    slot="blind",
                    properties={"Floor level": level, "Opening ID": opening["id"]},
                )


def _finishes(builder):
    for wall in sorted(builder.design["walls"], key=lambda item: item["id"]):
        level = builder.levels[wall["level_id"]]
        z, height = level["elevation_m"], level["clear_height_m"]
        openings = builder.openings_by_wall.get(wall["id"], [])
        _, (dx, dy), length = wall_frame(wall)
        cuts = [(op["offset"], op["offset"] + op["width"]) for op in openings if op["sill"] <= 0.1]
        sides = (-wall["exterior_side"],) if wall["role"] == "exterior" else (-1, 1)
        for index, (lo, hi) in enumerate(subtract_intervals((0, length), cuts)):
            for side in sides:
                builder.add(
                    wall,
                    f"skirting-{index:03d}-{side}",
                    wall_box(
                        wall,
                        lo,
                        hi,
                        side * (wall["thickness"] / 2 + 0.012),
                        0.018,
                        z + 0.0025,
                        z + 0.0875,
                    ),
                    level_collection(level["id"], "Details"),
                    material="mat_oak",
                    kind="skirting",
                    slot="skirting",
                )
        for index, closure in enumerate(wall.get("closures", [])):
            lo, hi = closure["span_m"]
            mesh = wall_box(
                wall,
                lo,
                hi,
                0,
                wall["thickness"],
                closure["bottom_m"],
                max(closure["top_m"]),
            )
            for vertex in mesh["vertices"]:
                if vertex[2] != closure["bottom_m"]:
                    along = (vertex[0] - wall["start"][0]) * dx + (
                        vertex[1] - wall["start"][1]
                    ) * dy
                    vertex[2] = closure["top_m"][0] + (along - lo) / (hi - lo) * (
                        closure["top_m"][1] - closure["top_m"][0]
                    )
            builder.add(
                wall,
                f"closure-{index}",
                mesh,
                level_collection(level["id"], "Walls high"),
                kind="wall",
            )
            builder.quantities["walls"][wall["id"]]["volume_m3"] += (
                (hi - lo) * wall["thickness"] * (sum(closure["top_m"]) / 2 - closure["bottom_m"])
            )
        if wall["role"] == "exterior":
            exterior_finish(builder, wall, openings, wall.get("height_m", height))


def _room_faces(builder, room):
    """Merged along-wall spans of every wall face bounding the room's finished floor."""
    walls = [
        wall
        for wall in sorted(builder.design["walls"], key=lambda item: item["id"])
        if wall["level_id"] == room["level_id"]
    ]
    spans = {}
    for record in builder.quantities["rooms"][room["id"]]["polygons"]:
        polygon = as_polygon(record)
        for ring in (polygon.exterior, *polygon.interiors):
            for p, q in pairwise(ring.coords):
                for wall in walls:
                    (x, y), (dx, dy), length = wall_frame(wall)
                    u = [(px - x) * dx + (py - y) * dy for px, py in (p, q)]
                    v = [(py - y) * dx - (px - x) * dy for px, py in (p, q)]
                    offset = sum(v) / 2
                    # Walls thinner than twice the floor inset leave the floor edge at the inset line.
                    reach = max(wall["thickness"] / 2, room["floor_inset_m"])
                    if (
                        abs(v[0] - v[1]) > FACE_TOLERANCE_M
                        or not wall["thickness"] / 2 - FACE_TOLERANCE_M
                        <= abs(offset)
                        <= reach + FACE_TOLERANCE_M
                    ):
                        continue
                    lo, hi = max(min(u), 0), min(max(u), length)
                    if hi - lo > 0.01:
                        spans.setdefault((wall["id"], 1 if offset > 0 else -1), []).append((lo, hi))
    by_id = {wall["id"]: wall for wall in walls}
    return [
        (by_id[wall_id], side, lo, hi)
        for (wall_id, side), intervals in sorted(spans.items())
        for lo, hi in merge_intervals(intervals)
    ]


def _room_finishes(builder):
    """Paint, wainscot and accent skins on the wall faces of rooms with a ``wall_finish``."""
    for room in sorted(builder.design["rooms"], key=lambda item: item["id"]):
        finish = room.get("wall_finish")
        if not finish:
            continue
        level = builder.levels[room["level_id"]]
        z, floor_top = level["elevation_m"], level["floor_top_offset_m"]
        wainscot = finish.get("wainscot")
        faces = _room_faces(builder, room)
        counters = {}
        for accent in finish.get("accents", []):
            if not any(wall["id"] == accent["wall_id"] for wall, *_ in faces):
                raise ValueError(f"{room['id']}: accent wall {accent['wall_id']} does not bound it")
        for wall, side, face_lo, face_hi in faces:
            height = wall.get("height_m", level["clear_height_m"])
            cutaway = wall.get("cutaway_height_m", CUTAWAY_HEIGHT_M)
            rows = {cutaway, *([wainscot["height_m"]] if wainscot else [])}
            length = wall_frame(wall)[2]
            accents = [
                (item.get("span_m", (0, length)), item["material_id"])
                for item in finish.get("accents", [])
                if item["wall_id"] == wall["id"]
            ]
            openings = builder.openings_by_wall.get(wall["id"], [])
            for _, _, cell_lo, cell_hi, bottom, top in wall_cells(wall, openings, height):
                lo, hi = max(cell_lo, face_lo), min(cell_hi, face_hi)
                bottom = max(bottom, floor_top)
                if hi - lo <= 1e-6 or top - bottom <= 1e-6:
                    continue
                columns = {lo, hi, *(u for span, _ in accents for u in span)}
                heights = {bottom, top, *rows}
                for a, b in pairwise(sorted(u for u in columns if lo <= u <= hi)):
                    accent = next(
                        (mat for (s0, s1), mat in accents if s0 <= (a + b) / 2 <= s1), None
                    )
                    for low, high in pairwise(sorted(h for h in heights if bottom <= h <= top)):
                        if b - a <= 1e-6 or high - low <= 1e-6:
                            continue
                        if accent:
                            role, material = "accent", accent
                        elif wainscot and high <= wainscot["height_m"] + 1e-9:
                            role, material = "wainscot", wainscot["material_id"]
                        else:
                            role, material = "base", finish["material_id"]
                        band = "low" if high <= cutaway + 1e-9 else "high"
                        index = counters[wall["id"]] = counters.get(wall["id"], -1) + 1
                        builder.add(
                            room,
                            f"finish-{wall['id']}-{index:03d}-{band}",
                            wall_box(
                                wall,
                                a,
                                b,
                                side * (wall["thickness"] / 2 + 0.001),
                                0.002,
                                z + low,
                                z + high,
                            ),
                            level_collection(level["id"], f"Wall finishes {band}"),
                            material=material,
                            kind="wall_finish",
                            slot="wall-finish",
                            properties={
                                "Finish room": room["id"],
                                "Wall ID": wall["id"],
                                "Wall face side": side,
                                "Wall finish role": role,
                            },
                        )


def stairs(builder):
    for stair in sorted(builder.design["stairs"], key=lambda item: item["id"]):
        low, high = (
            builder.levels[stair["from_level_id"]],
            builder.levels[stair["to_level_id"]],
        )
        rise = high["elevation_m"] - low["elevation_m"]
        count = stair["riser_count"]
        if (
            count < 4
            or count % 2
            or not math.isclose(rise / count, stair["riser_height_m"], abs_tol=1e-6)
        ):
            raise ValueError(f"{stair['id']}: U stair requires even risers matching the level rise")
        riser, going = rise / count, stair["tread_depth_m"]
        steps = count // 2 - 1
        run = steps * going
        params = stair.get("geometry", {})
        minx, miny, _, _ = as_polygon(stair["zone"]).bounds
        origin = params.get("origin", [minx, miny])
        axis = params.get("run_direction", [0, 1])
        norm = math.hypot(*axis)
        if norm == 0:
            raise ValueError("stair run direction cannot be zero")
        dy = [axis[0] / norm, axis[1] / norm]
        dx = [dy[1], -dy[0]]
        width = params.get("flight_width_m", 1.0)
        gap = params.get("flight_gap_m", 0.1)
        margin = params.get("side_margin_m", 0.1)
        landing = params.get("landing_depth_m", 1.0)
        # A slab landing keeps the volume beneath it free for storage.
        landing_thickness = params.get("landing_thickness_m", 0.2)
        z = low["elevation_m"]
        collection = level_collection(low["id"], "Stair")
        zone = as_polygon(stair["zone"])

        def place(
            child,
            mesh,
            mat="mat_oak",
            *,
            origin=origin,
            dx=dx,
            dy=dy,
            zone=zone,
            stair=stair,
            collection=collection,
            riser=riser,
            going=going,
        ):
            for vertex in mesh["vertices"]:
                x, y = vertex[:2]
                vertex[:2] = [
                    origin[0] + dx[0] * x + dy[0] * y,
                    origin[1] + dx[1] * x + dy[1] * y,
                ]
            footprint = Polygon([(v[0], v[1]) for v in mesh["vertices"]]).convex_hull
            if not zone.buffer(0.025).covers(footprint):
                raise ValueError(f"{stair['id']}/{child}: stair geometry exceeds its zone")
            return builder.add(
                stair,
                child,
                mesh,
                collection,
                material=mat,
                kind="stair",
                slot="stair",
                properties={"Riser height m": riser, "Tread depth m": going},
            )

        # Flight 1 rises from the origin along the run direction to a half landing; flight 2
        # returns beside it and arrives back at the origin line on the upper floor.
        for i in range(steps):
            top = z + (i + 1) * riser
            place(
                f"flight-1-riser-{i + 1:02d}",
                rectangle_mesh(margin, i * going, margin + width, (i + 1) * going, z, top),
            )
            place(
                f"flight-1-tread-{i + 1:02d}",
                rectangle_mesh(
                    margin, i * going, margin + width, (i + 1) * going, top - 0.018, top
                ),
            )
            top2 = z + (count // 2 + i + 1) * riser
            y0 = (steps - i - 1) * going
            place(
                f"flight-2-riser-{i + 1:02d}",
                rectangle_mesh(
                    margin + width + gap,
                    y0,
                    margin + 2 * width + gap,
                    y0 + going,
                    top2 - riser,
                    top2,
                ),
            )
        place(
            "landing",
            rectangle_mesh(
                margin,
                run,
                margin + 2 * width + gap,
                run + landing,
                z + rise / 2 - landing_thickness,
                z + rise / 2,
            ),
        )
        for side, x, start, end in [
            ("one", margin + 0.03, riser + 0.9, rise / 2 + 0.9),
            ("return", margin + 2 * width + gap - 0.03, rise + 0.9, rise / 2 + riser + 0.9),
        ]:
            place(
                "handrail-" + side,
                rod([x, 0.15, z + start], [x, run, z + end], 0.023),
            )
        builder.quantities["stairs"][stair["id"]] = {
            "riser_count": count,
            "riser_height_m": riser,
            "rise_m": rise,
            "tread_depth_m": going,
            "flight_width_m": width,
            "run_m": run,
            "landing_depth_m": landing,
        }


def _roof_details(builder):
    modules = 0
    for roof in sorted(builder.design["roofs"], key=lambda item: item["id"]):
        for index, trim in enumerate(roof.get("trims", [])):
            _box(
                builder,
                roof,
                f"trim-{index:03d}",
                trim["center"],
                trim["size"],
                EXTERIOR_DETAILS,
                material=trim.get("material_id") or _dark_finish(trim),
                kind="roof_trim",
            )
        pv = roof.get("pv")
        if not pv:
            continue
        roof_polygon = as_polygon(roof["polygon"])
        lift = pv["height_above_roof_m"]
        for col in range(pv["columns"]):
            for row in range(pv["rows"]):
                modules += 1
                x, y = [
                    pv["origin"][i] + (col if i == 0 else row) * pv["spacing_m"][i]
                    for i in range(2)
                ]
                w, d, t = pv["module_size_m"]
                mesh = rectangle_mesh(
                    x - w / 2, y - d / 2, x + w / 2, y + d / 2, lift - t / 2, lift + t / 2
                )
                for vertex in mesh["vertices"]:
                    vertex[2] += roof_covering_z(roof, vertex)
                footprint = Polygon([(v[0], v[1]) for v in mesh["vertices"]]).convex_hull
                if not roof_polygon.covers(footprint):
                    raise ValueError(f"{roof['id']}: PV module {col}/{row} outside roof")
                builder.add(
                    roof,
                    f"pv-{col:02d}-{row:02d}",
                    mesh,
                    ROOF_CAP_SOLAR,
                    material="mat_pv",
                    kind="pv",
                    slot="pv",
                    properties={"PV module": modules},
                )
                for side in (-1, 1):
                    a, b = ([x + side * (w / 2 - 0.01), y + end * d / 2] for end in (-1, 1))
                    a.append(roof_covering_z(roof, a) + lift)
                    b.append(roof_covering_z(roof, b) + lift)
                    builder.add(
                        roof,
                        f"pv-frame-{col:02d}-{row:02d}-{side}",
                        rod(a, b, 0.012),
                        ROOF_CAP_SOLAR,
                        material="mat_metal_dark",
                        kind="pv",
                        slot="pv-frame",
                    )


def compile_details(builder):
    _openings(builder)
    _finishes(builder)
    _room_finishes(builder)
    stairs(builder)
    _roof_details(builder)
