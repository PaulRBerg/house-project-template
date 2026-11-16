"""Stdlib-only mesh primitives for the parametric furniture kit.

A mesh is ``{"vertices": [...], "faces": [...]}`` with an optional per-vertex
``"normals"`` list of analytic smooth normals. Coordinates are metres in the
furnishing's local frame. Faces wind counter-clockwise seen from outside.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

Mesh = dict
Vec = tuple[float, float, float]


def _normalize(vector: Sequence[float]) -> Vec:
    length = math.sqrt(sum(value * value for value in vector)) or 1.0
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _cross(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _sub(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _outward(vertices: Sequence[Sequence[float]], face: list[int], normal: Sequence[float]):
    a, b, c = (vertices[index] for index in face[:3])
    if _dot(_cross(_sub(b, a), _sub(c, a)), normal) < 0:
        face.reverse()
    return face


def merge(meshes: Sequence[Mesh]) -> Mesh:
    """Concatenate meshes; normals survive only when every input carries them."""
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    normals: list[Vec] | None = [] if all("normals" in item for item in meshes) else None
    for item in meshes:
        base = len(vertices)
        vertices.extend([list(vertex) for vertex in item["vertices"]])
        faces.extend([[index + base for index in face] for face in item["faces"]])
        if normals is not None:
            normals.extend(item["normals"])
    result: Mesh = {"vertices": vertices, "faces": faces}
    if normals is not None:
        result["normals"] = [list(normal) for normal in normals]
    return result


def transform(
    item: Mesh,
    *,
    rotate: Sequence[float] = (0.0, 0.0, 0.0),
    offset: Sequence[float] = (0.0, 0.0, 0.0),
) -> Mesh:
    """Rotate (XYZ Euler, radians) and translate a mesh copy."""
    cx, sx = math.cos(rotate[0]), math.sin(rotate[0])
    cy, sy = math.cos(rotate[1]), math.sin(rotate[1])
    cz, sz = math.cos(rotate[2]), math.sin(rotate[2])

    def turn(vector: Sequence[float]) -> Vec:
        x, y, z = vector
        y, z = y * cx - z * sx, y * sx + z * cx
        x, z = x * cy + z * sy, -x * sy + z * cy
        x, y = x * cz - y * sz, x * sz + y * cz
        return (x, y, z)

    vertices = [
        [value + shift for value, shift in zip(turn(vertex), offset, strict=True)]
        for vertex in item["vertices"]
    ]
    result: Mesh = {"vertices": vertices, "faces": [list(face) for face in item["faces"]]}
    if "normals" in item:
        result["normals"] = [list(_normalize(turn(normal))) for normal in item["normals"]]
    return result


def box(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> Mesh:
    """Axis-aligned flat-shaded box."""
    vertices = [[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [
        [0, 2, 6, 4],
        [1, 5, 7, 3],
        [0, 4, 5, 1],
        [2, 3, 7, 6],
        [0, 1, 3, 2],
        [4, 6, 7, 5],
    ]
    return {"vertices": vertices, "faces": faces}


def centered_box(size: Sequence[float]) -> Mesh:
    w, d, h = size
    return box(-w / 2, -d / 2, -h / 2, w / 2, d / 2, h / 2)


def rounded_box(
    size: Sequence[float],
    center: Sequence[float] = (0.0, 0.0, 0.0),
    radius: float = 0.02,
    segments: int = 2,
    *,
    bulge: float = 0.0,
    bulge_axes: str = "z",
) -> Mesh:
    """Minkowski rounded box (cube-sphere corners) with optional cushion bulge.

    ``bulge`` pushes the flat regions of the named faces (``x``, ``y``, ``z`` for
    both signs, or ``+z``/``-y`` style single faces) outward by up to that many
    metres, giving upholstery a soft, filled look.
    """
    half = [value / 2 for value in size]
    radius = max(1e-4, min(radius, *(value - 2e-4 for value in half)))
    divisions = 4 if bulge else 0
    bulged = set()
    for token in bulge_axes.split(","):
        token = token.strip()
        signs = (
            (1.0,) if token.startswith("+") else (-1.0,) if token.startswith("-") else (-1.0, 1.0)
        )
        bulged.update(("xyz".index(token[-1]), sign) for sign in signs)
    angles = [math.radians(-45 + 45 * index / segments) for index in range(segments + 1)]
    samples = [(-1.0, math.tan(angle)) for angle in angles]
    samples += [(-1 + 2 * (index + 1) / (divisions + 1), 0.0) for index in range(divisions)]
    samples += [(1.0, -math.tan(angle)) for angle in reversed(angles)]
    vertices: list[list[float]] = []
    normals: list[Vec] = []
    faces: list[list[int]] = []
    welded: dict[tuple[int, int, int], int] = {}
    for axis in range(3):
        for sign in (-1.0, 1.0):
            u_axis, v_axis = [value for value in range(3) if value != axis]
            face_normal = [0.0, 0.0, 0.0]
            face_normal[axis] = sign
            grid: list[list[int]] = []
            for fu, tu in samples:
                row = []
                for fv, tv in samples:
                    fraction = [0.0, 0.0, 0.0]
                    tangent = [0.0, 0.0, 0.0]
                    fraction[axis], tangent[axis] = sign, sign
                    fraction[u_axis], tangent[u_axis] = fu, tu
                    fraction[v_axis], tangent[v_axis] = fv, tv
                    direction = _normalize(tangent)
                    point = [
                        center[i] + (half[i] - radius) * fraction[i] + radius * direction[i]
                        for i in range(3)
                    ]
                    if bulge and tu == 0 and tv == 0 and (axis, sign) in bulged:
                        point[axis] += sign * bulge * (1 - fu * fu) * (1 - fv * fv)
                    key = tuple(round(value * 1e6) for value in point)
                    if key not in welded:
                        welded[key] = len(vertices)
                        vertices.append(point)
                        normals.append(direction)
                    row.append(welded[key])
                grid.append(row)
            for i in range(len(samples) - 1):
                for j in range(len(samples) - 1):
                    quad = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
                    if len(set(quad)) < 3:
                        continue
                    if len(set(quad)) == 3:
                        quad = list(dict.fromkeys(quad))
                    faces.append(_outward(vertices, quad, face_normal))
    result: Mesh = {"vertices": vertices, "faces": faces}
    if not bulge:
        result["normals"] = [list(normal) for normal in normals]
    return result


def rounded_rect(width: float, depth: float, radius: float, segments: int = 6):
    """Convex rounded-rectangle outline centred on the origin, counter-clockwise."""
    radius = max(0.0, min(radius, width / 2 - 1e-4, depth / 2 - 1e-4))
    if radius <= 0:
        return [
            (-width / 2, -depth / 2),
            (width / 2, -depth / 2),
            (width / 2, depth / 2),
            (-width / 2, depth / 2),
        ]
    points = []
    for corner, (cx, cy) in enumerate(
        (
            (width / 2 - radius, -depth / 2 + radius),
            (width / 2 - radius, depth / 2 - radius),
            (-width / 2 + radius, depth / 2 - radius),
            (-width / 2 + radius, -depth / 2 + radius),
        )
    ):
        start = -math.pi / 2 + corner * math.pi / 2
        for step in range(segments + 1):
            angle = start + step * (math.pi / 2) / segments
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def corner_points(x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
    """The four corners of an axis-aligned rectangle, x-major, for legs and feet."""
    return [(x, y) for x in (x0, x1) for y in (y0, y1)]


def rectangular_bowl(
    size: Sequence[float],
    center: Sequence[float] = (0.0, 0.0, 0.0),
    *,
    radius: float = 0.03,
) -> Mesh:
    """Closed hollow shell with a rounded lip and an inset, upward-facing floor.

    Dimensions describe the existing outer envelope, including the floor and
    rim. The small wall and edge details are visualization geometry.
    """
    w, d, h = size
    wall, segments = 0.008, 8
    edge = min(wall / 3, h / 8)
    fillet = min(0.018, h / 5)
    # Walk the cross-section from the underside, up the outside and down inside.
    profile = [
        (edge, -h / 2),
        (0.0, -h / 2 + edge),
        (0.0, h / 2 - edge),
        (edge, h / 2),
        (wall - edge, h / 2),
        (wall, h / 2 - edge),
        (wall + fillet, -h / 2 + wall + fillet),
        (wall + 2 * fillet, -h / 2 + wall),
    ]
    outlines = [
        rounded_rect(w - 2 * inset, d - 2 * inset, radius, segments) for inset, _ in profile
    ]
    vertices = [
        [x + center[0], y + center[1], z + center[2]]
        for (_, z), outline in zip(profile, outlines, strict=True)
        for x, y in outline
    ]
    count = len(outlines[0])
    faces = [list(reversed(range(count)))]
    for ring in range(len(profile) - 1):
        lo, hi = ring * count, (ring + 1) * count
        faces.extend(
            [lo + i, lo + (i + 1) % count, hi + (i + 1) % count, hi + i] for i in range(count)
        )
    faces.append(list(range(len(vertices) - count, len(vertices))))
    normals = [[0.0, 0.0, 0.0] for _ in vertices]
    for face in faces:
        a, b, c = (vertices[index] for index in face[:3])
        normal = _normalize(_cross(_sub(b, a), _sub(c, a)))
        for index in face:
            normals[index] = [n + f for n, f in zip(normals[index], normal, strict=True)]
    normals = [list(_normalize(n)) for n in normals]
    # Keep the broad planar caps flat; the adjoining fillets meet them tangentially.
    normals[:count] = [[0.0, 0.0, -1.0] for _ in range(count)]
    normals[-count:] = [[0.0, 0.0, 1.0] for _ in range(count)]
    return {"vertices": vertices, "faces": faces, "normals": normals}


def dome_profile(
    radius: float, base_z: float, height: float, apex_radius: float, steps: int = 10
) -> list[tuple[float, float]]:
    """Quarter-ellipse lathe profile from ``(radius, base_z)`` up to a small apex opening."""
    points = [
        (radius * math.cos(a), base_z + height * math.sin(a))
        for a in [math.pi / 2 * i / steps for i in range(steps + 1)]
    ]
    points[-1] = (apex_radius, points[-1][1])
    return points


def ellipse(width: float, depth: float, segments: int = 48):
    return [
        (
            width / 2 * math.cos(2 * math.pi * step / segments),
            depth / 2 * math.sin(2 * math.pi * step / segments),
        )
        for step in range(segments)
    ]


def prism(outline: Sequence[Sequence[float]], z0: float, z1: float) -> Mesh:
    """Extrude a convex counter-clockwise outline with flat caps and soft sides."""
    count = len(outline)
    vertices: list[list[float]] = []
    normals: list[Vec] = []
    faces: list[list[int]] = []
    for z, normal in ((z0, (0.0, 0.0, -1.0)), (z1, (0.0, 0.0, 1.0))):
        base = len(vertices)
        vertices.extend([[x, y, z] for x, y in outline])
        normals.extend([normal] * count)
        cap = list(range(base, base + count))
        faces.append(cap if z == z1 else list(reversed(cap)))
    side_normals = []
    for index in range(count):
        previous = outline[index - 1]
        following = outline[(index + 1) % count]
        tangent = (following[0] - previous[0], following[1] - previous[1])
        side_normals.append(_normalize((tangent[1], -tangent[0], 0.0)))
    base = len(vertices)
    for z in (z0, z1):
        vertices.extend([[x, y, z] for x, y in outline])
        normals.extend(side_normals)
    for index in range(count):
        nxt = (index + 1) % count
        faces.append([base + index, base + nxt, base + count + nxt, base + count + index])
    return {"vertices": vertices, "faces": faces, "normals": [list(n) for n in normals]}


def lathe(
    profile: Sequence[Sequence[float]],
    *,
    segments: int = 32,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    cap_bottom: bool = True,
    cap_top: bool = True,
) -> Mesh:
    """Revolve an ``(r, z)`` profile listed from bottom to top around the Z axis."""
    points = [(float(r), float(z)) for r, z in profile]
    ring_normals = []
    for index, (_r, _z) in enumerate(points):
        before = points[max(index - 1, 0)]
        after = points[min(index + 1, len(points) - 1)]
        dr, dz = after[0] - before[0], after[1] - before[1]
        ring_normals.append(_normalize((dz, 0.0, -dr)))
    vertices: list[list[float]] = []
    normals: list[Vec] = []
    faces: list[list[int]] = []
    cx, cy, cz = center

    def ring(r: float, z: float, normal: Sequence[float] | None) -> int:
        start = len(vertices)
        for step in range(segments):
            angle = 2 * math.pi * step / segments
            cos, sin = math.cos(angle), math.sin(angle)
            vertices.append([cx + r * cos, cy + r * sin, cz + z])
            if normal is None:
                normals.append((0.0, 0.0, 0.0))
            else:
                normals.append(_normalize((normal[0] * cos, normal[0] * sin, normal[2])))
        return start

    rings = [ring(r, z, ring_normals[index]) for index, (r, z) in enumerate(points)]
    for index in range(len(points) - 1):
        lower, upper = rings[index], rings[index + 1]
        for step in range(segments):
            nxt = (step + 1) % segments
            faces.append([lower + step, lower + nxt, upper + nxt, upper + step])
    for index, flag, normal in ((0, cap_bottom, -1.0), (len(points) - 1, cap_top, 1.0)):
        r, z = points[index]
        if not flag or r <= 1e-6:
            continue
        start = ring(r, z, None)
        for step in range(segments):
            normals[start + step] = (0.0, 0.0, normal)
        cap = list(range(start, start + segments))
        faces.append(cap if normal > 0 else list(reversed(cap)))
    return {"vertices": vertices, "faces": faces, "normals": [list(n) for n in normals]}


def cylinder(
    radius: float,
    z0: float,
    z1: float,
    *,
    center: Sequence[float] = (0.0, 0.0),
    segments: int = 24,
) -> Mesh:
    return lathe(
        [(radius, z0), (radius, z1)], segments=segments, center=(center[0], center[1], 0.0)
    )


def rod(start: Sequence[float], end: Sequence[float], radius: float, segments: int = 12) -> Mesh:
    """Capped cylinder between two points."""
    axis = _sub(end, start)
    length = math.sqrt(_dot(axis, axis))
    base = cylinder(radius, 0.0, length, segments=segments)
    direction = _normalize(axis)
    pitch = math.acos(max(-1.0, min(1.0, direction[2])))
    yaw = math.atan2(direction[1], direction[0])
    return transform(base, rotate=(0.0, pitch, yaw), offset=start)


def curtain(
    width: float,
    height: float,
    *,
    depth: float = 0.08,
    pleat: float = 0.16,
    phase: float = 0.0,
) -> Mesh:
    """Pleated drape sheet along X, centred at the origin and hanging along Z.

    Ripple-fold pleats fill ``depth``; the hem flares slightly so the fabric
    reads as falling from a ceiling track rather than as a rigid panel.
    """
    flare = 0.012
    folds = max(2, round(width / pleat))
    amplitude = depth / 2 - flare
    columns = folds * 8
    rows = 8
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for row in range(rows + 1):
        t = row / rows
        z = -height / 2 + height * t
        swing = amplitude + flare * (1 - t) ** 2
        for column in range(columns + 1):
            x = -width / 2 + width * column / columns
            angle = 2 * math.pi * folds * column / columns + phase
            vertices.append([x, swing * math.sin(angle), z])
    for row in range(rows):
        for column in range(columns):
            a = row * (columns + 1) + column
            b = a + columns + 1
            faces.append([a, a + 1, b + 1, b])
    return {"vertices": vertices, "faces": faces}


def curved_wall(
    radius: float,
    thickness: float,
    sweep: float,
    z0: float,
    height: Callable[[float], float],
    *,
    center: Sequence[float] = (0.0, 0.0),
    segments: int = 24,
) -> Mesh:
    """Soft-topped upholstered wall swept along a circular arc around ``center``.

    Angle 0 points along +Y and the arc spans ``[-sweep, sweep]``; ``height(angle)``
    gives the crest height above ``z0``, so a tub-chair back can fall into its arms.
    """
    cx, cy = center
    inner, outer = radius - thickness / 2, radius + thickness / 2
    vertices: list[list[float]] = []
    normals: list[Vec] = []
    for step in range(segments + 1):
        angle = -sweep + 2 * sweep * step / segments
        sin, cos = math.sin(angle), math.cos(angle)
        top = z0 + height(angle)
        shoulder = top - thickness * 0.4
        for r, z, normal in (
            (inner, z0, (-sin, -cos, -0.3)),
            (outer, z0, (sin, cos, -0.3)),
            (outer, shoulder, (sin, cos, 0.6)),
            (radius, top, (0.0, 0.0, 1.0)),
            (inner, shoulder, (-sin, -cos, 0.6)),
        ):
            vertices.append([cx + r * sin, cy + r * cos, z])
            normals.append(_normalize(normal))
    faces: list[list[int]] = []
    ring = 5
    for step in range(segments):
        a, b = step * ring, (step + 1) * ring
        middle = -sweep + 2 * sweep * (step + 0.5) / segments
        out = (math.sin(middle), math.cos(middle), 0.0)
        back = (-out[0], -out[1], 0.0)
        for i, j, normal in (
            (0, 1, (0.0, 0.0, -1.0)),
            (1, 2, out),
            (2, 3, (out[0], out[1], 1.0)),
            (3, 4, (back[0], back[1], 1.0)),
            (4, 0, back),
        ):
            faces.append(_outward(vertices, [a + i, b + i, b + j, a + j], normal))
    for base, sign in ((0, -1.0), (segments * ring, 1.0)):
        angle = sign * sweep
        tangent = (math.cos(angle) * sign, -math.sin(angle) * sign, 0.0)
        faces.append(_outward(vertices, list(range(base, base + ring)), tangent))
    return {"vertices": vertices, "faces": faces, "normals": [list(n) for n in normals]}


def leaf(
    length: float,
    width: float,
    *,
    shape: Callable[[float], float] | None = None,
    fold: float = 0.25,
    curl: float = 0.35,
    steps: int = 6,
) -> Mesh:
    """Single leaf lying along +Y from the origin with a midrib fold and a downward curl."""
    profile = shape or (lambda t: math.sin(math.pi * t**0.8) ** 0.9)
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for step in range(steps + 1):
        t = step / steps
        y = length * t
        drop = curl * length * t * t
        half = width / 2 * profile(t)
        lift = fold * half
        vertices.append([-half, y, lift - drop])
        vertices.append([0.0, y, -drop])
        vertices.append([half, y, lift - drop])
    for step in range(steps):
        a = step * 3
        faces.append([a, a + 3, a + 4, a + 1])
        faces.append([a + 1, a + 4, a + 5, a + 2])
    return {"vertices": vertices, "faces": faces}
