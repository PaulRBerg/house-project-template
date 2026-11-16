"""Exterior wall facade finishes: base skins, bands, accent panels, opening surrounds and ledgestone.

Every skin is a ``facade`` mesh owned by its exterior wall, so the exported finished envelope
measures it. Rectangles are ``(u0, u1, z0, z1)``: along the wall from its start and above the
level elevation.
"""

from __future__ import annotations

import math
import random

from .architecture import wall_cells
from .geometry import clip_rectangle, subtract_rectangles, wall_box
from .kit_geometry import merge
from .mesh_descriptors import EXTERIOR_DETAILS
from .transforms import wall_frame

# Glazed openings that may carry a lined exterior reveal and a flush surround band.
REVEAL_KINDS = frozenset({"window", "double", "terrace"})
# Outer-face distance proud of the wall face, and body depth behind that outer face.
BASE_SKIN_PROUD_M = BASE_SKIN_DEPTH_M = 0.002
BAND_PROUD_M = 0.003
SURROUND_PROUD_M = 0.004
SURROUND_DEPTH_M = 0.012
STONE_DEFAULTS = {"joint_m": 0.005, "depth_m": 0.012, "proud_m": 0.004}
# Pieces thinner than this along either axis are clipping slivers and are skipped.
SLIVER_M = 1e-4


def _skin_mesh(wall, rect, z, proud, depth):
    a, b, bottom, top = rect
    face = wall["thickness"] / 2 + proud - depth / 2
    return wall_box(wall, a, b, wall["exterior_side"] * face, depth, z + bottom, z + top)


def _slats(rect, start, pitch, width):
    """Vertical slats ``width`` wide every ``pitch`` from ``start``, clipped to ``rect``."""
    if not pitch:
        return [rect]
    a, b, bottom, top = rect
    slats = []
    left = start + math.floor((a - start) / pitch) * pitch
    while left < b:
        lo, hi = max(a, left), min(b, left + width)
        if hi - lo > SLIVER_M:
            slats.append((lo, hi, bottom, top))
        left += pitch
    return slats


def _courses(wall, stone, length, top):
    """Global course rows ``(z0, z1, [(u0, u1, material_id)])`` from local z 0 to ``top``."""
    lo, hi = stone["length_range_m"]
    joint = stone["joint_m"]
    if not 0 < lo <= hi or joint >= min(lo, *stone["course_heights_m"]):
        raise ValueError(f"{wall['id']}: ledgestone joints or lengths leave no stone")
    rng = random.Random(stone.get("seed", wall["id"]))
    rows, z = [], 0.0
    while z < top:
        height = rng.choice(stone["course_heights_m"])
        u, stones = -rng.uniform(0, hi), []
        while u < length:
            run = rng.uniform(lo, hi)
            stones.append((u, u + run - joint, rng.choice(stone["material_ids"])))
            u += run
        rows.append((z, z + height - joint, stones))
        z += height
    return rows


def exterior_finish(builder, wall, openings, height):
    """Build one exterior wall's facade skins from its ``finish``."""
    finish = wall["finish"]
    z = builder.levels[wall["level_id"]]["elevation_m"]
    length = wall_frame(wall)[2]
    extend = finish.get("extend_top_m", 0)
    # A plain number raises the whole wall top; a list raises only its ``span_m`` ranges.
    rises = (
        [{"span_m": (0, length), "height_m": extend}]
        if isinstance(extend, (int, float))
        else extend
    )

    def skin(child, rect, proud, depth, material, slot, properties=None):
        builder.add(
            wall,
            child,
            _skin_mesh(wall, rect, z, proud, depth),
            EXTERIOR_DETAILS,
            material=material,
            kind="facade",
            slot=slot,
            properties=properties,
        )

    cells = []
    for cell, band, lo, hi, bottom, top in wall_cells(wall, openings, height):
        if not math.isclose(top, height):
            cells.append((cell, band, (lo, hi, bottom, top)))
            continue
        # A rise covering the whole cell lifts its top; a partial one adds a cell above it.
        lift = max(
            (r["height_m"] for r in rises if r["span_m"][0] <= lo and hi <= r["span_m"][1]),
            default=0,
        )
        cells.append((cell, band, (lo, hi, bottom, top + lift)))
        for index, rise in enumerate(rises):
            a, b = max(lo, rise["span_m"][0]), min(hi, rise["span_m"][1])
            if b - a > SLIVER_M and rise["height_m"] > lift:
                cells.append(
                    (cell, f"{band}-rise{index}", (a, b, top + lift, top + rise["height_m"]))
                )
    voids = [(o["offset"], o["offset"] + o["width"], o["sill"], o["head"]) for o in openings]

    # Bands replace the base skin and the stone, and stop at the openings they cross.
    bands = []
    for index, band in enumerate(finish.get("bands", [])):
        rect = (*band.get("span_m", (0, length)), *band["z_m"])
        bands.append(rect)
        proud = band.get("proud_m", BAND_PROUD_M)
        for piece, part in enumerate(subtract_rectangles(rect, voids)):
            skin(f"band-{index}-{piece:02d}", part, proud, proud, band["material_id"], "band")

    for cell, band, rect in cells:
        for piece, part in enumerate(subtract_rectangles(rect, bands)):
            skin(
                f"facade-{cell:03d}-{band}-{piece:02d}",
                part,
                BASE_SKIN_PROUD_M,
                BASE_SKIN_DEPTH_M,
                finish["material_id"],
                "facade",
            )

    panels = []
    for index, panel in enumerate(finish.get("panels", [])):
        rect = (*panel["span_m"], *panel.get("z_span_m", (-math.inf, math.inf)))
        panels.append(rect)
        for cell, band, cell_rect in cells:
            clipped = clip_rectangle(rect, cell_rect)
            if clipped is None:
                continue
            slats = _slats(clipped, rect[0], panel.get("pitch_m"), panel.get("width_m"))
            for slat, part in enumerate(slats):
                skin(
                    f"accent-{index}-{cell}-{band}-{slat}",
                    part,
                    panel["depth_m"],
                    panel["depth_m"],
                    panel["material_id"],
                    "accent",
                )

    surrounds = []
    for opening in sorted(openings, key=lambda item: item["id"]):
        reveal = opening.get("reveal", {})
        if opening["kind"] not in REVEAL_KINDS or "surround_m" not in reveal:
            continue
        width = reveal["surround_m"]
        lo, sill, head = opening["offset"], opening["sill"], opening["head"]
        hi = lo + opening["width"]
        outer = clip_rectangle(
            (lo - width, hi + width, sill - width, head + width), (0, length, 0, height)
        )
        surrounds.append(outer)
        for piece, part in enumerate(subtract_rectangles(outer, [(lo, hi, sill, head)])):
            slats = _slats(part, lo - width, reveal.get("pitch_m"), reveal.get("width_m"))
            for slat, rect in enumerate(slats):
                skin(
                    f"surround-{opening['id']}-{piece}-{slat:02d}",
                    rect,
                    SURROUND_PROUD_M,
                    SURROUND_DEPTH_M,
                    reveal["surround_material_id"],
                    "surround",
                    {"Opening ID": opening["id"]},
                )

    if finish["style"] != "ledgestone":
        return
    stone = {**STONE_DEFAULTS, **finish["stone"]}
    span = (*finish.get("span_m", (0, length)), -math.inf, math.inf)
    rows = _courses(wall, stone, length, max(rect[3] for *_, rect in cells))
    holes = bands + panels + surrounds
    boxes = {material: [] for material in stone["material_ids"]}
    for *_, cell_rect in cells:
        clipped = clip_rectangle(cell_rect, span)
        if clipped is None:
            continue
        # Each stone is cut only where a cell edge or a hole actually crosses it.
        for z0, z1, stones in rows:
            for u0, u1, material in stones:
                piece = clip_rectangle((u0, u1, z0, z1), clipped)
                if piece is None:
                    continue
                for a, b, bottom, top in subtract_rectangles(piece, holes):
                    if b - a > SLIVER_M and top - bottom > SLIVER_M:
                        boxes[material].append(
                            _skin_mesh(
                                wall, (a, b, bottom, top), z, stone["proud_m"], stone["depth_m"]
                            )
                        )
    # One mesh per stone material keeps the facade to a few objects instead of thousands.
    for index, material in enumerate(boxes):
        if boxes[material]:
            builder.add(
                wall,
                f"stone-{index:02d}",
                merge(boxes[material]),
                EXTERIOR_DETAILS,
                material=material,
                kind="facade",
                slot="stone",
            )
