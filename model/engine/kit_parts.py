"""Shared part collection, LED strips and vessel profiles for the parametric kits.

Templates receive the furnishing's fixed envelope ``(width, depth, height)`` and
return parts and optional light emitters in a local frame whose origin is the
envelope centre. The front faces local −Y and the floor is ``z = −height / 2``.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

from .kit_geometry import (
    box,
    lathe,
    merge,
    prism,
)

Part = dict[str, Any]
Light = dict[str, Any]
Result = tuple[list[Part], list[Light]]

WARM_WHITE_K = 2700
NEUTRAL_WARM_K = 3000
BOOK_ROLE_COUNT = 5


def book_role(rng: random.Random) -> str:
    """Pick one of the ``book0``…``book4`` cloth roles."""
    return f"book{rng.randint(0, BOOK_ROLE_COUNT - 1)}"


class Parts:
    """Collect meshes per role so a template yields one object per material."""

    def __init__(self) -> None:
        self.meshes: dict[tuple[str, str], list[dict]] = {}
        self.order: list[tuple[str, str]] = []
        self.lights: list[Light] = []
        self.shadowless: set[tuple[str, str]] = set()

    def add(self, name: str, mesh: dict, role: str, *, shadow: bool = True) -> None:
        """Collect a mesh; translucent shades pass ``shadow=False`` so emitters inside glow through."""
        key = (name, role)
        if key not in self.meshes:
            self.meshes[key] = []
            self.order.append(key)
        self.meshes[key].append(mesh)
        if not shadow:
            self.shadowless.add(key)

    def light(self, name: str, kind: str, position: Sequence[float], **spec: Any) -> None:
        self.lights.append({"name": name, "type": kind, "position": list(position), **spec})

    def result(self) -> Result:
        parts = []
        for name, role in self.order:
            items = self.meshes[(name, role)]
            mesh = items[0] if len(items) == 1 else merge(items)
            parts.append(
                {
                    "name": name,
                    "role": role,
                    "mesh": mesh,
                    "smooth": "normals" in mesh,
                    "shadow": (name, role) not in self.shadowless,
                }
            )
        return parts, self.lights


def led_strip(
    parts: Parts,
    name: str,
    x0: float,
    x1: float,
    y: float,
    z: float,
    *,
    energy_per_m: float = 6.0,
) -> None:
    """Downward-facing diffused LED profile with a matching rectangular area light."""
    length = x1 - x0
    width = 0.012
    parts.add(name, box(x0, y - width / 2, z - 0.004, x1, y + width / 2, z + 0.004), "led")
    parts.light(
        name,
        "AREA",
        ((x0 + x1) / 2, y, z - 0.006),
        rotation=(0.0, 0.0, 0.0),
        shape="RECTANGLE",
        size=max(length, 0.02),
        size_y=0.03,
        energy=energy_per_m * length,
        temperature=WARM_WHITE_K,
    )


def flutes(
    x0: float,
    x1: float,
    z0: float,
    z1: float,
    face_y: float,
    *,
    pitch: float = 0.03,
    depth: float = 0.008,
) -> dict:
    """Vertical half-round reeds standing on the ``face_y`` plane and bulging toward −Y.

    Reeds fill ``[x0, x1]`` at ``pitch`` centres; fluted joinery fronts and ribbed wall
    panels share this one profile so grazing light reads the same everywhere.
    """
    count = max(1, round((x1 - x0) / pitch))
    width = (x1 - x0) / count
    reeds = []
    for index in range(count):
        cx = x0 + width * (index + 0.5)
        outline = [
            (cx + width / 2 * math.cos(angle), face_y + depth * math.sin(angle))
            for angle in (math.pi + math.pi * step / 8 for step in range(9))
        ]
        reeds.append(prism(outline, z0, z1))
    return merge(reeds)


VESSEL_PROFILES: dict[str, list[tuple[float, float]]] = {
    "bud": [
        (0.55, 0),
        (0.9, 0.12),
        (1.0, 0.4),
        (0.7, 0.75),
        (0.35, 0.88),
        (0.4, 1.0),
        (0.3, 1.0),
    ],
    "jar": [(0.8, 0), (1.0, 0.1), (1.0, 0.85), (0.8, 1.0), (0.7, 1.0)],
    "bowl": [
        (0.45, 0),
        (0.8, 0.25),
        (1.0, 0.7),
        (1.0, 1.0),
        (0.9, 1.0),
        (0.85, 0.6),
        (0.4, 0.2),
    ],
    "amphora": [
        (0.45, 0),
        (0.95, 0.3),
        (1.0, 0.45),
        (0.6, 0.8),
        (0.45, 0.92),
        (0.55, 1.0),
        (0.45, 1.0),
    ],
    "cylinder": [(1.0, 0), (1.0, 1.0), (0.92, 1.0)],
}


def vessel_mesh(x: float, y: float, z: float, radius: float, height: float, kind: str) -> dict:
    profile = [(r * radius, z + t * height) for r, t in VESSEL_PROFILES[kind]]
    return lathe(profile, segments=24, center=(x, y, 0.0))
