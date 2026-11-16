"""Upholstered seating templates: sofas, lounge chairs, ottomans, chairs and benches."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from typing import Any

from .kit_geometry import (
    box,
    centered_box,
    corner_points,
    curved_wall,
    lathe,
    merge,
    prism,
    rod,
    rounded_box,
    rounded_rect,
    transform,
)
from .kit_parts import Parts, Result

# --------------------------------------------------------------------------- upholstery


def sofa(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Deep, low sofa on a plinth with arms, loose cushions and optional chaise."""
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    seat = z0 + float(p.get("seat_height", 0.42))
    arm_w = float(p.get("arm_width", 0.22))
    arm_top = z0 + float(p.get("arm_height", 0.6))
    back_d = float(p.get("back_depth", 0.24))
    base_h = float(p.get("base_height", 0.1))
    cushion = float(p.get("cushion_thickness", 0.17))
    radius = float(p.get("radius", 0.05))
    chaise = p.get("chaise")
    chaise_w = float(p.get("chaise_width", 0.95)) if chaise else 0.0
    main_d = float(p.get("main_depth", d)) if chaise else d
    arms = {"left": chaise != "left", "right": chaise != "right"}
    frame_top = seat - cushion
    main_x0 = -w / 2 + (chaise_w if chaise == "left" else 0)
    main_x1 = w / 2 - (chaise_w if chaise == "right" else 0)
    sections = [(main_x0, main_x1, d / 2 - main_d)]
    if chaise:
        cx0, cx1 = (-w / 2, main_x0) if chaise == "left" else (main_x1, w / 2)
        sections.append((cx0, cx1, -d / 2))
    for x0, x1, y0 in sections:
        parts.add(
            "base",
            rounded_box(
                (x1 - x0, d / 2 - y0, frame_top - z0 - base_h),
                ((x0 + x1) / 2, (y0 + d / 2) / 2, (z0 + base_h + frame_top) / 2),
                radius=0.03,
                segments=2,
            ),
            "upholstery",
        )
        parts.add(
            "plinth",
            box(x0 + 0.05, y0 + 0.05, z0, x1 - 0.05, d / 2 - 0.05, z0 + base_h),
            "base",
        )
    parts.add(
        "back",
        rounded_box(
            (w, back_d, h - (base_h)),
            (0, d / 2 - back_d / 2, (z0 + base_h + z0 + h) / 2),
            radius=radius,
            segments=3,
            bulge=0.01,
            bulge_axes="-y",
        ),
        "upholstery",
    )
    seat_x0 = main_x0 + (arm_w if arms["left"] and chaise != "left" else 0)
    seat_x1 = main_x1 - (arm_w if arms["right"] and chaise != "right" else 0)
    for side, flag in arms.items():
        if not flag:
            continue
        ax0, ax1 = (main_x0, main_x0 + arm_w) if side == "left" else (main_x1 - arm_w, main_x1)
        y0 = d / 2 - main_d
        parts.add(
            "arms",
            rounded_box(
                (ax1 - ax0, main_d - back_d + 0.02, arm_top - z0 - base_h),
                ((ax0 + ax1) / 2, (y0 + d / 2 - back_d + 0.02) / 2, (z0 + base_h + arm_top) / 2),
                radius=radius,
                segments=3,
            ),
            "upholstery",
        )
    seats = int(p.get("seats", 3))
    seat_front = d / 2 - main_d
    span = (seat_x1 - seat_x0) / seats
    back_front = d / 2 - back_d
    for index in range(seats):
        cx = seat_x0 + span * (index + 0.5)
        parts.add(
            "cushions",
            rounded_box(
                (span - 0.012, back_front - seat_front + 0.01, cushion),
                (cx, (seat_front + back_front) / 2, seat - cushion / 2 + 0.005),
                radius=0.045,
                segments=3,
                bulge=0.018,
                bulge_axes="+z",
            ),
            "cushion",
        )
    if chaise:
        cx0, cx1 = sections[1][0], sections[1][1]
        parts.add(
            "cushions",
            rounded_box(
                (cx1 - cx0 - 0.012, back_front + d / 2 + 0.01, cushion),
                ((cx0 + cx1) / 2, (-d / 2 + back_front) / 2, seat - cushion / 2 + 0.005),
                radius=0.045,
                segments=3,
                bulge=0.018,
                bulge_axes="+z",
            ),
            "cushion",
        )
    back_h = min(h - (seat - z0) + 0.03, 0.5)
    back_t = float(p.get("back_cushion_depth", 0.2))
    back_spans = [(seat_x0 + span * i, seat_x0 + span * (i + 1)) for i in range(seats)]
    if chaise:
        back_spans.append((sections[1][0], sections[1][1]))
    for bx0, bx1 in back_spans:
        cushion_mesh = rounded_box(
            (bx1 - bx0 - 0.015, back_t, back_h),
            (0, 0, 0),
            radius=0.06,
            segments=3,
            bulge=0.02,
            bulge_axes="-y",
        )
        placed = transform(
            cushion_mesh,
            rotate=(-0.16, 0.0, 0.0),
            offset=((bx0 + bx1) / 2, back_front - back_t / 2 + 0.03, seat + back_h / 2 - 0.02),
        )
        parts.add("back-cushions", placed, "cushion")
    for index, pillow in enumerate(p.get("pillows", [])):
        px = float(pillow["x"])
        size_p = float(pillow.get("size", 0.48))
        mesh = rounded_box(
            (size_p, 0.14, size_p), radius=0.06, segments=2, bulge=0.03, bulge_axes="y"
        )
        forward = float(pillow.get("forward", 0.0))
        mesh = transform(
            mesh,
            rotate=(-0.32, 0.0, float(pillow.get("turn", 0.12 * (-1) ** index))),
            offset=(px, back_front - back_t - 0.02 - forward, seat + size_p / 2 - 0.02),
        )
        parts.add(f"pillow-{index}", mesh, pillow.get("role", "accent"))
    throw = p.get("throw")
    if throw:
        tx = (
            (seat_x1 - arm_w / 2)
            if throw.get("side", "right") == "right" and arms["right"]
            else seat_x0 - arm_w / 2
        )
        drape = merge(
            [
                box(
                    tx - 0.25,
                    seat_front + 0.1,
                    arm_top - 0.004,
                    tx + 0.25,
                    seat_front + 0.55,
                    arm_top + 0.01,
                ),
                box(
                    tx
                    + (arm_w / 2 + 0.002) * (1 if throw.get("side", "right") == "right" else -1)
                    - 0.006,
                    seat_front + 0.1,
                    arm_top - 0.3,
                    tx + (arm_w / 2 + 0.012) * (1 if throw.get("side", "right") == "right" else -1),
                    seat_front + 0.55,
                    arm_top + 0.01,
                ),
            ]
        )
        parts.add("throw", drape, throw.get("role", "throw"))
    return parts.result()


def lounge_chair(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """High-back reclining lounge chair on a swivel or timber base."""
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    seat = z0 + float(p.get("seat_height", 0.42))
    arm_w = float(p.get("arm_width", 0.14))
    lean = float(p.get("lean", 0.28))
    base = p.get("base", "swivel")
    if base == "swivel":
        parts.add(
            "base",
            merge(
                [
                    lathe([(0.3, z0), (0.3, z0 + 0.012), (0.05, z0 + 0.03)], segments=32),
                    lathe([(0.035, z0 + 0.02), (0.035, seat - 0.16)], segments=16),
                ]
            ),
            "metal",
        )
    else:
        for lx in (-w / 2 + 0.06, w / 2 - 0.06):
            parts.add(
                "legs",
                merge(
                    [
                        rod((lx, -d / 2 + 0.06, z0), (lx, -d / 2 + 0.1, seat - 0.14), 0.02),
                        rod((lx, d / 2 - 0.08, z0), (lx, d / 2 - 0.16, seat - 0.14), 0.02),
                    ]
                ),
                "wood",
            )
    shell_d = d * 0.78
    parts.add(
        "seat-shell",
        rounded_box(
            (w, shell_d, 0.2), (0, -d / 2 + shell_d / 2, seat - 0.2), radius=0.05, segments=3
        ),
        "upholstery",
    )
    parts.add(
        "seat",
        rounded_box(
            (w - 2 * arm_w, shell_d - 0.12, 0.13),
            (0, -d / 2 + shell_d / 2 - 0.02, seat - 0.05),
            radius=0.05,
            segments=3,
            bulge=0.015,
            bulge_axes="+z",
        ),
        "cushion",
    )
    back_h = h - (seat - z0) + 0.06
    back = rounded_box(
        (w - 0.04, 0.2, back_h), radius=0.07, segments=3, bulge=0.02, bulge_axes="-y"
    )
    back = transform(
        back,
        rotate=(-lean, 0.0, 0.0),
        offset=(
            0,
            d / 2 - 0.22 - math.sin(lean) * back_h / 2 + 0.1,
            seat - 0.12 + back_h / 2 * math.cos(lean),
        ),
    )
    parts.add("back", back, "upholstery")
    head = rounded_box((w * 0.62, 0.14, 0.22), radius=0.06, segments=2, bulge=0.02, bulge_axes="-y")
    head = transform(
        head,
        rotate=(-lean, 0.0, 0.0),
        offset=(
            0,
            d / 2 - 0.3 - math.sin(lean) * (back_h - 0.18) + 0.1,
            seat - 0.12 + (back_h - 0.16) * math.cos(lean),
        ),
    )
    parts.add("headrest", head, "cushion")
    for side in (-1, 1):
        parts.add(
            "arms",
            rounded_box(
                (arm_w, shell_d - 0.05, 0.22),
                (side * (w / 2 - arm_w / 2), -d / 2 + shell_d / 2 + 0.02, seat + 0.08),
                radius=0.05,
                segments=2,
            ),
            "upholstery",
        )
    for _index, pillow in enumerate(p.get("pillows", [])):
        mesh = rounded_box((0.4, 0.12, 0.3), radius=0.05, segments=2, bulge=0.025, bulge_axes="y")
        parts.add(
            "pillow",
            transform(mesh, rotate=(-lean, 0.0, 0.0), offset=(0, d / 2 - 0.42, seat + 0.2)),
            pillow.get("role", "accent"),
        )
    if p.get("throw"):
        parts.add(
            "throw",
            merge(
                [
                    box(
                        -w / 2 - 0.01,
                        -d / 2 + 0.25,
                        seat + 0.18,
                        -w / 2 + arm_w + 0.02,
                        -d / 2 + 0.6,
                        seat + 0.192,
                    ),
                    box(
                        -w / 2 - 0.012,
                        -d / 2 + 0.25,
                        seat - 0.12,
                        -w / 2 - 0.002,
                        -d / 2 + 0.6,
                        seat + 0.192,
                    ),
                ]
            ),
            p["throw"].get("role", "throw"),
        )
    return parts.result()


def ottoman(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    leg = float(p.get("leg_height", 0.0))
    if p.get("shape", "rect") == "round":
        top_r = min(w, d) / 2
        profile = [
            (top_r * 0.92, z0),
            (top_r, z0 + 0.05),
            (top_r, z0 + h - 0.06),
            (top_r * 0.95, z0 + h - 0.015),
            (top_r * 0.6, z0 + h),
        ]
        parts.add("body", lathe(profile, segments=40), "upholstery")
    else:
        if leg > 0:
            for lx, ly in corner_points(-w / 2 + 0.05, -d / 2 + 0.05, w / 2 - 0.05, d / 2 - 0.05):
                parts.add(
                    "legs",
                    lathe([(0.016, z0), (0.022, z0 + leg)], segments=12, center=(lx, ly, 0.0)),
                    p.get("leg_role", "wood"),
                )
        parts.add(
            "body",
            rounded_box(
                (w, d, h - leg),
                (0, 0, z0 + leg + (h - leg) / 2),
                radius=float(p.get("radius", 0.05)),
                segments=3,
                bulge=0.012,
                bulge_axes="+z",
            ),
            "upholstery",
        )
    return parts.result()


def _footrest(w: float, d: float, inset: float, ring: float) -> list[dict]:
    """Stretcher ring that turns a high chair into a counter stool."""
    x0, y0, x1, y1 = -w / 2 + inset, -d / 2 + inset, w / 2 - inset, d / 2 - inset
    return [
        rod((x0, y0, ring), (x1, y0, ring), 0.011),
        rod((x0, y1, ring), (x1, y1, ring), 0.011),
        rod((x0, y0, ring), (x0, y1, ring), 0.011),
        rod((x1, y0, ring), (x1, y1, ring), 0.011),
    ]


def _shell_chair(size: Sequence[float], p: Mapping[str, Any]) -> Result:
    """Tub shell whose back curves forward into low arms, on tapered oak legs.

    The shell takes ``shell_role`` (upholstery by default; map it to oak for a timber shell).
    """
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    seat = z0 + float(p.get("seat_height", 0.46))
    inset = 0.045
    legs = [
        lathe([(0.012, z0), (0.019, seat - 0.07)], segments=12, center=(lx, ly, 0.0))
        for lx, ly in corner_points(-w / 2 + inset, -d / 2 + inset, w / 2 - inset, d / 2 - inset)
    ]
    if seat - z0 > 0.55:
        legs += _footrest(w, d, inset, z0 + 0.3)
    parts.add("frame", merge(legs), "wood")
    shell_t = float(p.get("shell_thickness", 0.05))
    radius = w / 2 - shell_t / 2
    arm_h = float(p.get("arm_height", 0.2))
    back_h = z0 + h - seat
    base = seat - 0.075
    sweep = float(p.get("sweep", 1.45))

    def crest(angle: float) -> float:
        return 0.075 + arm_h + (back_h - arm_h) * math.cos(angle / sweep * math.pi / 2) ** 1.5

    shell = curved_wall(
        radius, shell_t, sweep, base, crest, center=(0.0, d / 2 - shell_t / 2 - radius)
    )
    parts.add("shell", shell, p.get("shell_role", "upholstery"))
    parts.add(
        "seat",
        rounded_box(
            (w - 0.02, d - 0.03, 0.085),
            (0, -0.015, seat - 0.04),
            radius=0.035,
            segments=3,
            bulge=0.01,
            bulge_axes="+z",
        ),
        p.get("seat_role", "cushion"),
    )
    return parts.result()


def chair(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Oak dining chair or counter stool with upholstered or woven seat.

    ``style: "shell"`` builds an upholstered tub shell on tapered oak legs instead of the
    open rail back; a seat above 0.55 m adds a footrest ring either way.
    """
    if p.get("style") == "shell":
        return _shell_chair(size, p)
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    seat = z0 + float(p.get("seat_height", 0.46))
    leg_r = float(p.get("leg_radius", 0.017))
    inset = 0.03
    corners = [
        (-w / 2 + inset, -d / 2 + inset),
        (w / 2 - inset, -d / 2 + inset),
        (-w / 2 + inset, d / 2 - inset),
        (w / 2 - inset, d / 2 - inset),
    ]
    legs = []
    for index, (lx, ly) in enumerate(corners):
        top = seat - 0.04 if index < 2 else z0 + h - 0.05
        legs.append(
            lathe(
                [(leg_r * 0.75, z0), (leg_r, seat - 0.05), (leg_r, top)],
                segments=10,
                center=(lx, ly, 0.0),
            )
        )
    if seat - z0 > 0.55:
        legs += _footrest(w, d, inset, z0 + 0.3)
    legs.append(prism(rounded_rect(w - 0.02, d - 0.02, 0.03), seat - 0.06, seat - 0.035))
    parts.add("frame", merge(legs), "wood")
    parts.add(
        "seat",
        rounded_box(
            (w - 0.03, d - 0.04, 0.05),
            (0, -0.005, seat - 0.012),
            radius=0.02,
            segments=2,
            bulge=0.008,
            bulge_axes="+z",
        ),
        p.get("seat_role", "cushion"),
    )
    back_top = z0 + h - 0.02
    rail_h = float(p.get("back_rail", 0.12))
    segments = []
    for step in range(7):
        angle = -0.55 + 1.1 * step / 6
        segments.append((math.sin(angle) * w * 0.52, d / 2 - inset - (1 - math.cos(angle)) * 0.12))
    rail = []
    for (ax, ay), (bx, by) in zip(segments, segments[1:], strict=False):
        rail.append(
            transform(
                centered_box((math.dist((ax, ay), (bx, by)) + 0.012, 0.022, rail_h)),
                rotate=(0, 0, math.atan2(by - ay, bx - ax)),
                offset=((ax + bx) / 2, (ay + by) / 2, back_top - rail_h / 2),
            )
        )
    parts.add("back", merge(rail), "wood")
    return parts.result()


def bench(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Oak slab bench with optional cushion; ``style: "slats"`` gives a spa stool of spaced battens."""
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    top_t = float(p.get("top", 0.04))
    style = p.get("style", "slab")
    if style == "slats":
        count = int(p.get("slats", 5))
        gap = float(p.get("slat_gap", 0.012))
        slat_d = (d - gap * (count - 1)) / count
        top = []
        for index in range(count):
            y0 = -d / 2 + index * (slat_d + gap)
            top.append(
                rounded_box(
                    (w, slat_d, top_t),
                    (0, y0 + slat_d / 2, z0 + h - top_t / 2),
                    radius=0.005,
                    segments=1,
                )
            )
        for lx in (-w / 2 + 0.05, w / 2 - 0.05):
            top.append(box(lx - 0.016, -d / 2 + 0.02, z0, lx + 0.016, d / 2 - 0.02, z0 + h - top_t))
        top.append(box(-w / 2 + 0.066, -0.012, z0 + 0.08, w / 2 - 0.066, 0.012, z0 + 0.11))
        parts.add("top", merge(top), "wood")
        return parts.result()
    seat = z0 + h - (0.07 if p.get("cushion") else 0.0)
    parts.add(
        "top",
        rounded_box((w, d, top_t), (0, 0, seat - top_t / 2), radius=0.006, segments=1),
        "wood",
    )
    for lx in (-w / 2 + 0.08, w / 2 - 0.08):
        parts.add(
            "legs",
            box(lx - 0.02, -d / 2 + 0.03, z0, lx + 0.02, d / 2 - 0.03, seat - top_t),
            "wood",
        )
    if p.get("cushion"):
        parts.add(
            "cushion",
            rounded_box(
                (w - 0.04, d - 0.02, 0.06),
                (0, 0, seat + 0.03),
                radius=0.025,
                segments=2,
                bulge=0.008,
                bulge_axes="+z",
            ),
            "cushion",
        )
    return parts.result()
