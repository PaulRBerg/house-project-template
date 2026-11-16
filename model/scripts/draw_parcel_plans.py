"""Draft labeled 4800 × 2800 px PNG plans from an explicit Blender section export.

just parcel-drawings
uv run --project model python model/scripts/draw_parcel_plans.py
"""

import argparse
import json
import math
from collections import Counter
from itertools import pairwise
from pathlib import Path

import shapely
from parcel_render_output import DRAWING_FILENAMES, prepare_outputs
from plan_sheet import (
    DASH_DOT,
    DASHED,
    HEIGHT,
    PIXELS,
    SCALE,
    SIDE_LEFT,
    SIDE_RIGHT,
    WIDTH,
    Sheet,
    hull,
)
from project_paths import BLEND, DRAWING_GEOMETRY, DRAWINGS_COMPLETE, load_engine_modules
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import unary_union

persistence = load_engine_modules("persistence")

# A room counts as the stair room when the stair parts cover this share of its floor.
STAIR_ROOM_COVERAGE = 0.5
JOINERY_PREFIXES = {"terrace": "UF", "window": "F", "double": "F", "door": "U"}
STOREY_INITIALS = {"G": "P", "U": "E"}
STOREY_NAMES = {"G": "parter", "U": "etaj"}
# Beam type marks and their placement meaning in the reinforced-concrete frame.
BEAM_TYPES = {
    "G1": "grindă în perete",
    "G2": "grindă întoarsă",
    "G3": "grindă în grosimea plăcii",
    "G4": "grindă lată în placă",
    "GE": "grindă de margine a consolei",
    "GR": "grindă planșeu peste etaj",
}
STRUCTURE_SHEET_NOTES = (
    "Clasa betonului și grosimea plăcilor din proiectul de rezistență.",
    "Parametrii seismici ag și Tc ai amplasamentului din P 100-1/2013.",
    "Predimensionare concept, nu proiect de rezistență.",
)
ARCHITECTURAL_STRUCTURE_NOTE = (
    "Structură în cadre din beton armat, zidărie de umplutură; predimensionare",
    "concept, se stabilește prin proiectul de rezistență (P 100-1/2013).",
)


def outline(data):
    """Level contour on the outer wall faces: exterior openings closed, modelling notches filled."""
    walls = unary_union(
        [hull(e) for e in data["walls"]]
        + [
            LineString(o["span"]).buffer(o["wall_thickness_m"] / 2, cap_style="flat")
            for o in data["openings"]
            if o["exterior"]
        ]
    )
    # Closing merges hairline gaps between wall spans and opening fills.
    walls = walls.buffer(0.25, join_style="mitre").buffer(-0.25, join_style="mitre")
    shell = unary_union([Polygon(poly.exterior) for poly in shapely.get_parts(walls)])
    # Walls meet centreline to centreline, leaving small steps at the outer corners; a contour that
    # fills its bounding rectangle to within 0.5% is a rectangular floor.
    return shell.envelope if shell.area > 0.995 * shell.envelope.area else shell


def joinery_type(opening):
    return (
        JOINERY_PREFIXES[opening["kind"]],
        not opening["exterior"],
        -opening["width_m"],
        -opening["height_m"],
        opening["sill_m"],
        opening["operation"] or "",
        opening.get("door_style") or "",
        opening["panels"] or 0,
        opening["blind"],
    )


def stair_rooms(data):
    """IDs of rooms the stair parts mostly cover; the travel arrow labels them instead."""
    stairs = unary_union([hull(entry) for entry in data["stairs"]])
    return {
        room["id"]
        for room in data["rooms"]
        if (shape := unary_union([Polygon(ring) for ring in room["polygons"]])).area
        and shape.intersection(stairs).area >= STAIR_ROOM_COVERAGE * shape.area
    }


def summarize(floors):
    """House-wide joinery codes, conventional areas and column storeys shared by all sheets."""
    codes, used = {}, Counter()
    # Ground-floor types number first, so each sheet reads mostly consecutive codes.
    for data in floors.values():
        for key in sorted({joinery_type(o) for o in data["openings"]} - codes.keys()):
            used[key[0]] += 1
            codes[key] = f"{key[0]}{used[key[0]]}"
    storeys = {}  # Column mark → ordered storey initials, e.g. "P + E".
    for level, data in floors.items():
        for column in data["columns"]:
            storeys.setdefault(column["mark"], {})[STOREY_INITIALS[level]] = None
    return {
        "joinery_codes": {
            o["id"]: codes[joinery_type(o)] for f in floors.values() for o in f["openings"]
        },
        "su": {level: sum(r["area_m2"] for r in f["rooms"]) for level, f in floors.items()},
        "sc": {
            level: outline(f).area
            - sum(Polygon(v["polygon"]["outer"]).area for v in f.get("voids", []))
            for level, f in floors.items()
        },
        "column_storeys": {mark: " + ".join(levels) for mark, levels in storeys.items()},
    }


def remark(opening):
    parts = []
    if opening["kind"] == "door":
        parts.append("exterioară" if opening["exterior"] else "interioară")
        style = {"sliding-pocket": "glisantă în perete", "standard": "toc aparent"}
        if opening.get("door_style") in style:
            parts.append(style[opening["door_style"]])
    elif opening["operation"] == "sliding":
        parts.append(f"glisantă, {opening['panels']} foi")
    elif opening["kind"] == "double":
        parts.append("2 canate")
    elif (opening["panels"] or 0) > 1:
        parts.append(f"{opening['panels']} panouri")
    if opening["blind"]:
        parts.append("jaluzele")
    return ", ".join(parts)


def draw_column(sheet, entry, solid):
    """A column section: solid black, or white with a diagonal cross inside black walls."""
    poly = hull(entry)
    if solid:
        sheet.shape(poly, "#111")
        return
    sheet.shape(poly, "white", "#111", 1.1)
    corners = poly.exterior.coords  # Box sections: four hull corners.
    sheet.line(corners[0], corners[2], "#111", 0.9)
    sheet.line(corners[1], corners[3], "#111", 0.9)


def draw_architectural_sheet(data, level, summary):
    wall_hulls = [(entry, hull(entry)) for entry in data["walls"]]
    walls = unary_union([shape for _, shape in wall_hulls])
    x0, y0, x1, y1 = walls.bounds
    sheet = Sheet(walls.bounds)
    image, draw, factor = sheet.image, sheet.draw, PIXELS
    pt, pixels, text, text_width = sheet.pt, sheet.pixels, sheet.text, sheet.text_width
    rotated_text, polyline, line, shape = (
        sheet.rotated_text,
        sheet.polyline,
        sheet.line,
        sheet.shape,
    )

    # Light projection lines read beneath the heavy black section walls.
    for entry in data["stairs"]:
        shape(
            hull(entry),
            "white",
            "#888" if entry["overhead"] else "#555",
            1.2,
            DASHED if entry["overhead"] else None,
        )
    # Partitions read lighter than the masonry infill envelope; the reinforced concrete
    # frame carries the loads and its columns stay legible inside both.
    partitions = unary_union([h for e, h in wall_hulls if e.get("role") == "interior"])
    envelope = unary_union([h for e, h in wall_hulls if e.get("role") != "interior"])
    if not partitions.is_empty:
        shape(partitions, "#a3a3a3", "#444", 0.9)
    shape(envelope, "#080808")
    # Beams of the slab above, in projection: dash-dot where they turn up into the storey above.
    for beam in data["beams"]:
        dash = DASH_DOT if beam["placement"] == "upturned" else DASHED
        shape(hull(beam), None, "#333", 0.8, dash)
    for column in data["columns"]:
        draw_column(sheet, column, solid=False)
    for entry in data["glazing"]:
        # Two thin pane edges; nominal frame geometry keeps openings registered.
        shape(hull(entry), "white", "#111", 1.25)
    for entry in data["frames"]:
        shape(hull(entry), "white", "#111", 1.25)
    sliding_opening_ids = {door["id"] for door in data["sliding_doors"]}
    for door in data["doors"]:
        if door.get("opening_id") in sliding_opening_ids:
            continue
        hx, hy = door["hinge"]
        ex, ey = door["end"]
        radius = math.hypot(ex - hx, ey - hy)
        start = door["closed_angle"]
        end = math.atan2(ey - hy, ex - hx)
        delta = (end - start + math.pi) % (2 * math.pi) - math.pi
        points = [
            (
                hx + radius * math.cos(start + delta * i / 40),
                hy + radius * math.sin(start + delta * i / 40),
            )
            for i in range(41)
        ]
        polyline([pt(point) for point in points], "#333", 1.5)
        shape(hull(door), "white", "#111", 1.65)
    for door in data["sliding_doors"]:
        leaf = hull({"points": door["active_leaf_points"]})
        shape(leaf, "white", "#111", 1.65)
        dx, dy = door["travel_vector"]
        length = math.hypot(dx, dy)
        if not length:
            continue
        dx, dy = dx / length, dy / length
        span = math.dist(*door["opening_span"])
        arrow_length = min(0.9, max(0.35, span * 0.35))
        head = min(0.16, arrow_length * 0.3)
        center = leaf.centroid.coords[0]
        start = (center[0] - dx * arrow_length / 2, center[1] - dy * arrow_length / 2)
        tip = (center[0] + dx * arrow_length / 2, center[1] + dy * arrow_length / 2)
        normal = (-dy, dx)
        line(start, tip, "#333", 1.5)
        for side in (-1, 1):
            wing = (
                tip[0] - dx * head + normal[0] * head * side,
                tip[1] - dy * head + normal[1] * head * side,
            )
            line(tip, wing, "#333", 1.5)
    room_shapes = {
        room["id"]: unary_union([Polygon(ring) for ring in room["polygons"]])
        for room in data["rooms"]
    }
    # The stair reads from its travel arrow; a room label would sit on the treads.
    stairwells = stair_rooms(data)
    for room in data["rooms"]:
        if room["id"] in stairwells:
            continue
        name, anchor = room["label"], tuple(room["anchor"])
        room_shape = room_shapes[room["id"]]
        if not room_shape.buffer(0.03).covers(MultiPoint([anchor])):
            anchor = room_shape.representative_point().coords[0]
        x, y = pt(anchor)
        area = f"{room['area_m2']:.1f} m²"
        if room["area_m2"] < 3:
            # Tiny rooms keep one line so their dimensions stay clear of the label.
            name, area = f"{name} · {area}", None
        span = room_shape.intersection(
            LineString([(anchor[0] - 20, anchor[1]), (anchor[0] + 20, anchor[1])])
        )
        free = (span.length - 0.6) * SCALE  # Keep clear of the interior dimension bands.
        sizes = (18, 16, 14) if area else (14,)
        size = next((s for s in sizes if text_width(name, s, True) <= free), 12)
        if area is None:
            text(name, x, y + size * 0.35, size, weight="500")
        else:
            text(name, x, y - 4, size, weight="500")
            text(area, x, y + 4 + size * 0.8, 12 if size < 16 else 13, "#444")
    for void in data.get("voids", []):
        center = Polygon(void["polygon"]["outer"]).centroid
        x, y = pt((center.x, center.y))
        text(void["name"], x, y, 16, weight="500")
        text("Gol în planșeu", x, y + 22, 12, "#444")
    # Travel arrow up flight one, across the half landing and up flight two; reversed upstairs.
    steps = {entry["part"]: hull(entry).centroid for entry in data["stairs"]}
    flights = [
        [steps[name] for name in sorted(steps) if name.startswith(f"flight-{flight}-")]
        for flight in (1, 2)
    ]
    if all(flights) and "landing" in steps:
        (first, *_, last), (turn, *_, top) = flights
        # Shift both turning points from the flight ends to the landing centre.
        mid = ((last.x + turn.x) / 2, (last.y + turn.y) / 2)
        shift = (steps["landing"].x - mid[0], steps["landing"].y - mid[1])
        route = [
            (first.x, first.y),
            (last.x, last.y),
            (last.x + shift[0], last.y + shift[1]),
            (turn.x + shift[0], turn.y + shift[1]),
            (turn.x, turn.y),
            (top.x, top.y),
        ]
        if not data.get("stair_up"):
            route.reverse()
        path = [pt(point) for point in route]
        a, b, before = path[0], path[-1], path[-2]
        polyline(path, "#111", 1.3)
        draw.ellipse([*pixels((a[0] - 4, a[1] - 4)), *pixels((a[0] + 4, a[1] + 4))], fill="#111")
        dx, dy = (
            (b[0] - before[0]) / math.dist(before, b),
            (b[1] - before[1]) / math.dist(before, b),
        )
        for side in (-1, 1):
            polyline(
                [b, (b[0] - dx * 12 - dy * 7 * side, b[1] - dy * 12 + dx * 7 * side)], "#111", 1.3
            )
        start_dy = path[1][1] - a[1]
        label = "SUS" if data.get("stair_up") else "JOS"
        text(label, a[0], a[1] + (22 if start_dy < 0 else -12), 12, weight="600")

    # Dimensions are measured from the section, never room targets.
    tick, dimension = sheet.tick, sheet.dimension

    def chain(side):
        """Exterior dimension chain: wall piers, openings and overall length on one facade."""
        across = 0 if side in {"garden", "rear"} else 1
        edge = {"garden": y0, "rear": y1, "service": x0, "private": x1}[side]
        start, end = (x0, x1) if across == 0 else (y0, y1)
        intervals = []
        for bounds in wall_bounds:
            near = bounds[1 - across] if side in {"garden", "service"} else bounds[3 - across]
            if abs(near - edge) < 0.25:
                intervals.append((bounds[across], bounds[across + 2]))
        stops = {start, end}
        # Pieces within 1 cm join, unlike geometry.merge_intervals, so no sliver stops appear.
        merged = []
        for lo, hi in sorted(intervals):
            if merged and lo <= merged[-1][1] + 0.01:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        for lo, hi in merged:
            stops.update(min(max(v, start), end) for v in (lo, hi))
        stops = sorted(stops)
        stops = [v for i, v in enumerate(stops) if i == 0 or v - stops[i - 1] > 0.02]
        outward = -1 if side in {"garden", "service"} else 1

        def at(value, distance):
            level = edge + outward * distance
            return pt((value, level) if across == 0 else (level, value))

        # Labels read from the bottom or right: above horizontal lines, left of vertical ones.
        text_offset = -8 if across == 0 else -9
        for value in stops:
            polyline([at(value, 0.15), at(value, 1.1)], "#bbb", 0.8)
        for lo, hi in pairwise(stops) if len(stops) > 2 else ():
            label = f"{hi - lo:.2f}"
            short = (hi - lo) * SCALE < 34
            dimension(at(lo, 0.55), at(hi, 0.55), text_offset * (2.4 if short else 1), label, 11)
        dimension(at(start, 1.05), at(end, 1.05), text_offset, f"{end - start:.2f}", 13, "#333")

    wall_bounds = [shape.bounds for _, shape in wall_hulls]
    for side in ("garden", "rear", "service", "private"):
        chain(side)

    # Interior wall faces: each room edge that runs along a sectioned wall.
    for room in data["rooms"]:
        if room["id"] in stairwells:
            continue
        seen = set()  # One dimension per repeated parallel face length.
        room_shape = room_shapes[room["id"]]
        room_shape = room_shape.buffer(0.01, join_style="mitre").buffer(-0.01, join_style="mitre")
        room_shape = room_shape.simplify(0.03)
        for poly in shapely.get_parts(room_shape):
            for ring in [poly.exterior, *poly.interiors]:
                for a, b in pairwise(ring.coords):
                    length = math.dist(a, b)
                    if length < 0.8:
                        continue
                    edge_line = LineString([a, b])
                    # A wall fills one 0.05 m side of the buffer; keep faces at least 40% walled.
                    if walls.intersection(edge_line.buffer(0.05)).area < 0.02 * length:
                        continue
                    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
                    key = (round(abs(ux)), round(length, 1))
                    if key in seen:
                        continue
                    seen.add(key)
                    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                    nx, ny = -uy, ux
                    if not poly.contains(Point(mid[0] + nx * 0.1, mid[1] + ny * 0.1)):
                        nx, ny = -nx, -ny
                    inset = 0.10
                    pa = pt((a[0] + nx * inset + ux * 0.02, a[1] + ny * inset + uy * 0.02))
                    pb = pt((b[0] + nx * inset - ux * 0.02, b[1] + ny * inset - uy * 0.02))
                    polyline([pa, pb], "#b0b0b0", 0.8)
                    for p in (pa, pb):
                        tick(p, 3, "#777", 1)
                    tx, ty = pt((mid[0] + nx * (inset + 0.12), mid[1] + ny * (inset + 0.12)))
                    angle = 0 if abs(ux) > abs(uy) else 90
                    rotated_text(f"{length:.2f}", tx, ty, 10, "#8a8a8a", angle)

    # Joinery marks: outside the envelope, or on the side of an interior wall away from the swing.
    shell = outline(data)
    leaves = {door.get("opening_id"): door for door in data["doors"]}
    for opening in data["openings"]:
        code = summary["joinery_codes"][opening["id"]]
        (ax, ay), (bx, by) = opening["span"]
        length = math.dist((ax, ay), (bx, by))
        ux, uy = (bx - ax) / length, (by - ay) / length
        nx, ny = -uy, ux
        mid = ((ax + bx) / 2, (ay + by) / 2)
        w, h = text_width(code, 10, True) + 10, 16
        reach = (h if abs(ny) > abs(nx) else w) / 2 / SCALE
        if opening["exterior"]:
            side = -1 if shell.contains(Point(mid[0] + nx, mid[1] + ny)) else 1
            gap = 0.08
        else:
            leaf = leaves.get(opening["id"])
            swing = (leaf["end"][0] - mid[0]) * nx + (leaf["end"][1] - mid[1]) * ny if leaf else -1
            side = -1 if swing > 0 else 1
            gap = 0.30
        distance = opening["wall_thickness_m"] / 2 + gap + reach
        cx, cy = pt((mid[0] + nx * side * distance, mid[1] + ny * side * distance))
        draw.rounded_rectangle(
            [*pixels((cx - w / 2, cy - h / 2)), *pixels((cx + w / 2, cy + h / 2))],
            radius=3 * factor,
            fill="white",
            outline="#111",
            width=factor,
        )
        text(code, cx, cy, 10, anchor="center", weight="600")

    # Schedule column: conventional areas, joinery and legend.
    left, right = SIDE_LEFT, SIDE_RIGHT
    heading = sheet.heading

    y = 205
    heading("TABLOU DE SUPRAFEȚE", y)
    y += 32
    for room in data["rooms"]:
        text(room["label"], left, y, 13, "#222", "start")
        text(f"{room['area_m2']:.2f} m²", right, y, 13, "#222", "end")
        y += 23
    polyline([(left, y - 14), (right, y - 14)], "#999", 1)
    y += 6
    storey = STOREY_NAMES[level]
    for label, value in (
        (f"Arie utilă {storey}", summary["su"][level]),
        (f"Arie construită {storey}", summary["sc"][level]),
        ("Arie utilă casă (Su)", sum(summary["su"].values())),
        ("Arie construită la sol (Sc)", next(iter(summary["sc"].values()))),
        ("Arie desfășurată casă (Sd)", sum(summary["sc"].values())),
    ):
        text(label, left, y, 13, "#111", "start", "600")
        text(f"{value:.2f} m²", right, y, 13, "#111", "end", "600")
        y += 23
    for note in (
        "Concept măsurat pe model: Su pe fețele pardoselilor (scara inclusă),",
        "Sc/Sd: contur pereți, fără finisaje; Sd exclude golurile din planșeu.",
        "Valorile oficiale le stabilește arhitectul, conform STAS 4908-85.",
    ):
        text(note, left, y, 11, "#777", "start")
        y += 16

    y += 30
    heading("TÂMPLĂRIE", y)
    y += 30
    columns = (left, left + 48, left + 92, left + 196, left + 258)
    sheet.table_row(columns, ("Cod", "Buc.", "L × H cm", "Parapet", "Observații"), y, header=True)
    y += 22
    openings = data["openings"]
    counts = Counter(summary["joinery_codes"][o["id"]] for o in openings)
    for code in sorted(counts, key=lambda c: (c.rstrip("0123456789"), int(c.lstrip("FU")))):
        sample = next(o for o in openings if summary["joinery_codes"][o["id"]] == code)
        values = (
            code,
            str(counts[code]),
            f"{sample['width_m'] * 100:.0f} × {sample['height_m'] * 100:.0f}",
            f"{sample['sill_m'] * 100:.0f}" if sample["sill_m"] else "–",
            remark(sample),
        )
        sheet.table_row(columns, values, y)
        y += 21
    text(
        "Dimensiuni nominale de gol; tâmplăria se detaliază prin proiect.",
        left,
        y + 2,
        11,
        "#777",
        "start",
    )

    y += 46
    heading("LEGENDĂ", y)
    y += 30

    def thickness_range(entries):
        values = sorted({round(e["thickness_m"] * 100) for e in entries if "thickness_m" in e})
        return f"{values[0]}–{values[-1]}" if len(values) > 1 else f"{values[0]}" if values else ""

    exterior = [e for e in data["walls"] if e.get("role") != "interior"]
    interior = [e for e in data["walls"] if e.get("role") == "interior"]
    envelope_label = (
        f"Zidărie exterioară de umplutură, cărămidă ceramică {thickness_range(exterior)} cm"
    )
    sheet.legend_box(y, "#080808")
    text(envelope_label, left + 48, y, 12, "#222", "start")
    y += 24
    sheet.legend_box(y, "#a3a3a3", "#444")
    text(
        f"Pereți interiori {thickness_range(interior)} cm, concept",
        left + 48,
        y,
        12,
        "#222",
        "start",
    )
    y += 24
    placements = {beam["placement"] for beam in data["beams"]}
    for present, swatch, label in (
        (
            data["columns"],
            lambda y: sheet.column_swatch(y, solid=False),
            "Stâlp beton armat (S)",
        ),
        (
            placements - {"upturned"},
            lambda y: sheet.legend_lines(y, "#333", DASHED),
            "Grindă b.a. peste nivel, proiecție",
        ),
        (
            "upturned" in placements,
            lambda y: sheet.legend_lines(y, "#333", DASH_DOT),
            "Grindă întoarsă (în perete)",
        ),
    ):
        if present:
            swatch(y)
            text(label, left + 48, y, 12, "#222", "start")
            y += 24
    draw.rounded_rectangle(
        [*pixels((left + 3, y - 13)), *pixels((left + 31, y + 3))],
        radius=3 * factor,
        fill="white",
        outline="#111",
        width=factor,
    )
    text("F1", left + 17, y - 5, 10, anchor="center", weight="600")
    text("Marcaj tâmplărie, vezi tabelul", left + 48, y, 12, "#222", "start")
    y += 26
    for note in ARCHITECTURAL_STRUCTURE_NOTE:
        text(note, left, y, 11, "#777", "start")
        y += 16

    sheet.frame(
        storey.capitalize(),
        "PLAN ARHITECTURAL · CONCEPT",
        data["elevation_m"],
        (
            f"Secțiune la +{summary['section_height_m']:.2f} m față de fiecare nivel · Cote în metri"
            " · Suprafețe măsurate pe fețele pardoselilor",
            "Goluri și uși din model · Vitrajele glisante au săgeată de culisare · Alte mecanisme neprecizate · Concept, nu plan de execuție",
        ),
        summary["north_local"],
        summary["project_name"],
    )
    return image, walls.area


def natural_key(mark):
    """Sort S2 before S10."""
    digits = mark.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return (mark[: len(mark) - len(digits)], int(digits) if digits.isdigit() else 0, mark)


def draw_structure_sheet(data, level, summary):
    """Structure sheet: pale walls, black columns, beam outlines, axes and schedules."""
    walls = unary_union([hull(entry) for entry in data["walls"]])
    x0, y0, x1, y1 = walls.bounds
    sheet = Sheet(walls.bounds)
    pt, text, text_width = sheet.pt, sheet.text, sheet.text_width
    left = SIDE_LEFT
    sheet.shape(walls, "#eeeeee", "#c8c8c8", 0.6)
    for entry in data["stairs"]:
        sheet.shape(hull(entry), None, "#d4d4d4", 0.6)
    occupied = []  # Page-space label boxes already placed.

    def label_box(x, y, w, h):
        return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)

    # Structural axes: dash-dot lines, a chain between axes and bubbles on the rear and service sides.
    axes = data["axes"]
    positions = {d: sorted(a["position"] for a in axes if a["direction"] == d) for d in "xy"}
    gx0, gx1 = min([x0, *positions["x"]]), max([x1, *positions["x"]])
    gy0, gy1 = min([y0, *positions["y"]]), max([y1, *positions["y"]])
    radius = 15
    for axis in axes:
        value = axis["position"]
        if axis["direction"] == "x":
            start, end = (value, gy0 - 0.4), (value, gy1 + 1.25)
            bubble = pt((value, gy1 + 1.25 + radius / SCALE))
        else:
            start, end = (gx1 + 0.4, value), (gx0 - 1.25, value)
            bubble = pt((gx0 - 1.25 - radius / SCALE, value))
        sheet.line(start, end, "#777", 0.8, DASH_DOT)
        bx, by = bubble
        sheet.draw.ellipse(
            [*sheet.pixels((bx - radius, by - radius)), *sheet.pixels((bx + radius, by + radius))],
            fill="white",
            outline="#111",
            width=PIXELS,
        )
        text(axis["label"], bx, by, 13, anchor="center", weight="600")
    for values, at, offset in (
        (positions["x"], lambda v: pt((v, gy1 + 0.6)), -8),
        (positions["y"], lambda v: pt((gx0 - 0.6, v)), -9),
    ):
        for lo, hi in pairwise(values):
            sheet.dimension(at(lo), at(hi), offset, f"{hi - lo:.2f}", 11)

    # Small room names on a white knockout keep orientation without competing with the frame.
    stairwells = stair_rooms(data)
    for room in data["rooms"]:
        if room["id"] not in stairwells:
            x, y = pt(room["anchor"])
            spot = label_box(x, y, text_width(room["label"], 11) + 6, 14)
            sheet.draw.rectangle(
                [*sheet.pixels(spot.bounds[:2]), *sheet.pixels(spot.bounds[2:])], fill="white"
            )
            text(room["label"], x, y, 11, "#a0a0a0", anchor="center")
            occupied.append(spot)

    # Beams of the slab above as solid outlines, then columns cut at the section height.
    for beam in data["beams"]:
        sheet.shape(hull(beam), None, "#222", 1.0)
    center = walls.centroid
    for column in data["columns"]:
        draw_column(sheet, column, solid=True)
        poly = hull(column)
        cx, cy = poly.centroid.x, poly.centroid.y
        reach = max(poly.bounds[2] - poly.bounds[0], poly.bounds[3] - poly.bounds[1]) / 2
        # The mark sits diagonally inward, away from the axis bubbles and chains.
        dx = math.copysign(1, center.x - cx)
        dy = math.copysign(1, center.y - cy)
        w = text_width(column["mark"], 11, True) + 4
        x, y = pt((cx + dx * reach, cy + dy * reach))
        x, y = x - dx * (w / 2 + 3), y - dy * 10
        occupied.append(label_box(x, y, w, 14))
        text(column["mark"], x, y, 11, anchor="center", weight="600")
    columns = [label_box(*pt(hull(c).centroid.coords[0]), 16, 16) for c in data["columns"]]
    for beam in data["beams"]:
        poly = hull(beam)
        # The longest hull edge runs along the beam; its rectangular footprint gives the width.
        (ax, ay), (bx, by) = max(pairwise(poly.exterior.coords), key=lambda e: math.dist(*e))
        length = math.dist((ax, ay), (bx, by))
        ux, uy = (bx - ax) / length, (by - ay) / length
        width = poly.area / length
        label = f"{beam['mark']} {beam['section']}"
        along = abs(ux) > abs(uy)
        w, h = text_width(label, 10) + 6, 13
        w, h = (w, h) if along else (h, w)
        mid = poly.centroid
        inward = 1 if (center.x - mid.x) * -uy + (center.y - mid.y) * ux > 0 else -1
        candidates = [
            (
                mid.x + ux * shift * length - uy * side * gap,
                mid.y + uy * shift * length + ux * side * gap,
            )
            for shift in (0, -0.25, 0.25)
            for side in (inward, -inward)
            for gap in [width / 2 + (h if along else w) / 2 / SCALE + 0.03]
        ]
        spots = [label_box(*pt(c), w, h) for c in candidates]
        spot = next(
            (s for s in spots if not any(s.intersects(o) for o in occupied + columns)), spots[0]
        )
        occupied.append(spot)
        x, y = spot.centroid.x, spot.centroid.y
        sheet.draw.rectangle(
            [*sheet.pixels((x - w / 2, y - h / 2)), *sheet.pixels((x + w / 2, y + h / 2))],
            fill="white",
        )
        sheet.rotated_text(label, x, y, 10, "#222", 0 if along else 90)

    # Schedule column: columns, beam types, legend and notes.
    y = 205
    sheet.heading("STÂLPI", y)
    y += 30
    layout = (left, left + 70, left + 120, left + 250)
    sheet.table_row(layout, ("Marcaj", "Buc.", "Secțiune cm", "Niveluri"), y, header=True)
    y += 22
    marks = Counter(c["mark"] for c in data["columns"])
    for mark in sorted(marks, key=natural_key):
        sections = sorted({c["section"] for c in data["columns"] if c["mark"] == mark})
        values = (mark, str(marks[mark]), ", ".join(sections), summary["column_storeys"][mark])
        sheet.table_row(layout, values, y)
        y += 21

    y += 30
    sheet.heading("GRINZI", y)
    y += 30
    layout = (left, left + 44, left + 88, left + 196)
    sheet.table_row(layout, ("Tip", "Buc.", "Secțiune cm", "Rol"), y, header=True)
    y += 22
    # One row per type and section; the role reads once per type.
    types = Counter((b["mark"], b["section"]) for b in data["beams"])
    order = list(BEAM_TYPES)
    previous = None
    for mark, section in sorted(types, key=lambda t: (order.index(t[0]), t[1])):
        role = BEAM_TYPES[mark] if mark != previous else ""
        sheet.table_row(layout, (mark, str(types[mark, section]), section, role), y)
        previous = mark
        y += 21

    y += 30
    sheet.heading("LEGENDĂ", y)
    y += 30
    for swatch, label in (
        (lambda y: sheet.column_swatch(y, solid=True), "Stâlp beton armat, marcaj S"),
        (lambda y: sheet.legend_box(y, "white", "#222"), "Grindă b.a. în planșeul peste nivel"),
        (lambda y: sheet.legend_lines(y, "#777", DASH_DOT, 1), "Ax structural"),
        (lambda y: sheet.legend_box(y, "#eeeeee", "#c8c8c8"), "Pereți și zidărie de umplutură"),
    ):
        swatch(y)
        text(label, left + 48, y, 12, "#222", "start")
        y += 24

    y += 22
    sheet.heading("NOTE", y)
    y += 30
    for note in STRUCTURE_SHEET_NOTES:
        text(note, left, y, 12, "#222", "start")
        y += 20

    sheet.frame(
        f"Structură {STOREY_NAMES[level]}",
        "PLAN STRUCTURĂ · PREDIMENSIONARE CONCEPT",
        data["elevation_m"],
        (
            f"Stâlpi secționați la +{summary['section_height_m']:.2f} m față de nivel"
            " · Grinzile planșeului peste nivel, în proiecție · Cote între axe în metri",
            "Predimensionare concept pe modelul procedural · Secțiunile le stabilește proiectul"
            " de rezistență · Nu plan de execuție",
        ),
        summary["north_local"],
        summary["project_name"],
    )
    return sheet.image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    source_bytes = DRAWING_GEOMETRY.read_bytes()
    export = json.loads(source_bytes)
    if export["blend_sha256"] != persistence.sha256_file(BLEND):
        raise ValueError("Drawing export is stale; export the current saved blend again")
    run_dir = prepare_outputs("drawings", export["blend_sha256"])
    (run_dir / DRAWING_GEOMETRY.name).write_bytes(source_bytes)
    completion = run_dir / DRAWINGS_COMPLETE
    receipt = {
        "started_at": persistence.utc_now(),
        "blend_sha256": export["blend_sha256"],
        "geometry_sha256": persistence.sha256_file(DRAWING_GEOMETRY),
        "renderer_sha256": persistence.sha256_file(Path(__file__)),
        "sheet_sha256": persistence.sha256_file(Path(__file__).with_name("plan_sheet.py")),
        "engine": "Pillow / PNG",
        "images": [],
    }
    out = run_dir / "plans"
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        **summarize(export["floors"]),
        "north_local": export["north_local"],
        "project_name": export["project_name"],
        "section_height_m": export["section_height_m"],
    }
    for level, label in [("G", "ground"), ("U", "upper")]:
        data = export["floors"][level]
        counts = {
            "columns": len(data["columns"]),
            "beams": len(data["beams"]),
        }
        image, wall_area = draw_architectural_sheet(data, level, summary)
        structure = draw_structure_sheet(data, level, summary)
        for sheet, picture, details in (
            (
                "drawing",
                image,
                {
                    "wall_section_m2": round(wall_area, 4),
                    "doors": len(data["doors"]),
                    "rooms": len(data["rooms"]),
                    **counts,
                },
            ),
            ("structure", structure, {**counts, "axes": len(data["axes"])}),
        ):
            png_path = out / DRAWING_FILENAMES[f"parcel-{label}-{sheet}.png"]
            picture.save(png_path)
            assert picture.size == (WIDTH * PIXELS, HEIGHT * PIXELS)
            receipt["images"].append(
                {
                    "path": str(png_path),
                    "level": level,
                    "sheet": sheet,
                    "labels": True,
                    "resolution": picture.size,
                    **details,
                }
            )
    receipt.update(status="complete", completed_at=persistence.utc_now())
    persistence.atomic_write_json(completion, receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
