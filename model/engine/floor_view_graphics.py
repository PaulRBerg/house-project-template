"""Temporary, camera-aware drawing graphics for furnished floor views."""

from __future__ import annotations

import math
import textwrap
from contextlib import contextmanager
from typing import Any

LABEL_PAPER_PADDING = (0.08, 0.06)
LABEL_GAP = 0.02


def room_label(room: Any, room_id: str, *, cutaway: bool) -> str:
    name = textwrap.fill(
        room.get("Room label", room["Room name"]), width=16, break_long_words=False
    )
    lines = [name, f"{room['Room total area m²']:.1f} m²"]
    return "\n".join(lines if cutaway else [room_id, *lines])


def rectangles_overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def place_labels(specifications):
    """Pack measured cards at room-derived candidates; fail rather than overlap."""
    placed, result = [], {}
    # Narrow rooms have fewer useful positions; reserve their space first.
    for key, bounds, candidates in sorted(specifications, key=lambda item: (len(item[2]), item[0])):
        for x, y in candidates:
            rectangle = (x + bounds[0], y + bounds[1], x + bounds[2], y + bounds[3])
            if not any(rectangles_overlap(rectangle, other) for other in placed):
                placed.append(rectangle)
                result[key] = (x, y)
                break
        else:
            return None
    return result


def _inside(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def _room_candidates(room_objects, camera_inverse, preferred):
    """Sample actual top faces, retaining disconnected floor parts and concave rooms."""
    from mathutils import Vector

    polygons = []
    for room in room_objects:
        for face in room.data.polygons:
            if face.normal.z > 0.9:
                polygons.append(
                    [room.matrix_world @ room.data.vertices[i].co for i in face.vertices]
                )
    points = [point for polygon in polygons for point in polygon]
    if not points:
        raise ValueError("Room floor has no upward faces for label placement")
    z = max(point.z for point in points) + 0.08
    xmin, xmax = min(p.x for p in points), max(p.x for p in points)
    ymin, ymax = min(p.y for p in points), max(p.y for p in points)
    candidates = []
    projected_preferred = camera_inverse @ preferred
    # Labels were lifted along the camera axis to clear furniture. Recover their floor anchor.
    ray = camera_inverse.inverted().col[2].xyz
    preferred = preferred + ray * ((z - preferred.z) / ray.z)
    # Include the current anchor only if it actually lies on a floor face.
    samples = [(preferred.x, preferred.y)] + [
        (xmin + (xmax - xmin) * x / 10, ymin + (ymax - ymin) * y / 10)
        for x in range(1, 10)
        for y in range(1, 10)
    ]
    for x, y in samples:
        if any(_inside((x, y), [(p.x, p.y) for p in polygon]) for polygon in polygons):
            projected = camera_inverse @ Vector((x, y, z))
            candidates.append((projected.x, projected.y))
    return sorted(
        set(candidates),
        key=lambda p: (math.dist(p, (projected_preferred.x, projected_preferred.y)), p),
    )


def fit_floor_labels(bpy, scene, camera, labels):
    """Place every label from evaluated text bounds, preserving the room association."""
    from mathutils import Vector

    inverse = camera.matrix_world.inverted()
    floors = {}
    for obj in scene.objects:
        if obj.get("Room ID"):
            floors.setdefault(obj["Room ID"], []).append(obj)
    candidates = {
        label.name: _room_candidates(floors[room_id], inverse, label.matrix_world.translation)
        for label, room_id in labels
    }
    for attempt in range(7):
        bpy.context.view_layer.update()
        specifications = []
        for label, _ in labels:
            px, py = (value + LABEL_GAP for value in LABEL_PAPER_PADDING)
            bounds = (
                min(p[0] for p in label.bound_box) - px,
                min(p[1] for p in label.bound_box) - py,
                max(p[0] for p in label.bound_box) + px,
                max(p[1] for p in label.bound_box) + py,
            )
            specifications.append((label.name, bounds, candidates[label.name]))
        placements = place_labels(specifications)
        if placements is not None:
            for label, _ in labels:
                x, y = placements[label.name]
                current = inverse @ label.matrix_world.translation
                label.matrix_world.translation = camera.matrix_world @ Vector((x, y, current.z))
            bpy.context.view_layer.update()
            return
        if attempt < 6:
            for label, _ in labels:
                label.data.size *= 0.9
    raise ValueError("Floor labels cannot fit without overlap in the current camera")


def glazing_symbol(points, elevation):
    """A pale pane with a fine closed frame, independent of its sill height."""
    # Procedural panes are vertical boxes. Their longest horizontal pair defines the glazing span.
    a, b = max(
        ((a, b) for a in points for b in points),
        key=lambda pair: math.dist(pair[0][:2], pair[1][:2]),
    )
    length = math.dist(a[:2], b[:2])
    if length < 0.05:
        raise ValueError("Glazing pane has no horizontal span")
    nx, ny = -(b[1] - a[1]) / length, (b[0] - a[0]) / length
    half_width, frame = 0.05, 0.009
    end = frame / length
    vertices, faces, materials = [], [], []
    for start, stop, low, high, material in (
        (0, 1, -half_width, half_width, 0),
        (0, 1, -half_width, -half_width + frame, 1),
        (0, 1, half_width - frame, half_width, 1),
        (0, end, -half_width, half_width, 1),
        (1 - end, 1, -half_width, half_width, 1),
    ):
        index = len(vertices)
        vertices.extend(
            (
                a[0] + (b[0] - a[0]) * along + nx * side,
                a[1] + (b[1] - a[1]) * along + ny * side,
                elevation + material * 0.001,
            )
            for along, side in ((start, low), (stop, low), (stop, high), (start, high))
        )
        faces.append(tuple(range(index, index + 4)))
        materials.append(material)
    return vertices, faces, materials


@contextmanager
def floor_window_symbols(bpy, scene, level):
    """Place window graphics at the section plane, respecting furniture occlusion."""
    objects, meshes, materials = [], [], []
    try:
        for name, color in (
            ("glazing mist", (0.66, 0.72, 0.72, 1)),
            ("glazing frame", (0.18, 0.20, 0.20, 1)),
        ):
            material = bpy.data.materials.new("Temporary / " + name)
            materials.append(material)
            material.use_nodes = True
            nodes = material.node_tree.nodes
            nodes.clear()
            emission = nodes.new("ShaderNodeEmission")
            emission.inputs["Color"].default_value = color
            output = nodes.new("ShaderNodeOutputMaterial")
            material.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
        floor_points = [
            obj.matrix_world @ vertex.co
            for obj in scene.objects
            if obj.get("Room ID") and obj.get("Floor level") == level
            for vertex in obj.data.vertices
        ]
        elevation = max(point.z for point in floor_points) + 1.08
        # Pane ownership and material metadata come from the maintained opening generator.
        panes = [
            obj
            for obj in scene.objects
            if obj.get("Floor level") == level
            and obj.get("Opening ID")
            and obj.get("material_id") == "mat_glass"
        ]
        for pane in panes:
            points = [tuple(pane.matrix_world @ vertex.co) for vertex in pane.data.vertices]
            vertices, faces, slots = glazing_symbol(points, elevation)
            mesh = bpy.data.meshes.new("Temporary / window symbol")
            meshes.append(mesh)
            mesh.from_pydata(vertices, [], faces)
            obj = bpy.data.objects.new(mesh.name, mesh)
            objects.append(obj)
            scene.collection.objects.link(obj)
            obj.visible_shadow = False
            for material in materials:
                mesh.materials.append(material)
            for polygon, slot in zip(mesh.polygons, slots, strict=True):
                polygon.material_index = slot
        yield
    finally:
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            bpy.data.meshes.remove(mesh)
        for material in materials:
            bpy.data.materials.remove(material)
