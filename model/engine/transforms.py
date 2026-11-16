"""Pure affine 4x4 matrix and wall-frame helpers shared across ``model/engine`` modules.

Matrices are 4x4 nested lists in row-major order. Every function here uses only
the Python standard library (``math``), so this module stays importable inside
Blender's bundled Python interpreter, which has no third-party packages
installed.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


def finite_vector(
    value: Any, size: int, field: str, error: type[Exception] = ValueError
) -> list[float]:
    """Return *value* as ``size`` finite floats, raising *error* naming *field* otherwise."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != size:
        raise error(f"{field} must contain {size} values")
    if not all(isinstance(item, (int, float)) for item in value):
        raise error(f"{field} values must be numeric")
    result = [float(item) for item in value]
    if not all(math.isfinite(item) for item in result):
        raise error(f"{field} values must be finite")
    return result


def apply_point(matrix: Sequence[Sequence[float]], point: Sequence[float]) -> list[float]:
    """Transform a 3D point by a 4x4 affine matrix."""

    return [
        sum(float(matrix[row][k]) * float(point[k]) for k in range(3)) + float(matrix[row][3])
        for row in range(3)
    ]


def multiply(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    """Multiply two 4x4 matrices: ``a @ b``."""

    return [
        [sum(float(a[row][k]) * float(b[k][column]) for k in range(4)) for column in range(4)]
        for row in range(4)
    ]


def translation(x: float, y: float, z: float) -> list[list[float]]:
    """Return a 4x4 translation matrix."""

    return [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]


def rotation_xyz(rx: float, ry: float, rz: float) -> list[list[float]]:
    """Return the 4x4 rotation matrix for XYZ-order Euler angles, in radians."""

    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    x = [[1, 0, 0, 0], [0, cx, -sx, 0], [0, sx, cx, 0], [0, 0, 0, 1]]
    y = [[cy, 0, sy, 0], [0, 1, 0, 0], [-sy, 0, cy, 0], [0, 0, 0, 1]]
    z = [[cz, -sz, 0, 0], [sz, cz, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    return multiply(multiply(z, y), x)


def rotation_translation(position: Sequence[float], rotation: Sequence[float]) -> list[list[float]]:
    """Return the combined rotate-then-translate 4x4 matrix ``T(position) @ R(rotation)``."""

    x, y, z = (float(value) for value in position)
    rx, ry, rz = (float(value) for value in rotation)
    return multiply(translation(x, y, z), rotation_xyz(rx, ry, rz))


def affine_inverse_rigid(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    """Return the inverse of a rigid (rotation + translation) 4x4 matrix."""

    rotation = [[float(matrix[r][c]) for c in range(3)] for r in range(3)]
    transposed = [[rotation[c][r] for c in range(3)] for r in range(3)]
    translation_vector = [float(matrix[r][3]) for r in range(3)]
    result = [[0.0] * 4 for _ in range(4)]
    for row in range(3):
        for column in range(3):
            result[row][column] = transposed[row][column]
        result[row][3] = -sum(transposed[row][k] * translation_vector[k] for k in range(3))
    result[3] = [0, 0, 0, 1]
    return result


def determinant3(matrix: Sequence[Sequence[float]]) -> float:
    """Return the determinant of the upper-left 3x3 block of a 4x4 matrix."""

    a, b, c = matrix[0][:3]
    d, e, f = matrix[1][:3]
    g, h, i = matrix[2][:3]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def wall_frame(wall: Mapping[str, Any]) -> tuple[Sequence[float], tuple[float, float], float]:
    """Return a wall's start point, unit start-to-end direction and length."""

    start, end = wall["start"], wall["end"]
    length = math.dist(start, end)
    return start, ((end[0] - start[0]) / length, (end[1] - start[1]) / length), length


def wall_point(wall: Mapping[str, Any], u: float, v: float = 0) -> list[float]:
    """Point ``u`` along the wall and ``v`` to the left of its start-to-end vector."""

    (x, y), (dx, dy), _ = wall_frame(wall)
    return [x + dx * u - dy * v, y + dy * u + dx * v]
