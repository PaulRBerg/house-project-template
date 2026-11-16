"""Host-side Shapely geometry helpers for the design compilers; never imported inside Blender."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from itertools import pairwise
from typing import Any

from shapely import affinity, constrained_delaunay_triangles
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.validation import explain_validity

from .transforms import wall_point

Point2D = Sequence[float]
Interval = tuple[float, float]
Rectangle = tuple[float, float, float, float]
Mesh = dict[str, list]


def _open_ring(points: Sequence[Point2D]) -> list[tuple[float, float]]:
    ring = [(float(point[0]), float(point[1])) for point in points]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()
    return ring


def as_polygon(value: Mapping[str, Any] | Polygon) -> Polygon:
    """Convert the JSON polygon shape into a Shapely polygon."""

    if isinstance(value, Polygon):
        return value
    if not isinstance(value, Mapping) or "outer" not in value:
        raise ValueError("polygon must be an object with an outer ring")
    outer = _open_ring(value["outer"])
    holes = [_open_ring(ring) for ring in value.get("holes", [])]
    return Polygon(outer, holes)


def validate_polygon(value: Mapping[str, Any] | Polygon) -> Polygon:
    """Return a valid positive-area polygon, preserving concavity and holes."""

    polygon = as_polygon(value)
    if not polygon.is_valid:
        raise ValueError(f"invalid polygon: {explain_validity(polygon)}")
    if polygon.is_empty or polygon.area <= 0:
        raise ValueError("polygon must have positive area")
    return polygon


def polygon_area(value: Mapping[str, Any] | Polygon) -> float:
    """Measure arbitrary simple polygons, including concavity and holes."""

    return float(validate_polygon(value).area)


def triangulate_polygon(value: Mapping[str, Any] | Polygon) -> list[list[list[float]]]:
    """Constrained-Delaunay triangulate a polygon without filling its holes."""

    polygon = validate_polygon(value)
    triangles = constrained_delaunay_triangles(polygon)
    result = []
    for triangle in triangles.geoms:
        coordinates = [[float(x), float(y)] for x, y in list(triangle.exterior.coords)[:-1]]
        if len(coordinates) == 3 and triangle.area > 0:
            result.append(coordinates)
    result.sort(key=lambda tri: tuple(coordinate for point in tri for coordinate in point))
    return result


def extrude_polygon(value: Mapping[str, Any] | Polygon, bottom: float, top: float) -> Mesh:
    """Manifold prism with consistently outward normals, concavity and voids."""

    if top <= bottom:
        raise ValueError("prism top must exceed bottom")
    polygon = orient(as_polygon(value), sign=1)
    rings = [list(polygon.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in polygon.interiors]
    rings = [ring[ring.index(min(ring)) :] + ring[: ring.index(min(ring))] for ring in rings]
    rings = rings[:1] + sorted(rings[1:])
    coordinates = list(dict.fromkeys(point for ring in rings for point in ring))
    index = {point: i for i, point in enumerate(coordinates)}
    n = len(coordinates)
    vertices = [[x, y, bottom] for x, y in coordinates] + [[x, y, top] for x, y in coordinates]
    faces = []
    for triangle in triangulate_polygon(polygon):
        face = [index[tuple(p)] for p in triangle]
        a, b, c = triangle
        if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) < 0:
            face.reverse()
        faces.extend([list(reversed(face)), [i + n for i in face]])
    for ring in rings:
        for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
            i, j = index[a], index[b]
            faces.append([i, j, j + n, i + n])
    return {"vertices": vertices, "faces": faces}


def oriented_box(corners: Sequence[Point2D], bottom: float, top: float) -> Mesh:
    """Eight-vertex, six-quad prism of a convex XY quadrilateral with outward faces."""

    if top <= bottom:
        raise ValueError("prism top must exceed bottom")
    ring = [(float(x), float(y)) for x, y in corners]
    doubled_area = sum(
        a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True)
    )
    if len(ring) != 4 or abs(doubled_area) <= 1e-18:
        raise ValueError("oriented box needs four corners enclosing positive area")
    if doubled_area < 0:
        ring.reverse()
    vertices = [[x, y, bottom] for x, y in ring] + [[x, y, top] for x, y in ring]
    faces = [[3, 2, 1, 0], [4, 5, 6, 7]]
    faces += [[i, (i + 1) % 4, (i + 1) % 4 + 4, i + 4] for i in range(4)]
    return {"vertices": vertices, "faces": faces}


def rectangle_mesh(x0: float, y0: float, x1: float, y1: float, z0: float, z1: float) -> Mesh:
    return oriented_box([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def wall_box(
    wall: Mapping[str, Any],
    lo: float,
    hi: float,
    offset: float,
    depth: float,
    bottom: float,
    top: float,
) -> Mesh:
    """Box spanning ``lo..hi`` along a wall, centred ``offset`` to its left."""

    near, far = offset - depth / 2, offset + depth / 2
    corners = [wall_point(wall, u, v) for u, v in ((lo, near), (hi, near), (hi, far), (lo, far))]
    return oriented_box(corners, bottom, top)


def wall_footprint(start: Point2D, end: Point2D, thickness: float) -> dict[str, list[Any]]:
    """Return the centered footprint of an arbitrary 2D wall segment."""

    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    length = math.hypot(x1 - x0, y1 - y0)
    if length <= 0:
        raise ValueError("wall start and end must differ")
    if not math.isfinite(thickness) or thickness <= 0:
        raise ValueError("wall thickness must be a positive finite number")
    nx, ny = -(y1 - y0) / length, (x1 - x0) / length
    half = thickness / 2
    outer = [
        [x0 + nx * half, y0 + ny * half],
        [x1 + nx * half, y1 + ny * half],
        [x1 - nx * half, y1 - ny * half],
        [x0 - nx * half, y0 - ny * half],
    ]
    return {"outer": outer, "holes": []}


def map_plan(
    value: Mapping[str, Any] | BaseGeometry, transform: Sequence[Sequence[float]]
) -> BaseGeometry:
    """Map plan geometry, or a JSON polygon, through the XY part of a 4x4 affine transform."""

    return affinity.affine_transform(
        as_polygon(value) if isinstance(value, Mapping) else value,
        [
            float(transform[0][0]),
            float(transform[0][1]),
            float(transform[1][0]),
            float(transform[1][1]),
            float(transform[0][3]),
            float(transform[1][3]),
        ],
    )


def furnishing_footprint(
    room: Mapping[str, Any], furnishing: Mapping[str, Any], *, clearance: bool = False
) -> Polygon:
    """Local plan footprint of a furnishing, optionally grown by its authored clearances."""

    width, depth = float(furnishing["dimensions"][0]), float(furnishing["dimensions"][1])
    values = furnishing.get("clearance_m", {}) if clearance else {}
    left, right = float(values.get("left", 0)), float(values.get("right", 0))
    front, back = float(values.get("front", 0)), float(values.get("back", 0))
    shape = box(-width / 2 - left, -depth / 2 - back, width / 2 + right, depth / 2 + front)
    shape = affinity.rotate(
        shape, float(furnishing["rotation"][2]), origin=(0, 0), use_radians=True
    )
    position = furnishing["position"]
    return affinity.translate(
        shape,
        float(room["anchor"][0]) + float(position[0]),
        float(room["anchor"][1]) + float(position[1]),
    )


def merge_intervals(
    intervals: Iterable[Sequence[float]], *, lower: float | None = None, upper: float | None = None
) -> list[Interval]:
    """Clip, sort and merge overlapping or touching 1D intervals."""

    if lower is not None and upper is not None and lower > upper:
        raise ValueError("lower bound must not exceed upper bound")
    prepared: list[Interval] = []
    for interval in intervals:
        lo, hi = float(interval[0]), float(interval[1])
        if not math.isfinite(lo) or not math.isfinite(hi) or hi < lo:
            raise ValueError(f"invalid interval: {interval!r}")
        if lower is not None:
            lo = max(lo, lower)
        if upper is not None:
            hi = min(hi, upper)
        if hi > lo:
            prepared.append((lo, hi))
    prepared.sort()
    merged: list[Interval] = []
    for lo, hi in prepared:
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def subtract_intervals(base: Sequence[float], cuts: Iterable[Sequence[float]]) -> list[Interval]:
    """Subtract cut intervals from one base interval."""

    lo, hi = float(base[0]), float(base[1])
    if hi < lo:
        raise ValueError("base interval end must not precede its start")
    cursor = lo
    result: list[Interval] = []
    for cut_lo, cut_hi in merge_intervals(cuts, lower=lo, upper=hi):
        if cut_lo > cursor:
            result.append((cursor, cut_lo))
        cursor = max(cursor, cut_hi)
    if cursor < hi:
        result.append((cursor, hi))
    return result


def clip_rectangle(rect: Rectangle, bounds: Rectangle) -> Rectangle | None:
    """Intersect two ``(u0, u1, z0, z1)`` rectangles; ``None`` when they share no area."""

    u0, u1 = max(rect[0], bounds[0]), min(rect[1], bounds[1])
    z0, z1 = max(rect[2], bounds[2]), min(rect[3], bounds[3])
    return (u0, u1, z0, z1) if u1 - u0 > 1e-9 and z1 - z0 > 1e-9 else None


def subtract_rectangles(rect: Rectangle, holes: Iterable[Rectangle]) -> list[Rectangle]:
    """Cover ``rect`` minus ``holes`` with disjoint rectangles, merged along rows then columns."""

    clipped = [hole for hole in (clip_rectangle(hole, rect) for hole in holes) if hole]
    us = sorted({rect[0], rect[1], *(value for hole in clipped for value in hole[:2])})
    zs = sorted({rect[2], rect[3], *(value for hole in clipped for value in hole[2:])})
    pieces: list[list[float]] = []
    for z0, z1 in pairwise(zs):
        row: list[list[float]] = []
        for u0, u1 in pairwise(us):
            uc, zc = (u0 + u1) / 2, (z0 + z1) / 2
            if any(h[0] < uc < h[1] and h[2] < zc < h[3] for h in clipped):
                continue
            if row and row[-1][1] == u0:
                row[-1][1] = u1
            else:
                row.append([u0, u1])
        for u0, u1 in row:
            below = next((p for p in pieces if p[:2] == [u0, u1] and p[3] == z0), None)
            if below:
                below[3] = z1
            else:
                pieces.append([u0, u1, z0, z1])
    return [(u0, u1, z0, z1) for u0, u1, z0, z1 in pieces if u1 - u0 > 1e-9 and z1 - z0 > 1e-9]


def roof_frame(roof: Mapping[str, Any]) -> tuple[tuple[float, float], Point2D, float]:
    """Return a roof's unit uphill slope direction, pitch origin and pitch angle in radians."""
    dx, dy = roof["slope_direction"]
    norm = math.hypot(dx, dy)
    if norm == 0:
        raise ValueError(f"{roof['id']}: slope_direction cannot be zero")
    origin = roof.get("pitch_origin") or next(iter(as_polygon(roof["polygon"]).centroid.coords))
    return (dx / norm, dy / norm), origin, math.radians(roof["pitch_deg"])


def roof_covering_z(roof: Mapping[str, Any], point: Point2D) -> float:
    """Covering-surface elevation above a plan point; ``base_z_m`` is its height at the origin."""
    (dx, dy), origin, angle = roof_frame(roof)
    along = (point[0] - origin[0]) * dx + (point[1] - origin[1]) * dy
    return roof["base_z_m"] + along * math.tan(angle)
