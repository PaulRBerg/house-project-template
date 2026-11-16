from __future__ import annotations

import math
from collections import Counter

import pytest
from shapely.geometry import Point, Polygon

from engine.geometry import (
    clip_rectangle,
    extrude_polygon,
    merge_intervals,
    oriented_box,
    polygon_area,
    subtract_intervals,
    subtract_rectangles,
    triangulate_polygon,
    validate_polygon,
    wall_footprint,
)


@pytest.fixture(scope="module")
def concave_with_hole():
    return {
        "outer": [[0, 0], [5, 0], [5, 2], [3, 2], [3, 5], [0, 5]],
        "holes": [[[1, 1], [2, 1], [2, 2], [1, 2]]],
    }


def test_nonrectangular_area_and_constrained_triangulation(concave_with_hole) -> None:
    assert polygon_area(concave_with_hole) == pytest.approx(18.0)
    triangles = triangulate_polygon(concave_with_hole)
    triangle_area = sum(polygon_area({"outer": triangle, "holes": []}) for triangle in triangles)
    assert triangle_area == pytest.approx(18.0)


def test_oriented_box_faces_outward_for_either_corner_order(signed_volume) -> None:
    corners = [(0, 0), (2, 0), (2, 1), (0, 1)]
    for ring in (corners, corners[::-1]):
        mesh = oriented_box(ring, 0.5, 1.5)
        assert len(mesh["vertices"]) == 8
        assert signed_volume(mesh) == pytest.approx(2.0)


def test_wall_footprint_supports_arbitrary_angles() -> None:
    footprint = wall_footprint([1, 2], [4, 6], 0.3)
    assert polygon_area(footprint) == pytest.approx(1.5)
    polygon = validate_polygon(footprint)
    assert math.dist(polygon.exterior.coords[0], polygon.exterior.coords[1]) == pytest.approx(5.0)


def test_interval_operations_clip_merge_and_subtract() -> None:
    assert merge_intervals([(-1, 2), (1, 3), (6, 12)], lower=0, upper=10) == [(0, 3), (6, 10)]
    assert subtract_intervals((0, 10), [(2, 4), (3, 5), (7, 8)]) == [(0, 2), (5, 7), (8, 10)]


def test_invalid_self_intersection_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid polygon"):
        validate_polygon({"outer": [[0, 0], [2, 2], [0, 2], [2, 0]], "holes": []})


def test_concave_holed_prism_is_manifold_outward_and_has_correct_volume(
    concave_with_hole, signed_volume, subtests
):
    mesh = extrude_polygon(concave_with_hole, 0, 2.4)
    assert len(mesh["vertices"]) == 20
    edges = Counter(
        tuple(sorted((a, b)))
        for face in mesh["faces"]
        for a, b in zip(face, face[1:] + face[:1], strict=True)
    )
    assert all(count == 2 for count in edges.values())
    assert signed_volume(mesh) == pytest.approx(18 * 2.4)
    for index, face in enumerate(mesh["faces"]):
        points = [mesh["vertices"][i] for i in face]
        if all(p[2] == 2.4 for p in points):
            with subtests.test(face_index=index):
                assert not Polygon([p[:2] for p in points]).contains(Point(1.5, 1.5))


def test_rectangle_difference_covers_the_remainder_with_disjoint_merged_pieces() -> None:
    assert clip_rectangle((0, 2, 0, 2), (2, 3, 0, 1)) is None
    assert clip_rectangle((0, 2, 0, 2), (1, 3, -1, 1)) == (1, 2, 0, 1)
    assert subtract_rectangles((0, 4, 0, 3), []) == [(0, 4, 0, 3)]
    pieces = subtract_rectangles((0, 4, 0, 3), [(1, 2, 1, 2), (3, 9, -9, 9)])
    assert sorted(pieces) == [(0, 1, 1, 2), (0, 3, 0, 1), (0, 3, 2, 3), (2, 3, 1, 2)]
    assert sum((u1 - u0) * (z1 - z0) for u0, u1, z0, z1 in pieces) == pytest.approx(8)
