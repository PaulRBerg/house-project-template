"""Table, bed, rug, curtain and panel templates."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from typing import Any

from .kit_geometry import (
    box,
    centered_box,
    ellipse,
    lathe,
    merge,
    prism,
    rod,
    rounded_box,
    rounded_rect,
    transform,
)
from .kit_geometry import curtain as curtain_sheet
from .kit_parts import (
    WARM_WHITE_K,
    Parts,
    Result,
    flutes,
    led_strip,
)

# --------------------------------------------------------------------------- tables and beds


def table(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Dining, coffee, side, console and desk tables with legs, pedestal or block base."""
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    top_t = float(p.get("top_thickness", 0.035))
    shape = p.get("shape", "rect")
    outline = (
        ellipse(w, d, 56)
        if shape in {"round", "oval"}
        else rounded_rect(w, d, float(p.get("corner_radius", 0.01)))
    )
    parts.add("top", prism(outline, z0 + h - top_t, z0 + h), p.get("top_role", "wood"))
    base = p.get("base", "legs")
    under = z0 + h - top_t
    if base == "legs":
        inset = float(p.get("leg_inset", 0.06))
        r = float(p.get("leg_radius", 0.022))
        spots = [
            (-w / 2 + inset, -d / 2 + inset),
            (w / 2 - inset, -d / 2 + inset),
            (-w / 2 + inset, d / 2 - inset),
            (w / 2 - inset, d / 2 - inset),
        ]
        if shape in {"round", "oval"}:
            spots = [
                (0.62 * w / 2 * math.cos(a), 0.62 * d / 2 * math.sin(a))
                for a in (0.785, 2.356, 3.927, 5.498)
            ]
        parts.add(
            "base",
            merge(
                [
                    lathe([(r * 0.7, z0), (r, under)], segments=12, center=(x, y, 0.0))
                    for x, y in spots
                ]
            ),
            "wood",
        )
    elif base == "pedestal":
        radius = float(p.get("pedestal_radius", min(w, d) * 0.16))
        parts.add(
            "base",
            lathe(
                [
                    (radius * 1.9, z0),
                    (radius * 1.9, z0 + 0.02),
                    (radius, z0 + 0.06),
                    (radius * 0.9, under - 0.03),
                    (radius * 1.3, under),
                ],
                segments=40,
            ),
            p.get("base_role", "wood"),
        )
    elif base == "block":
        inset = float(p.get("block_inset", 0.12))
        parts.add(
            "base",
            rounded_box(
                (w - 2 * inset, d - 2 * inset, h - top_t),
                (0, 0, z0 + (h - top_t) / 2),
                radius=0.01,
                segments=1,
            ),
            p.get("base_role", "wood"),
        )
    elif base == "frame":
        r = 0.012
        spots = [
            (-w / 2 + 0.03, -d / 2 + 0.03),
            (w / 2 - 0.03, -d / 2 + 0.03),
            (w / 2 - 0.03, d / 2 - 0.03),
            (-w / 2 + 0.03, d / 2 - 0.03),
        ]
        pieces = [rod((x, y, z0), (x, y, under), r) for x, y in spots]
        pieces += [
            rod((*spots[i], under - 0.012), (*spots[(i + 1) % 4], under - 0.012), r)
            for i in range(4)
        ]
        parts.add("base", merge(pieces), p.get("base_role", "metal"))
    return parts.result()


def bed(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Bed with frame, mattress, duvet, pillows, throw and headboard (head at +Y)."""
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    mw = float(p.get("mattress_width", 1.8))
    ml = float(p.get("mattress_length", 2.0))
    head_t = float(p.get("headboard_thickness", 0.1))
    frame_w = float(p.get("frame_width", mw + 0.12))
    frame_top = z0 + float(p.get("frame_height", 0.3))
    mt = float(p.get("mattress_thickness", 0.24))
    head_y = d / 2 - head_t
    foot_y = head_y - ml - float(p.get("frame_overhang", 0.06))
    if p.get("frame") == "floating":
        recess = 0.18
        parts.add(
            "plinth",
            box(
                -frame_w / 2 + recess,
                foot_y + recess,
                z0,
                frame_w / 2 - recess,
                head_y - 0.05,
                z0 + 0.12,
            ),
            "plinth",
        )
        parts.add(
            "frame",
            rounded_box(
                (frame_w, head_y - foot_y, frame_top - z0 - 0.12),
                (0, (foot_y + head_y) / 2, (z0 + 0.12 + frame_top) / 2),
                radius=0.012,
                segments=1,
            ),
            "frame",
        )
        for side in (-1, 1):
            parts.light(
                "underglow",
                "AREA",
                (side * (frame_w / 2 - recess - 0.02), (foot_y + head_y) / 2, z0 + 0.115),
                shape="RECTANGLE",
                size=0.03,
                size_y=head_y - foot_y - 0.3,
                energy=float(p.get("underglow_w", 3.0)),
                temperature=WARM_WHITE_K,
            )
        parts.add(
            "led",
            box(
                -frame_w / 2 + recess + 0.02,
                foot_y + recess - 0.01,
                z0 + 0.11,
                frame_w / 2 - recess - 0.02,
                foot_y + recess + 0.004,
                z0 + 0.118,
            ),
            "led",
        )
        parts.light(
            "underglow-foot",
            "AREA",
            (0, foot_y + recess, z0 + 0.115),
            shape="RECTANGLE",
            size=frame_w - 2 * recess,
            size_y=0.03,
            energy=float(p.get("underglow_w", 3.0)),
            temperature=WARM_WHITE_K,
        )
    else:
        parts.add(
            "frame",
            rounded_box(
                (frame_w, head_y - foot_y, frame_top - z0 - 0.06),
                (0, (foot_y + head_y) / 2, (z0 + 0.06 + frame_top) / 2),
                radius=0.03,
                segments=2,
            ),
            "frame",
        )
        parts.add(
            "plinth",
            box(
                -frame_w / 2 + 0.08, foot_y + 0.08, z0, frame_w / 2 - 0.08, head_y - 0.08, z0 + 0.06
            ),
            "plinth",
        )
    mattress_top = frame_top + mt
    my = head_y - ml / 2 - 0.02
    parts.add(
        "mattress",
        rounded_box((mw, ml, mt), (0, my, frame_top + mt / 2), radius=0.05, segments=2),
        "linen",
    )
    duvet_l = ml * float(p.get("duvet_cover", 0.74))
    duvet_y0 = head_y - 0.02 - ml - 0.03
    parts.add(
        "duvet",
        rounded_box(
            (mw + 0.08, duvet_l + 0.03, 0.34),
            (0, duvet_y0 + (duvet_l + 0.03) / 2, mattress_top + 0.07 - 0.17),
            radius=0.07,
            segments=3,
            bulge=0.025,
            bulge_axes="+z",
        ),
        "bedding",
    )
    parts.add(
        "duvet",
        rounded_box(
            (mw + 0.1, 0.3, 0.12),
            (0, duvet_y0 + duvet_l, mattress_top + 0.04),
            radius=0.05,
            segments=2,
            bulge=0.015,
            bulge_axes="+z",
        ),
        "bedding",
    )
    pillows = int(p.get("pillows", 2))
    pw = min(0.7, (mw - 0.1) / pillows)
    for index in range(pillows):
        px = -mw / 2 + 0.05 + pw * (index + 0.5)
        parts.add(
            "pillows",
            transform(
                rounded_box(
                    (pw - 0.04, 0.46, 0.13), radius=0.06, segments=2, bulge=0.035, bulge_axes="z"
                ),
                rotate=(0.12, 0, 0),
                offset=(px, head_y - 0.3, mattress_top + 0.06),
            ),
            "pillow",
        )
        parts.add(
            "pillows",
            transform(
                rounded_box(
                    (pw - 0.06, 0.14, 0.42), radius=0.06, segments=2, bulge=0.03, bulge_axes="y"
                ),
                rotate=(0.28, 0, 0),
                offset=(px, head_y - 0.12, mattress_top + 0.21),
            ),
            "pillow",
        )
    for index, cushion in enumerate(p.get("cushions", [])):
        cw = float(cushion.get("width", 0.5))
        parts.add(
            f"cushion-{index}",
            transform(
                rounded_box((cw, 0.14, 0.34), radius=0.05, segments=2, bulge=0.03, bulge_axes="y"),
                rotate=(0.36, 0, float(cushion.get("turn", 0.0))),
                offset=(float(cushion.get("x", 0.0)), head_y - 0.36, mattress_top + 0.2),
            ),
            cushion.get("role", "accent"),
        )
    if p.get("throw", True):
        ty = duvet_y0 + 0.28
        parts.add(
            "throw",
            rounded_box(
                (mw + 0.14, 0.52, 0.36),
                (0, ty, mattress_top + 0.095 - 0.18),
                radius=0.04,
                segments=2,
                bulge=0.01,
                bulge_axes="+z",
            ),
            "throw",
        )
    head = p.get("headboard", "upholstered")
    head_w = float(p.get("headboard_width", frame_w + 0.06))
    if head == "channels":
        count = int(p.get("channels", 7))
        cw = head_w / count
        for index in range(count):
            parts.add(
                "headboard",
                rounded_box(
                    (cw - 0.006, head_t, h - (frame_top - z0) + 0.1),
                    (
                        -head_w / 2 + cw * (index + 0.5),
                        d / 2 - head_t / 2,
                        (frame_top - 0.1 + z0 + h) / 2,
                    ),
                    radius=0.035,
                    segments=2,
                    bulge=0.012,
                    bulge_axes="-y",
                ),
                "headboard",
            )
        parts.add(
            "headboard-base",
            box(-head_w / 2, d / 2 - head_t + 0.02, z0, head_w / 2, d / 2, frame_top - 0.1),
            "plinth",
        )
    elif head == "upholstered":
        parts.add(
            "headboard",
            rounded_box(
                (head_w, head_t, h),
                (0, d / 2 - head_t / 2, 0),
                radius=0.04,
                segments=3,
                bulge=0.012,
                bulge_axes="-y",
            ),
            "headboard",
        )
    elif head == "panel":
        parts.add(
            "headboard",
            box(-head_w / 2, d / 2 - head_t, z0, head_w / 2, d / 2, z0 + h),
            "headboard",
        )
    return parts.result()


def rug(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    w, d, h = size
    parts = Parts()
    border = float(p.get("border", 0.0))
    outline = rounded_rect(w, d, float(p.get("corner_radius", 0.03)))
    if border > 0:
        parts.add(
            "border", prism(outline, -h / 2, h / 2 - 0.002), p.get("border_role", "rug_border")
        )
        inner = rounded_rect(w - 2 * border, d - 2 * border, 0.02)
        parts.add("field", prism(inner, -h / 2 + 0.001, h / 2), "rug")
    else:
        parts.add("field", prism(outline, -h / 2, h / 2), "rug")
    return parts.result()


# Curtain pocket liner board and the reveal that keeps it off the ceiling hole's faces.
POCKET_LINER_M = 0.012
POCKET_REVEAL_M = 0.002
TRACK_HEIGHT_M = 0.03
TRACK_CLEARANCE_M = 0.005
# Retracted blackout roller: cassette depth (Y) and height (Z); channel width (X) and depth (Y).
ROLLER_CASSETTE_M = (0.06, 0.07)
ROLLER_CHANNEL_M = (0.025, 0.03)


def curtain(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Ceiling-track drapes: ``panels`` are ``[x0, x1]`` spans per layer (sheer, dimout, blackout).

    ``pocket: {"depth_m"}`` recesses the tracks into a plaster-lined ceiling pocket over the
    whole envelope footprint, lit by a warm LED strip; the architecture cuts the matching
    ceiling hole. ``roller`` (``true`` or ``{"bottom_m"}``) adds a retracted blackout-roller
    cassette on the window (−Y) side of the pocket and slim side channels from the floor, or
    from ``bottom_m`` with a bottom channel between them, up to the envelope top.
    """
    w, d, h = size
    parts = Parts()
    x0, x1, y0, y1, top = -w / 2, w / 2, -d / 2, d / 2, h / 2
    pocket = p.get("pocket")
    if pocket:
        outer, inner = POCKET_REVEAL_M, POCKET_REVEAL_M + POCKET_LINER_M
        z1 = h / 2 + float(pocket["depth_m"])
        x0, x1, y0, y1 = -w / 2 + inner, w / 2 - inner, -d / 2 + inner, d / 2 - inner
        top = z1 - POCKET_LINER_M
        parts.add(
            "pocket",
            merge(
                [
                    box(-w / 2 + outer, -d / 2 + outer, h / 2, w / 2 - outer, y0, z1),
                    box(-w / 2 + outer, y1, h / 2, w / 2 - outer, d / 2 - outer, z1),
                    box(-w / 2 + outer, y0, h / 2, x0, y1, z1),
                    box(x1, y0, h / 2, w / 2 - outer, y1, z1),
                    box(x0, y0, top, x1, y1, z1),
                ]
            ),
            "pocket",
        )
        led_strip(parts, "pocket-led", x0 + 0.02, x1 - 0.02, y1 - 0.012, top - 0.006)
    roller = p.get("roller")
    if roller:
        if not pocket:
            raise ValueError("a curtain roller retracts into its ceiling pocket")
        cassette_d, cassette_h = ROLLER_CASSETTE_M
        parts.add(
            "roller-cassette", box(x0, y0, top - cassette_h, x1, y0 + cassette_d, top), "metal"
        )
        channel_w, channel_d = ROLLER_CHANNEL_M
        y = y0 + cassette_d / 2
        bottom = -h / 2 + (float(roller["bottom_m"]) if isinstance(roller, Mapping) else 0.0)
        channels = [
            box(-w / 2, y - channel_d / 2, bottom, -w / 2 + channel_w, y + channel_d / 2, h / 2),
            box(w / 2 - channel_w, y - channel_d / 2, bottom, w / 2, y + channel_d / 2, h / 2),
        ]
        if bottom > -h / 2:
            channels.append(
                box(
                    -w / 2 + channel_w,
                    y - channel_d / 2,
                    bottom,
                    w / 2 - channel_w,
                    y + channel_d / 2,
                    bottom + channel_w,
                )
            )
        parts.add("roller-channels", merge(channels), "trim")
        y0 += cassette_d
    sheet_top = top - TRACK_HEIGHT_M - TRACK_CLEARANCE_M
    layers = p.get("layers") or [{"role": "sheer"}]
    for index, layer in enumerate(layers):
        depth = float(layer.get("depth", min(0.09, (y1 - y0) / len(layers))))
        y = (
            y0 + depth / 2 + index * (y1 - y0 - depth) / (len(layers) - 1)
            if len(layers) > 1
            else (y0 + y1) / 2
        )
        parts.add("track", box(x0, y - 0.015, top - TRACK_HEIGHT_M, x1, y + 0.015, top), "track")
        for px0, px1 in layer.get("panels", [[x0, x1]]):
            gathered = px1 - px0 < 0.8 * w
            sheet = curtain_sheet(
                px1 - px0,
                sheet_top + h / 2,
                depth=depth,
                pleat=0.09 if gathered else 0.15,
                phase=rng.uniform(0, math.pi),
            )
            parts.add(
                f"layer-{index}",
                transform(sheet, offset=((px0 + px1) / 2, y, (sheet_top - h / 2) / 2)),
                layer.get("role", "sheer"),
            )
    return parts.result()


def panel(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Wall finish: flat sheet (wallpaper, limewash), vertical slats or reeds.

    ``slats`` stand square battens on a 6 mm backing; ``flutes`` stand half-round reeds of
    the envelope depth on it. Both take ``backing_role`` for the board between them.
    """
    w, d, h = size
    parts = Parts()
    style = p.get("style", "flat")
    if style in {"slats", "flutes"}:
        parts.add(
            "backing",
            box(-w / 2, d / 2 - 0.006, -h / 2, w / 2, d / 2, h / 2),
            p.get("backing_role", "plinth"),
        )
    if style == "flutes":
        parts.add(
            "reeds",
            flutes(
                -w / 2,
                w / 2,
                -h / 2,
                h / 2,
                d / 2 - 0.006,
                pitch=float(p.get("pitch", 0.03)),
                depth=d - 0.006,
            ),
            "wood",
        )
    elif style == "slats":
        pitch = float(p.get("pitch", 0.06))
        slat = float(p.get("slat", 0.035))
        x = -w / 2
        slats = []
        while x + slat <= w / 2 + 1e-6:
            slats.append(box(x, -d / 2, -h / 2, x + slat, d / 2 - 0.006, h / 2))
            x += pitch
        parts.add("slats", merge(slats), "wood")
    else:
        parts.add("sheet", centered_box((w, d, h)), "panel")
    return parts.result()
