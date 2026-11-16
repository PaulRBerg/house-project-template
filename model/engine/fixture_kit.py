"""Lighting fixtures, bathroom fittings, plants and styling objects for the kit.

Same contract as ``furniture_kit``: envelope-centred local frame, front toward
local −Y, floor at ``z = −height / 2``. Lights are Blender emitters with an
explicit colour temperature; ceiling-hung fixtures reach ``z = +height / 2``.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .kit_geometry import (
    box,
    centered_box,
    cylinder,
    ellipse,
    lathe,
    leaf,
    merge,
    prism,
    rectangular_bowl,
    rod,
    rounded_box,
    rounded_rect,
    transform,
)
from .kit_parts import (
    NEUTRAL_WARM_K,
    Parts,
    Result,
    book_role,
    vessel_mesh,
)
from .lighting_kit import downlight, floor_lamp, led_line, pendant, sconce, table_lamp
from .plant_kit import plant

# --------------------------------------------------------------------------- bath


def mirror(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Wall mirror on the +Y wall, optionally rounded, framed or halo-backlit."""
    w, d, h = size
    parts = Parts()
    corner = float(p.get("corner_radius", 0.0))
    outline = rounded_rect(w, h, corner)
    slab = prism(outline, -d / 2, d / 2)
    slab = transform(slab, rotate=(math.pi / 2, 0, 0))
    if p.get("frame"):
        parts.add("frame", slab, "metal")
        inner = transform(
            prism(
                rounded_rect(w - 0.03, h - 0.03, max(corner - 0.015, 0.0)),
                -d / 2 - 0.002,
                -d / 2 + 0.004,
            ),
            rotate=(math.pi / 2, 0, 0),
        )
        parts.add("glass", inner, "mirror")
    else:
        parts.add("glass", slab, "mirror")
    if p.get("halo"):
        parts.add(
            "halo",
            box(-w / 2 + 0.04, d / 2 - 0.004, -h / 2 + 0.04, w / 2 - 0.04, d / 2, h / 2 - 0.04),
            "led",
        )
        parts.light(
            "halo",
            "AREA",
            (0, d / 2 - 0.005, 0),
            rotation=(math.pi / 2, 0, 0),
            shape="RECTANGLE",
            size=w - 0.1,
            size_y=h - 0.1,
            energy=float(p.get("halo_w", 6.0)),
            temperature=float(p.get("temperature", NEUTRAL_WARM_K)),
            spread=math.radians(160),
        )
    return parts.result()


def basin(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Countertop basin with a wall or deck spout; the envelope sits on the counter."""
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    bh = float(p.get("basin_height", 0.13))
    if p.get("shape", "round") == "round":
        r = min(w, d - 0.12) / 2
        parts.add(
            "basin",
            lathe(
                [
                    (r * 0.62, z0),
                    (r * 0.95, z0 + bh * 0.5),
                    (r, z0 + bh),
                    (r - 0.008, z0 + bh),
                    (r * 0.9, z0 + bh * 0.4),
                    (0.02, z0 + 0.012),
                ],
                segments=40,
                center=(0, -0.05, 0),
            ),
            "ceramic",
        )
    else:
        parts.add(
            "basin",
            rectangular_bowl((w, d - 0.12, bh), (0, -0.05, z0 + bh / 2)),
            "ceramic",
        )
    ty = d / 2 - 0.03
    spout = [
        rod((0, ty, z0), (0, ty, z0 + bh + 0.14), 0.013),
        rod((0, ty, z0 + bh + 0.14), (0, ty - 0.14, z0 + bh + 0.14), 0.009),
    ]
    parts.add("tap", merge(spout), "metal")
    return parts.result()


def towel_rail(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Heated ladder rail on the +Y wall with folded towels over some bars."""
    w, d, h = size
    parts = Parts()
    rails = [
        rod((x, d / 2 - 0.03, -h / 2), (x, d / 2 - 0.03, h / 2), 0.012)
        for x in (-w / 2 + 0.012, w / 2 - 0.012)
    ]
    bars = int(p.get("bars", 7))
    levels = [-h / 2 + 0.1 + (h - 0.2) * i / (bars - 1) for i in range(bars)]
    rails += [rod((-w / 2, d / 2 - 0.03, z), (w / 2, d / 2 - 0.03, z), 0.009) for z in levels]
    parts.add("rail", merge(rails), "metal")
    for z in p.get("towels_at", [levels[-2]]):
        parts.add(
            "towels",
            merge(
                [
                    box(
                        -w / 2 + 0.03, d / 2 - 0.05, z - 0.45, w / 2 - 0.03, d / 2 - 0.035, z + 0.01
                    ),
                    box(
                        -w / 2 + 0.03, d / 2 - 0.025, z - 0.3, w / 2 - 0.03, d / 2 - 0.01, z + 0.01
                    ),
                ]
            ),
            "towel",
        )
    return parts.result()


def towel_stack(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    w, d, h = size
    parts = Parts()
    count = int(p.get("count", 3))
    layer = h / count
    for index in range(count):
        parts.add(
            "towels",
            rounded_box(
                (w - rng.uniform(0, 0.02), d - rng.uniform(0, 0.02), layer - 0.004),
                (rng.uniform(-0.005, 0.005), 0, -h / 2 + layer * (index + 0.5)),
                radius=min(0.02, layer / 2 - 0.002),
                segments=2,
            ),
            p.get("role", "towel") if index % 2 == 0 else p.get("role_2", p.get("role", "towel")),
        )
    return parts.result()


def glass_screen(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Frameless glass shower screen along X with a slim bronze-black profile and stay."""
    w, d, h = size
    parts = Parts()
    parts.add("glass", box(-w / 2 + 0.01, -0.004, -h / 2 + 0.01, w / 2, 0.004, h / 2), "glass")
    profile = [box(-w / 2, -0.012, -h / 2, -w / 2 + 0.012, 0.012, h / 2)]
    if p.get("stay", True):
        profile.append(
            rod((w / 2 - 0.01, 0, h / 2 - 0.05), (w / 2 - 0.01, d / 2, h / 2 - 0.05), 0.008)
        )
    parts.add("profile", merge(profile), "metal")
    return parts.result()


def shower_set(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Ceiling rain head, riser and hand shower on the +Y wall."""
    w, d, h = size
    parts = Parts()
    wall = d / 2 - 0.02
    head_r = float(p.get("head_radius", 0.15))
    parts.add(
        "fittings",
        merge(
            [
                rod((0, wall, -h / 2), (0, wall, h / 2 - 0.05), 0.011),
                rod(
                    (0, wall, h / 2 - 0.05), (0, wall - (d - head_r * 2) + 0.02, h / 2 - 0.05), 0.01
                ),
                cylinder(head_r, h / 2 - 0.07, h / 2 - 0.055, center=(0, -d / 2 + head_r)),
                rounded_box(
                    (0.12, 0.05, 0.12), (0, wall - 0.02, -h / 2 + 0.25), radius=0.01, segments=1
                ),
                rod((0.12, wall - 0.03, -h / 2 + 0.3), (0.12, wall - 0.03, -h / 2 + 0.52), 0.014),
            ]
        ),
        "metal",
    )
    return parts.result()


# --------------------------------------------------------------------------- styling


def artwork(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Framed abstract landscape on the +Y wall: ground, soft sun disc and horizon bands."""
    w, d, h = size
    parts = Parts()
    frame = float(p.get("frame", 0.025))
    parts.add(
        "frame", box(-w / 2, -d / 2, -h / 2, w / 2, d / 2, h / 2), p.get("frame_role", "wood")
    )
    mat = float(p.get("mat", 0.06))
    front = -d / 2 - 0.001
    parts.add(
        "ground",
        box(-w / 2 + frame, front - 0.002, -h / 2 + frame, w / 2 - frame, front, h / 2 - frame),
        "paper",
    )
    iw, ih = w - 2 * (frame + mat), h - 2 * (frame + mat)
    parts.add(
        "canvas", box(-iw / 2, front - 0.004, -ih / 2, iw / 2, front - 0.002, ih / 2), "canvas"
    )
    motif = p.get("motif", "sun")
    if motif == "sun":
        r = min(iw, ih) * rng.uniform(0.18, 0.26)
        cx, cz = rng.uniform(-iw / 4, iw / 4), rng.uniform(0.05, ih / 4)
        disc = transform(
            prism(ellipse(2 * r, 2 * r, 40), 0, 0.002),
            rotate=(math.pi / 2, 0, 0),
            offset=(cx, front - 0.004, cz),
        )
        parts.add("motif-a", disc, "art_a")
        band = box(
            -iw / 2,
            front - 0.006,
            -ih / 2,
            iw / 2,
            front - 0.004,
            -ih / 2 + ih * rng.uniform(0.22, 0.34),
        )
        parts.add("motif-b", band, "art_b")
    elif motif == "arches":
        for index in range(3):
            r = iw * (0.32 - index * 0.08)
            arch = transform(
                prism(
                    [
                        (r * math.cos(a), r * math.sin(a))
                        for a in [math.pi * i / 24 for i in range(25)]
                    ],
                    0,
                    0.002,
                ),
                rotate=(math.pi / 2, 0, 0),
                offset=(0, front - 0.004 - index * 0.001, -ih / 2),
            )
            parts.add(f"motif-{index}", arch, ("art_a", "art_b", "paper")[index])
    else:
        for index in range(3):
            y0 = -ih / 2 + ih * index / 3
            parts.add(
                f"motif-{index}",
                box(
                    -iw / 2,
                    front - 0.005,
                    y0,
                    iw / 2,
                    front - 0.004,
                    y0 + ih / 3 * rng.uniform(0.6, 0.95),
                ),
                ("art_a", "art_b", "canvas")[index],
            )
    return parts.result()


def vessel(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Ceramic vase, jar or bowl, optionally holding a few dried stems."""
    w, d, h = size
    parts = Parts()
    kind = p.get("kind", "bud")
    body_h = h if not p.get("stems") else h * float(p.get("body_fraction", 0.45))
    parts.add("vessel", vessel_mesh(0, 0, -h / 2, w / 2, body_h, kind), p.get("role", "ceramic"))
    if p.get("stems"):
        stems = []
        heads = []
        for _index in range(int(p["stems"])):
            angle = rng.uniform(0, 2 * math.pi)
            lean = rng.uniform(0.05, 0.28)
            length = h - body_h * 0.6 - rng.uniform(0, 0.12)
            start = (0, 0, -h / 2 + body_h * 0.6)
            end = (
                math.cos(angle) * math.sin(lean) * length,
                math.sin(angle) * math.sin(lean) * length,
                start[2] + math.cos(lean) * length,
            )
            stems.append(rod(start, end, 0.0025, 6))
            for _ in range(5):
                t = rng.uniform(0.45, 1.0)
                at = tuple(s + (e - s) * t for s, e in zip(start, end, strict=True))
                heads.append(
                    transform(
                        leaf(0.05, 0.018, curl=0.1),
                        rotate=(
                            rng.uniform(-0.6, 0.6),
                            rng.uniform(-0.6, 0.6),
                            rng.uniform(0, 6.28),
                        ),
                        offset=at,
                    )
                )
        parts.add("stems", merge(stems), "stem")
        parts.add("sprigs", merge(heads), p.get("leaf_role", "dried"))
    return parts.result()


def books(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """A small horizontal stack of books, optionally topped by a tray or bowl."""
    w, d, h = size
    parts = Parts()
    count = int(p.get("count", 3))
    z = -h / 2
    for _index in range(count):
        t = (h if not p.get("bowl") else h * 0.6) / count
        bw = w - rng.uniform(0, 0.04)
        bd = d - rng.uniform(0, 0.03)
        parts.add(
            "books",
            transform(
                centered_box((bw, bd, t - 0.002)),
                rotate=(0, 0, rng.uniform(-0.08, 0.08)),
                offset=(0, 0, z + t / 2),
            ),
            book_role(rng),
        )
        z += t
    if p.get("bowl"):
        parts.add("bowl", vessel_mesh(0, 0, z, min(w, d) * 0.3, h - (z + h / 2), "bowl"), "ceramic")
    return parts.result()


def tray(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    w, d, h = size
    parts = Parts()
    parts.add("tray", prism(rounded_rect(w, d, 0.02), -h / 2, h / 2), "wood")
    return parts.result()


def cabinetry(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Single flat-shaded body for simple generated cabinetry and proxies."""
    parts = Parts()
    parts.add("body", centered_box(size), "body")
    return parts.result()


def soft_box(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Rounded single-material body: folded textiles, mats, appliances and small proxies."""
    parts = Parts()
    radius = float(p.get("radius", min(size) * 0.2))
    parts.add(
        "body",
        rounded_box(
            size,
            radius=radius,
            segments=2,
            bulge=float(p.get("bulge", 0.0)),
            bulge_axes="+z",
        ),
        p.get("role", "body"),
    )
    return parts.result()


FIXTURES: dict[str, Callable[[Sequence[float], Mapping[str, Any], random.Random], Result]] = {
    "pendant": pendant,
    "floor_lamp": floor_lamp,
    "table_lamp": table_lamp,
    "sconce": sconce,
    "led_line": led_line,
    "downlight": downlight,
    "mirror": mirror,
    "basin": basin,
    "towel_rail": towel_rail,
    "towel_stack": towel_stack,
    "glass_screen": glass_screen,
    "shower_set": shower_set,
    "artwork": artwork,
    "vessel": vessel,
    "books": books,
    "tray": tray,
    "plant": plant,
    "cabinetry": cabinetry,
    "soft_box": soft_box,
}
