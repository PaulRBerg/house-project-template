"""Potted plants with seeded phyllotaxis foliage."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from typing import Any

from .kit_geometry import (
    cylinder,
    lathe,
    leaf,
    merge,
    rod,
    transform,
)
from .kit_parts import Parts, Result

_SPECIES: dict[str, dict[str, Any]] = {
    "fiddle": {
        "leaf": (0.26, 0.17),
        "count": 34,
        "canopy": (0.45, 1.0),
        "trunk": True,
        "spread": 0.9,
        "curl": 0.25,
    },
    "olive": {
        "leaf": (0.07, 0.016),
        "count": 520,
        "canopy": (0.35, 1.0),
        "trunk": True,
        "spread": 1.0,
        "curl": 0.1,
        "branches": 7,
    },
    "grass": {
        "leaf": (1.0, 0.014),
        "count": 150,
        "canopy": (0.0, 1.0),
        "trunk": False,
        "spread": 0.35,
        "curl": 0.3,
    },
    "rubber": {
        "leaf": (0.22, 0.1),
        "count": 28,
        "canopy": (0.3, 1.0),
        "trunk": True,
        "spread": 0.7,
        "curl": 0.15,
    },
    "monstera": {
        "leaf": (0.34, 0.3),
        "count": 14,
        "canopy": (0.1, 1.0),
        "trunk": False,
        "spread": 1.0,
        "curl": 0.35,
    },
    "herb": {
        "leaf": (0.045, 0.028),
        "count": 70,
        "canopy": (0.1, 1.0),
        "trunk": False,
        "spread": 1.0,
        "curl": 0.3,
    },
    "trailing": {
        "leaf": (0.07, 0.055),
        "count": 90,
        "canopy": (0.0, 1.0),
        "trunk": False,
        "spread": 1.0,
        "curl": 0.2,
    },
}


def plant(size: Sequence[float], p: Mapping[str, Any], rng: random.Random) -> Result:
    """Potted plant with seeded phyllotaxis; the envelope includes pot and foliage."""
    w, d, h = size
    parts = Parts()
    z0 = -h / 2
    pot_h = float(p.get("pot_height", min(0.42, h * 0.3)))
    pot_r = float(p.get("pot_radius", min(w, d) * 0.28))
    style = p.get("pot", "tapered")
    profile = {
        "tapered": [(pot_r * 0.72, 0), (pot_r, 1.0), (pot_r * 0.94, 1.0)],
        "round": [
            (pot_r * 0.6, 0),
            (pot_r * 0.95, 0.35),
            (pot_r, 0.7),
            (pot_r * 0.86, 1.0),
            (pot_r * 0.8, 1.0),
        ],
        "cylinder": [(pot_r, 0), (pot_r, 1.0), (pot_r * 0.93, 1.0)],
    }[style]
    parts.add(
        "pot",
        lathe([(r, z0 + t * pot_h) for r, t in profile], segments=36),
        p.get("pot_role", "pot"),
    )
    parts.add(
        "soil", cylinder(pot_r * 0.92, z0 + pot_h - 0.04, z0 + pot_h - 0.03, segments=24), "soil"
    )
    species = _SPECIES[p.get("species", "fiddle")]
    top = h / 2
    base = z0 + pot_h - 0.035
    height = top - base
    length, width = species["leaf"]
    scale = float(p.get("leaf_scale", 1.0))
    length, width = length * scale, width * scale
    stems = []
    leaves: dict[str, list[dict]] = {"leaf": [], "leaf2": []}
    radius = min(w, d) / 2
    kind = p.get("species", "fiddle")
    if species["trunk"]:
        trunk_top = base + height * species["canopy"][0] + 0.05
        lean = rng.uniform(-0.04, 0.04)
        stems.append(rod((0, 0, base), (lean, 0, trunk_top), 0.012 if kind != "olive" else 0.022))
    if kind == "olive":
        canopy = max(radius - length, 0.0)
        tips = []
        for index in range(species["branches"]):
            angle = index * 2.4 + rng.uniform(-0.3, 0.3)
            reach = canopy * rng.uniform(0.5, 0.75)
            tip = (
                math.cos(angle) * reach,
                math.sin(angle) * reach,
                base + height * rng.uniform(0.62, 0.95),
            )
            stems.append(rod((lean, 0, trunk_top - 0.05), tip, 0.009))
            tips.append(tip)
        for index in range(species["count"]):
            tip = tips[index % len(tips)]
            spread = canopy * 0.25
            at = (
                tip[0] + rng.uniform(-spread, spread),
                tip[1] + rng.uniform(-spread, spread),
                tip[2] + rng.uniform(-0.18, 0.12),
            )
            mesh = transform(
                leaf(length, width, curl=0.05, fold=0.1, steps=3),
                rotate=(rng.uniform(-1.2, 0.4), rng.uniform(-0.5, 0.5), rng.uniform(0, 6.28)),
                offset=at,
            )
            leaves["leaf" if rng.random() < 0.6 else "leaf2"].append(mesh)
    else:
        golden = math.pi * (3 - math.sqrt(5))
        count = species["count"]
        for index in range(count):
            t = index / max(count - 1, 1)
            lo, hi = species["canopy"]
            z = base + height * (lo + (hi - lo) * t) - length * 0.3
            angle = index * golden + rng.uniform(-0.2, 0.2)
            if kind == "grass":
                # Ornamental grass: a dense clump of fine blades arching outward.
                ring = radius * species["spread"] * math.sqrt(rng.random())
                at = (math.cos(angle) * ring, math.sin(angle) * ring, base)
                lean = rng.uniform(0.05, 0.6)
                curl = species["curl"] * lean
                # The tip reaches leaf_len * (sin(lean) + curl * cos(lean)) outward; keep it
                # inside the envelope radius.
                leaf_len = min(
                    height * rng.uniform(0.55, 1.0) / (1 + curl),
                    (radius - ring) / (math.sin(lean) + curl * math.cos(lean)),
                )
                mesh = transform(
                    leaf(
                        leaf_len,
                        width,
                        shape=lambda s: (1 - s) ** 0.7,
                        fold=0.2,
                        curl=curl,
                        steps=6,
                    ),
                    rotate=(math.pi / 2 - lean, 0, angle - math.pi / 2),
                    offset=at,
                )
            elif kind in {"herb", "trailing", "monstera"}:
                # Leaves extend outward from their base, so keep the base inside radius - length.
                limit = max(radius - length, 0.0) * species["spread"]
                reach = limit * (0.35 + 0.65 * math.sqrt(rng.random()))
                droop = -rng.uniform(0.1, 0.5) if kind == "trailing" else 0
                zz = base + (
                    height * rng.uniform(0.15, 1.0)
                    if kind != "trailing"
                    else rng.uniform(-pot_h * 0.8, height * 0.5)
                )
                at = (math.cos(angle) * reach, math.sin(angle) * reach, zz)
                if kind == "monstera":
                    stems.append(rod((0, 0, base), at, 0.006))
                mesh = transform(
                    leaf(length, width, curl=species["curl"], fold=0.15),
                    rotate=(rng.uniform(-0.4, 0.3) + droop, 0, angle - math.pi / 2),
                    offset=at,
                )
            else:
                trunk_x = lean * (z - base) / max(height, 0.01) if species["trunk"] else 0
                reach = 0.02
                at = (trunk_x + math.cos(angle) * reach, math.sin(angle) * reach, z)
                pitch = rng.uniform(-0.25, 0.35) - 0.5 * t
                mesh = transform(
                    leaf(length * rng.uniform(0.8, 1.1), width, curl=species["curl"], fold=0.18),
                    rotate=(pitch, 0, angle - math.pi / 2),
                    offset=at,
                )
            leaves["leaf" if rng.random() < 0.55 else "leaf2"].append(mesh)
    if stems:
        parts.add("stems", merge(stems), "stem")
    for role, items in leaves.items():
        if items:
            parts.add(role, merge(items), role)
    return parts.result()
