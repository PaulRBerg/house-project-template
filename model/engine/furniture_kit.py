"""Parametric furniture templates compiled to multi-part, multi-material meshes.

Templates follow the envelope contract in ``kit_parts``. The front faces local −Y (toward
the entrance garden at zero rotation). Parts carry a material *role*; the furnishing maps
roles to style material IDs.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .bed_table_kit import bed, curtain, panel, rug, table
from .kit_geometry import (
    box,
    merge,
    rectangular_bowl,
    rod,
    rounded_box,
    rounded_rect,
)
from .kit_parts import (
    Parts,
    Result,
    book_role,
    flutes,
    led_strip,
    vessel_mesh,
)
from .seating_kit import bench, chair, lounge_chair, ottoman, sofa

# --------------------------------------------------------------------------- joinery


def _spans(total: float, items: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    fixed = sum(float(item[key]) for item in items if key in item)
    free = [item for item in items if key not in item]
    share = (total - fixed) / len(free) if free else 0.0
    return [float(item.get(key, share)) for item in items]


def joinery(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Cabinet runs, wardrobes, vanities and media units with 3 mm shadow gaps.

    ``columns`` list cells from bottom to top: ``door``, ``drawer``, ``panel``,
    ``oven`` (black glass), ``open`` (lit niche with ``shelves``) or ``void``.
    ``fluted`` (``true`` or ``{"pitch", "depth"}``) reeds every door and drawer front
    within the front thickness.
    """
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    board = float(p.get("board", 0.019))
    front_t = float(p.get("front_thickness", 0.02))
    gap = float(p.get("gap", 0.003))
    plinth = float(p.get("plinth", 0.08))
    handle = p.get("handle", "none")
    fluted = p.get("fluted")
    reed = fluted if isinstance(fluted, Mapping) else {}
    reed_depth = float(reed.get("depth", 0.008)) if fluted else 0.0
    front_y = -d / 2
    body_y = front_y + front_t
    bottom = z0 + plinth
    top = z0 + h
    columns = p.get("columns") or [{"cells": [{"type": "door"}]}]
    widths = _spans(w, columns, "width")
    carcass = [
        box(-w / 2, body_y, bottom, -w / 2 + board, d / 2, top),
        box(w / 2 - board, body_y, bottom, w / 2, d / 2, top),
        box(-w / 2 + board, body_y, bottom, w / 2 - board, d / 2, bottom + board),
        box(-w / 2 + board, d / 2 - board, bottom + board, w / 2 - board, d / 2, top),
    ]
    if p.get("top", "carcass") == "carcass":
        carcass.append(box(-w / 2 + board, body_y, top - board, w / 2 - board, d / 2, top))
    if plinth > 0:
        recess = float(p.get("plinth_recess", 0.05))
        parts.add(
            "plinth", box(-w / 2, front_y + recess, z0, w / 2, d / 2 - 0.02, bottom), "plinth"
        )
    elif p.get("underglow"):
        led_strip(parts, "underglow", -w / 2 + 0.05, w / 2 - 0.05, front_y + 0.08, bottom - 0.005)
    x = -w / 2
    for index, (column, width) in enumerate(zip(columns, widths, strict=True)):
        x0, x1 = x, x + width
        x = x1
        if index:
            carcass.append(
                box(
                    x0 - board / 2,
                    body_y,
                    bottom + board,
                    x0 + board / 2,
                    d / 2 - board,
                    top - board,
                )
            )
        cells = column.get("cells") or [{"type": "door"}]
        heights = _spans(top - bottom, cells, "height")
        z = bottom
        for cell_index, (cell, height) in enumerate(zip(cells, heights, strict=True)):
            c0, c1 = z, z + height
            z = c1
            kind = cell.get("type", "door")
            if cell_index and (kind == "open" or cells[cell_index - 1].get("type") == "open"):
                carcass.append(
                    box(
                        x0 + board / 2,
                        body_y,
                        c0 - board / 2,
                        x1 - board / 2,
                        d / 2 - board,
                        c0 + board / 2,
                    )
                )
            if kind == "void":
                continue
            if kind == "open":
                inner0, inner1 = x0 + board / 2, x1 - board / 2
                parts.add(
                    "niche",
                    box(inner0, d / 2 - board - 0.004, c0, inner1, d / 2 - board, c1),
                    "niche",
                )
                for shelf in range(int(cell.get("shelves", 0))):
                    sz = c0 + height * (shelf + 1) / (int(cell["shelves"]) + 1)
                    carcass.append(
                        box(
                            inner0,
                            body_y + 0.01,
                            sz - board / 2,
                            inner1,
                            d / 2 - board,
                            sz + board / 2,
                        )
                    )
                if cell.get("led"):
                    led_strip(
                        parts,
                        "niche-led",
                        inner0 + 0.03,
                        inner1 - 0.03,
                        body_y + 0.03,
                        c1 - board / 2 - 0.006,
                        energy_per_m=4.0,
                    )
                continue
            role = "appliance" if kind == "oven" else cell.get("role", "front")
            fz1 = c1 - gap / 2
            groove = handle == "groove" and kind in {"door", "drawer"}
            if groove:
                fz1 -= 0.022
                parts.add(
                    "handle",
                    box(
                        x0 + gap / 2,
                        front_y + 0.012,
                        fz1,
                        x1 - gap / 2,
                        front_y + front_t,
                        fz1 + 0.022,
                    ),
                    "plinth",
                )
            reeded = reed_depth > 0 and kind in {"door", "drawer"}
            parts.add(
                "fronts",
                box(
                    x0 + gap / 2,
                    front_y + (reed_depth if reeded else 0.0),
                    c0 + gap / 2,
                    x1 - gap / 2,
                    front_y + front_t,
                    fz1,
                ),
                role,
            )
            if reeded:
                parts.add(
                    "reeds",
                    flutes(
                        x0 + gap / 2,
                        x1 - gap / 2,
                        c0 + gap / 2,
                        fz1,
                        front_y + reed_depth,
                        pitch=float(reed.get("pitch", 0.03)),
                        depth=reed_depth,
                    ),
                    role,
                )
            if kind == "oven":
                parts.add(
                    "handle",
                    rod(
                        (x0 + 0.06, front_y - 0.02, c1 - 0.06),
                        (x1 - 0.06, front_y - 0.02, c1 - 0.06),
                        0.008,
                    ),
                    "metal",
                )
            elif handle == "bar" and kind in {"door", "drawer"}:
                if kind == "drawer" or height < 0.5:
                    length = min(0.32, (x1 - x0) * 0.45)
                    hz = c1 - min(0.06, height / 3)
                    xm = (x0 + x1) / 2
                    parts.add(
                        "handle",
                        rod(
                            (xm - length / 2, front_y - 0.022, hz),
                            (xm + length / 2, front_y - 0.022, hz),
                            0.006,
                        ),
                        "metal",
                    )
                else:
                    side = cell.get("hinge", "left" if index % 2 == 0 else "right")
                    hx = x1 - 0.045 if side == "left" else x0 + 0.045
                    length = min(0.9, height * 0.35)
                    hz = c0 + min(1.05, height / 2) if c1 - bottom > 1.4 else c1 - 0.05 - length / 2
                    parts.add(
                        "handle",
                        rod(
                            (hx, front_y - 0.022, hz - length / 2),
                            (hx, front_y - 0.022, hz + length / 2),
                            0.006,
                        ),
                        "metal",
                    )
    parts.add("carcass", merge(carcass), "carcass")
    return parts.result()


def worktop(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Stone or timber worktop with optional flush sink bowls, taps and hob glass."""
    from .geometry import extrude_polygon

    w, d, h = size
    parts = Parts()
    top = h / 2
    holes = []
    for sink in p.get("sinks", []):
        sx, sw, sd = float(sink["x"]), float(sink.get("width", 0.45)), float(sink.get("depth", 0.4))
        sy = float(sink.get("y", 0.0))
        holes.append([(x + sx, y + sy) for x, y in rounded_rect(sw - 0.012, sd - 0.012, 0.024)])
        parts.add(
            "basin",
            rectangular_bowl((sw, sd, 0.2015), (sx, sy, top - 0.09925)),
            "basin",
        )
    slab = (
        extrude_polygon({"outer": rounded_rect(w, d, min(0.004, h / 3)), "holes": holes}, -top, top)
        if holes
        else rounded_box((w, d, h), radius=min(0.004, h / 3), segments=1)
    )
    parts.add("top", slab, "stone")
    for tap in p.get("taps", []):
        tx, ty = float(tap["x"]), float(tap.get("y", d / 2 - 0.08))
        reach = float(tap.get("reach", 0.2))
        spout = [
            rod((tx, ty, top), (tx, ty, top + 0.3), 0.014),
            rod((tx, ty, top + 0.3), (tx, ty - reach, top + 0.3), 0.011),
            rod((tx, ty - reach, top + 0.3), (tx, ty - reach, top + 0.26), 0.011),
        ]
        parts.add("tap", merge(spout), "metal")
    for hob in p.get("hobs", []):
        hx, hy = float(hob["x"]), float(hob.get("y", 0.0))
        hw, hd = float(hob.get("width", 0.8)), float(hob.get("depth", 0.52))
        parts.add(
            "hob",
            box(hx - hw / 2, hy - hd / 2, top, hx + hw / 2, hy + hd / 2, top + 0.005),
            "appliance",
        )
    return parts.result()


def shelving(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Open shelving or bookcase with seeded book rows, ceramics and optional LEDs."""
    w, d, h = size
    parts = Parts()
    board = float(p.get("board", 0.024))
    z0 = -h / 2
    count = int(p.get("shelves", 4))
    sides = p.get("sides", True)
    frame = []
    inner0, inner1 = (-w / 2 + board, w / 2 - board) if sides else (-w / 2, w / 2)
    if sides:
        frame += [
            box(-w / 2, -d / 2, z0, -w / 2 + board, d / 2, z0 + h),
            box(w / 2 - board, -d / 2, z0, w / 2, d / 2, z0 + h),
        ]
    if p.get("back", True):
        parts.add("back", box(inner0, d / 2 - 0.008, z0, inner1, d / 2, z0 + h), "niche")
    levels = [z0 + (h - board) * i / max(count - 1, 1) for i in range(count)]
    for level in levels:
        frame.append(
            box(
                inner0,
                -d / 2,
                level,
                inner1,
                d / 2 - (0.008 if p.get("back", True) else 0),
                level + board,
            )
        )
    parts.add("frame", merge(frame), "wood")
    fill = float(p.get("books", 0.6))
    for index, level in enumerate(levels[:-1]):
        clear = levels[index + 1] - level - board
        _shelf_objects(
            parts,
            rng,
            inner0 + 0.02,
            inner1 - 0.02,
            level + board,
            min(clear - 0.03, 0.34),
            d,
            fill,
        )
        if p.get("led"):
            led_strip(
                parts,
                "shelf-led",
                inner0 + 0.02,
                inner1 - 0.02,
                -d / 2 + 0.03,
                levels[index + 1] - 0.005,
                energy_per_m=float(p.get("led_w_per_m", 3.0)),
            )
    return parts.result()


def _shelf_objects(
    parts: Parts,
    rng: random.Random,
    x0: float,
    x1: float,
    z: float,
    clear: float,
    depth: float,
    fill: float,
) -> None:
    """Groups of books with the odd horizontal stack and a ceramic, left to right."""
    if clear < 0.12:
        return
    x = x0 + rng.uniform(0.0, 0.12)
    while x < x1 - 0.05:
        roll = rng.random()
        if roll > fill:
            if rng.random() < 0.35 and x1 - x > 0.2:
                radius = rng.uniform(0.045, 0.07)
                height = min(clear * rng.uniform(0.45, 0.8), 0.24)
                parts.add(
                    "ceramics",
                    vessel_mesh(
                        x + radius, 0.0, z, radius, height, rng.choice(("bud", "jar", "bowl"))
                    ),
                    "ceramic",
                )
                x += radius * 2 + rng.uniform(0.05, 0.12)
            else:
                x += rng.uniform(0.08, 0.2)
            continue
        if rng.random() < 0.18:
            stack_h = 0.0
            width = rng.uniform(0.16, 0.24)
            for _layer in range(rng.randint(2, 4)):
                t = rng.uniform(0.02, 0.04)
                parts.add(
                    "books",
                    box(
                        x,
                        -depth / 2 + 0.03,
                        z + stack_h,
                        x + width,
                        -depth / 2 + 0.03 + rng.uniform(0.14, 0.2),
                        z + stack_h + t,
                    ),
                    book_role(rng),
                )
                stack_h += t
            x += width + 0.03
            continue
        for _book in range(rng.randint(4, 11)):
            t = rng.uniform(0.018, 0.045)
            if x + t > x1:
                break
            bh = min(clear, rng.uniform(0.17, 0.29))
            bd = min(depth - 0.05, rng.uniform(0.13, 0.21))
            parts.add(
                "books",
                box(x, -depth / 2 + 0.02, z, x + t, -depth / 2 + 0.02 + bd, z + bh),
                book_role(rng),
            )
            x += t + 0.001
        x += rng.uniform(0.04, 0.16)


TEMPLATES: dict[str, Callable[[Sequence[float], Mapping[str, Any], random.Random], Result]] = {
    "joinery": joinery,
    "worktop": worktop,
    "shelving": shelving,
    "sofa": sofa,
    "lounge_chair": lounge_chair,
    "ottoman": ottoman,
    "chair": chair,
    "bench": bench,
    "table": table,
    "bed": bed,
    "rug": rug,
    "curtain": curtain,
    "panel": panel,
}
