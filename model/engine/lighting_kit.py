"""Lighting fixtures: pendants, lamps, sconces, LED lines and downlights."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from typing import Any

from .kit_geometry import (
    box,
    centered_box,
    cylinder,
    dome_profile,
    lathe,
    merge,
    rod,
    rounded_box,
    transform,
)
from .kit_parts import (
    NEUTRAL_WARM_K,
    WARM_WHITE_K,
    Parts,
    Result,
    vessel_mesh,
)

# --------------------------------------------------------------------------- lighting


def _shade(
    radius_bottom: float, radius_top: float, z0: float, z1: float, thickness: float = 0.004
) -> dict:
    return lathe(
        [
            (radius_bottom, z0),
            (radius_top, z1),
            (radius_top - thickness, z1),
            (radius_bottom - thickness, z0),
        ],
        segments=40,
        cap_bottom=False,
        cap_top=False,
    )


def pendant(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Ceiling pendant with a translucent ``dome`` shade or a ``linear`` LED bar."""
    w, d, h = size
    parts = Parts()
    top = h / 2
    shape = p.get("shape", "dome")
    shade_h = float(p.get("shade_height", 0.22 if shape != "linear" else 0.05))
    bottom = -h / 2
    parts.add("canopy", cylinder(0.05, top - 0.02, top, segments=24), "metal")
    energy = float(p.get("energy", 25.0))
    temperature = float(p.get("temperature", WARM_WHITE_K))
    if shape == "linear":
        parts.add(
            "cord",
            merge(
                [
                    rod((x, 0, bottom + shade_h), (x, 0, top - 0.02), 0.0015)
                    for x in (-w / 2 + 0.1, w / 2 - 0.1)
                ]
            ),
            "metal",
        )
        parts.add(
            "shade",
            rounded_box((w, d, shade_h), (0, 0, bottom + shade_h / 2), radius=0.01, segments=1),
            p.get("shade_role", "metal"),
        )
        parts.add(
            "diffuser",
            box(
                -w / 2 + 0.02,
                -d / 2 + 0.01,
                bottom - 0.001,
                w / 2 - 0.02,
                d / 2 - 0.01,
                bottom + 0.002,
            ),
            "led",
        )
        parts.light(
            "down",
            "AREA",
            (0, 0, bottom - 0.004),
            shape="RECTANGLE",
            size=w - 0.04,
            size_y=max(d - 0.02, 0.02),
            energy=energy,
            temperature=temperature,
        )
        return parts.result()
    radius = w / 2
    parts.add("cord", rod((0, 0, bottom + shade_h), (0, 0, top - 0.02), 0.002), "metal")
    profile = dome_profile(radius, bottom, shade_h, 0.02)
    inner = [(r - 0.004, z - 0.004) for r, z in reversed(profile)]
    parts.add(
        "shade",
        lathe(profile + inner, segments=48, cap_bottom=False, cap_top=False),
        p.get("shade_role", "ceramic"),
        shadow=False,
    )
    parts.light(
        "glow",
        "SPOT",
        (0, 0, bottom + shade_h * 0.45),
        spot_size=math.radians(float(p.get("beam", 110))),
        spot_blend=0.8,
        radius=0.04,
        energy=energy,
        temperature=temperature,
    )
    return parts.result()


def floor_lamp(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Linen drum floor lamp, an arched reading lamp whose hood sits over −Y, or a lantern.

    ``lantern`` is a tall paper ovoid on a slim stem and disc base, glowing from within;
    ``shade_height`` sets the ovoid and the shade takes ``shade_role``.
    """
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    energy = float(p.get("energy", 18.0))
    temperature = float(p.get("temperature", WARM_WHITE_K))
    if p.get("style") == "lantern":
        shade_h = float(p.get("shade_height", h * 0.55))
        radius = min(w, d) / 2
        shade_z = z0 + h - shade_h
        parts.add(
            "base",
            lathe(
                [(radius * 0.55, z0), (radius * 0.55, z0 + 0.016), (0.02, z0 + 0.028)], segments=32
            ),
            "metal",
        )
        parts.add("stem", rod((0, 0, z0 + 0.02), (0, 0, shade_z + 0.04), 0.008), "metal")
        profile = [
            (max(radius * math.sin(math.pi * t) ** 0.6, 0.03), shade_z + shade_h * t)
            for t in [0.03 + 0.94 * i / 14 for i in range(15)]
        ]
        parts.add(
            "shade",
            lathe(profile, segments=40, cap_bottom=False, cap_top=False),
            p.get("shade_role", "shade"),
            shadow=False,
        )
        parts.light(
            "glow",
            "POINT",
            (0, 0, shade_z + shade_h * 0.5),
            radius=radius * 0.5,
            energy=energy,
            temperature=temperature,
        )
        return parts.result()
    if p.get("style", "drum") == "reading":
        base_r = 0.14
        parts.add(
            "base",
            lathe(
                [(base_r, z0), (base_r, z0 + 0.018), (0.02, z0 + 0.03)],
                segments=32,
                center=(0, d / 2 - base_r, 0),
            ),
            "metal",
        )
        stem = [rod((0, d / 2 - base_r, z0 + 0.02), (0, d / 2 - base_r, z0 + h - 0.22), 0.009)]
        arc = []
        for step in range(8):
            a0, a1 = step / 8 * math.pi / 2, (step + 1) / 8 * math.pi / 2
            r = d - base_r - 0.12
            p0 = (0, d / 2 - base_r - r * math.sin(a0), z0 + h - 0.22 + 0.15 * math.sin(a0 * 2))
            p1 = (0, d / 2 - base_r - r * math.sin(a1), z0 + h - 0.22 + 0.15 * math.sin(a1 * 2))
            arc.append(rod(p0, p1, 0.007))
        parts.add("stem", merge(stem + arc), "metal")
        hood_y = -d / 2 + 0.12
        parts.add(
            "shade",
            transform(_shade(0.12, 0.05, 0, 0.12), offset=(0, hood_y, z0 + h - 0.36)),
            p.get("shade_role", "metal"),
        )
        parts.add("glow", cylinder(0.1, z0 + h - 0.358, z0 + h - 0.355, center=(0, hood_y)), "glow")
        parts.light(
            "reading",
            "SPOT",
            (0, hood_y, z0 + h - 0.3),
            spot_size=math.radians(70),
            spot_blend=0.6,
            radius=0.03,
            energy=energy,
            temperature=temperature,
        )
        return parts.result()
    shade_h = float(p.get("shade_height", 0.34))
    radius = w / 2
    parts.add(
        "base", lathe([(0.15, z0), (0.15, z0 + 0.02), (0.03, z0 + 0.035)], segments=32), "metal"
    )
    parts.add("stem", rod((0, 0, z0 + 0.03), (0, 0, z0 + h - shade_h * 0.4), 0.01), "metal")
    parts.add(
        "shade",
        _shade(radius, radius * float(p.get("taper", 0.92)), z0 + h - shade_h, z0 + h),
        "shade",
        shadow=False,
    )
    parts.light(
        "glow",
        "POINT",
        (0, 0, z0 + h - shade_h * 0.5),
        radius=radius * 0.5,
        energy=energy,
        temperature=temperature,
    )
    return parts.result()


def table_lamp(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    shade_h = float(p.get("shade_height", h * 0.42))
    base_h = h - shade_h * 0.8
    base_r = float(p.get("base_radius", w * 0.28))
    style = p.get("style", "ceramic")
    if style == "mushroom":
        parts.add(
            "base",
            lathe(
                [(base_r, z0), (base_r * 0.6, z0 + 0.03), (base_r * 0.35, z0 + base_h * 0.9)],
                segments=32,
            ),
            "ceramic",
        )
        dome = dome_profile(w / 2, z0 + base_h * 0.85, shade_h, 0.001)
        parts.add(
            "shade",
            lathe([(w / 2 - 0.005, z0 + base_h * 0.85)] + dome, segments=40),
            p.get("shade_role", "glow"),
            shadow=False,
        )
    else:
        parts.add("base", vessel_mesh(0, 0, z0, base_r, base_h, p.get("vessel", "bud")), "ceramic")
        parts.add(
            "shade", _shade(w / 2, w / 2 * 0.82, z0 + h - shade_h, z0 + h), "shade", shadow=False
        )
    parts.light(
        "glow",
        "POINT",
        (0, 0, z0 + h - shade_h * 0.55),
        radius=0.05,
        energy=float(p.get("energy", 8.0)),
        temperature=float(p.get("temperature", WARM_WHITE_K)),
    )
    return parts.result()


def sconce(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Wall light on the +Y wall: ``tube`` (up/down glow) or ``arm`` (swing arm)."""
    w, d, h = size
    parts = Parts()
    energy = float(p.get("energy", 6.0))
    temperature = float(p.get("temperature", WARM_WHITE_K))
    style = p.get("style", "tube")
    parts.add(
        "plate",
        rounded_box(
            (min(w, 0.1), 0.012, min(h, 0.14)),
            (0, d / 2 - 0.006, 0 if style != "arm" else -h / 2 + 0.08),
            radius=0.004,
            segments=1,
        ),
        "metal",
    )
    if style == "tube":
        r = min(w, d) / 2 - 0.004
        parts.add("arm", rod((0, d / 2 - 0.01, 0), (0, d / 2 - 0.05, 0), 0.008), "metal")
        parts.add(
            "tube",
            cylinder(r, -h / 2 + 0.02, h / 2 - 0.02, center=(0, -d / 2 + r + 0.004)),
            "glow",
            shadow=False,
        )
        parts.add(
            "caps",
            merge(
                [
                    cylinder(r + 0.002, -h / 2, -h / 2 + 0.02, center=(0, -d / 2 + r + 0.004)),
                    cylinder(r + 0.002, h / 2 - 0.02, h / 2, center=(0, -d / 2 + r + 0.004)),
                ]
            ),
            "metal",
        )
        parts.light(
            "glow",
            "POINT",
            (0, -d / 2 + r + 0.004, 0),
            radius=r,
            energy=energy,
            temperature=temperature,
        )
    else:
        parts.add(
            "arm",
            merge(
                [
                    rod((0, d / 2 - 0.01, -h / 2 + 0.08), (0, -d / 2 + 0.1, -h / 2 + 0.08), 0.006),
                    rod((0, -d / 2 + 0.1, -h / 2 + 0.08), (0, -d / 2 + 0.1, h / 2 - 0.12), 0.006),
                ]
            ),
            "metal",
        )
        parts.add(
            "shade",
            _shade(0.075, 0.06, h / 2 - 0.16, h / 2),
            p.get("shade_role", "shade"),
            shadow=False,
        )
        parts.light(
            "glow",
            "POINT",
            (0, -d / 2 + 0.1, h / 2 - 0.09),
            radius=0.04,
            energy=energy,
            temperature=temperature,
        )
    return parts.result()


def led_line(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Linear LED cove, curtain pocket or step light along X.

    ``facing`` is the emitting direction: ``down`` or ``up``.
    ``concealed`` coves (ceiling pockets, slots) show only a dark shadow reveal.
    """
    w, d, h = size
    parts = Parts()
    facing = p.get("facing", "down")
    energy = float(p.get("w_per_m", 8.0)) * w
    temperature = float(p.get("temperature", WARM_WHITE_K))
    concealed = bool(p.get("concealed", False))
    if concealed:
        parts.add("slot", centered_box((w, d, 0.002)), "plinth")
    else:
        parts.add("profile", centered_box((w, d, h)), p.get("profile_role", "track"))
    z = -h / 2 - 0.001 if facing == "down" else h / 2 + 0.001
    if not concealed:
        parts.add(
            "diffuser",
            box(-w / 2, -d / 2 + 0.003, z - 0.002, w / 2, d / 2 - 0.003, z + 0.002),
            "led",
        )
    parts.light(
        "line",
        "AREA",
        (0, 0, z + (-0.003 if facing == "down" else 0.003)),
        rotation=(0.0, 0.0, 0.0) if facing == "down" else (math.pi, 0.0, 0.0),
        shape="RECTANGLE",
        size=w,
        size_y=max(d - 0.006, 0.01),
        energy=energy,
        temperature=temperature,
        spread=math.radians(float(p.get("spread", 150))),
    )
    return parts.result()


def downlight(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Recessed trimless downlight (or wall-grazing accent when ``tilt`` is set)."""
    w, d, h = size
    parts = Parts()
    parts.add("trim", cylinder(w / 2, -h / 2, h / 2, segments=24), "trim")
    parts.add(
        "lens",
        cylinder(w / 2 - 0.012, -h / 2 - 0.001, -h / 2 + 0.001, segments=24),
        "glow",
        shadow=False,
    )
    tilt = math.radians(float(p.get("tilt", 0.0)))
    parts.light(
        "spot",
        "SPOT",
        (0, 0, -h / 2 - 0.01),
        rotation=(-tilt, 0.0, 0.0),
        spot_size=math.radians(float(p.get("beam", 50))),
        spot_blend=float(p.get("blend", 0.6)),
        radius=0.02,
        energy=float(p.get("energy", 12.0)),
        temperature=float(p.get("temperature", NEUTRAL_WARM_K)),
    )
    return parts.result()
