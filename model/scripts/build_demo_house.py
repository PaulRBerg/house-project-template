"""Build the repository's small, generic Blender demonstration house."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from math import radians
from typing import Any

FOOTPRINT_X_M = 8.0
FOOTPRINT_Y_M = 6.0
FOOTPRINT_AREA_M2 = FOOTPRINT_X_M * FOOTPRINT_Y_M
WALL_HEIGHT_M = 2.8
WALL_THICKNESS_M = 0.2
SLAB_TOP_M = 0.1
EAVE_HEIGHT_M = SLAB_TOP_M + WALL_HEIGHT_M
RIDGE_HEIGHT_M = 4.2


@dataclass(frozen=True)
class Opening:
    start: float
    end: float
    bottom: float
    top: float


def facade_sections(
    length: float, height: float, openings: tuple[Opening, ...]
) -> list[tuple[float, float, float, float]]:
    """Return center/width/center-height/height rectangles around facade openings."""
    ordered = tuple(sorted(openings, key=lambda opening: opening.start))
    lower = -length / 2
    upper = length / 2
    previous = lower
    for opening in ordered:
        if not (
            lower <= opening.start < opening.end <= upper
            and 0.0 <= opening.bottom < opening.top <= height
            and opening.start >= previous
        ):
            raise ValueError("Facade openings must be ordered, non-overlapping, and in bounds")
        previous = opening.end

    stops = sorted({lower, upper, *(value for item in ordered for value in (item.start, item.end))})
    sections: list[tuple[float, float, float, float]] = []
    for start, end in pairwise(stops):
        midpoint = (start + end) / 2
        opening = next((item for item in ordered if item.start < midpoint < item.end), None)
        width = end - start
        center = midpoint
        if opening is None:
            sections.append((center, width, height / 2, height))
            continue
        if opening.bottom > 0:
            sections.append((center, width, opening.bottom / 2, opening.bottom))
        if opening.top < height:
            remaining = height - opening.top
            sections.append((center, width, opening.top + remaining / 2, remaining))
    return sections


def _append_box(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    center: tuple[float, float, float],
    size: tuple[float, float, float],
) -> None:
    cx, cy, cz = center
    sx, sy, sz = (axis / 2 for axis in size)
    offset = len(vertices)
    vertices.extend(
        [
            (cx - sx, cy - sy, cz - sz),
            (cx + sx, cy - sy, cz - sz),
            (cx + sx, cy + sy, cz - sz),
            (cx - sx, cy + sy, cz - sz),
            (cx - sx, cy - sy, cz + sz),
            (cx + sx, cy - sy, cz + sz),
            (cx + sx, cy + sy, cz + sz),
            (cx - sx, cy + sy, cz + sz),
        ]
    )
    faces.extend(
        [
            tuple(offset + index for index in face)
            for face in (
                (0, 3, 2, 1),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            )
        ]
    )


def _mesh_object(
    bpy: Any,
    collection: Any,
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    material: Any,
) -> Any:
    mesh = bpy.data.meshes.new(f"{name}.Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def _box_object(
    bpy: Any,
    collection: Any,
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    material: Any,
) -> Any:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    _append_box(vertices, faces, center, size)
    return _mesh_object(bpy, collection, name, vertices, faces, material)


def _wall_object(
    bpy: Any,
    collection: Any,
    name: str,
    axis: str,
    coordinate: float,
    length: float,
    openings: tuple[Opening, ...],
    material: Any,
) -> Any:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for center, width, center_z, section_height in facade_sections(length, WALL_HEIGHT_M, openings):
        z = SLAB_TOP_M + center_z
        if axis == "X":
            box_center = (center, coordinate, z)
            box_size = (width, WALL_THICKNESS_M, section_height)
        elif axis == "Y":
            box_center = (coordinate, center, z)
            box_size = (WALL_THICKNESS_M, width, section_height)
        else:
            raise ValueError(f"Unsupported wall axis: {axis}")
        _append_box(vertices, faces, box_center, box_size)
    return _mesh_object(bpy, collection, name, vertices, faces, material)


def _material(
    bpy: Any,
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
    metallic: float = 0.0,
    transmission: float = 0.0,
) -> Any:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    transmission_input = shader.inputs.get("Transmission Weight")
    if transmission_input is not None:
        transmission_input.default_value = transmission
    return material


def _add_roof(bpy: Any, collection: Any, material: Any) -> Any:
    half_x = FOOTPRINT_X_M / 2 + 0.3
    half_y = FOOTPRINT_Y_M / 2 + 0.3
    vertices = [
        (-half_x, -half_y, EAVE_HEIGHT_M),
        (-half_x, 0.0, RIDGE_HEIGHT_M),
        (-half_x, half_y, EAVE_HEIGHT_M),
        (half_x, -half_y, EAVE_HEIGHT_M),
        (half_x, 0.0, RIDGE_HEIGHT_M),
        (half_x, half_y, EAVE_HEIGHT_M),
    ]
    faces = [
        (0, 2, 1),
        (3, 4, 5),
        (0, 1, 4, 3),
        (1, 2, 5, 4),
        (0, 3, 5, 2),
    ]
    return _mesh_object(bpy, collection, "Roof.Gabled", vertices, faces, material)


def _point_camera(camera: Any, target: tuple[float, float, float]) -> None:
    from mathutils import Vector

    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_scene(bpy: Any, builder_source_sha256: str) -> dict[str, Any]:
    """Populate an empty Blender file and return a compact build report."""
    if bpy.data.objects:
        raise RuntimeError("The demonstration builder requires an empty object inventory")

    scene = bpy.context.scene
    scene.name = "Demo House | Illustrative"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene["status"] = "illustrative_unaccepted_demo"
    scene["external_footprint_area_m2"] = FOOTPRINT_AREA_M2
    scene["builder_script"] = "scripts/build_demo_house.py"
    scene["builder_source_sha256"] = builder_source_sha256
    scene["design_notice"] = "Generic demonstration only; not a buildable design."

    collection = bpy.data.collections.new("Illustrative Demo House")
    scene.collection.children.link(collection)

    wall_material = _material(bpy, "Wall | Warm White", (0.78, 0.75, 0.69, 1.0), 0.75)
    slab_material = _material(bpy, "Slab | Pale Concrete", (0.45, 0.47, 0.48, 1.0), 0.9)
    roof_material = _material(bpy, "Roof | Charcoal", (0.09, 0.10, 0.11, 1.0), 0.65)
    ground_material = _material(bpy, "Ground | Neutral Green", (0.18, 0.27, 0.17, 1.0), 1.0)
    door_material = _material(bpy, "Door | Natural Wood", (0.33, 0.16, 0.07, 1.0), 0.55)
    glass_material = _material(
        bpy, "Window | Blue Grey Glass", (0.12, 0.24, 0.30, 1.0), 0.15, transmission=0.5
    )

    _box_object(bpy, collection, "Ground", (0.0, 0.0, -0.18), (16.0, 14.0, 0.15), ground_material)
    _box_object(bpy, collection, "Slab.8x6m", (0.0, 0.0, 0.0), (8.0, 6.0, 0.2), slab_material)

    front_openings = (
        Opening(-2.65, -1.55, 0.0, 2.2),
        Opening(0.55, 2.15, 0.8, 2.05),
    )
    back_openings = (
        Opening(-2.65, -1.25, 0.8, 2.05),
        Opening(1.0, 2.4, 0.8, 2.05),
    )
    east_openings = (Opening(-0.7, 0.7, 0.8, 2.05),)
    _wall_object(bpy, collection, "Wall.Front", "X", -2.9, 8.0, front_openings, wall_material)
    _wall_object(bpy, collection, "Wall.Back", "X", 2.9, 8.0, back_openings, wall_material)
    _wall_object(bpy, collection, "Wall.East", "Y", 3.9, 6.0, east_openings, wall_material)
    _wall_object(bpy, collection, "Wall.West", "Y", -3.9, 6.0, (), wall_material)

    _box_object(bpy, collection, "Door.Front", (-2.1, -3.01, 1.2), (1.0, 0.08, 2.2), door_material)
    window_specs = (
        ("Window.Front", (1.35, -3.01, 1.525), (1.5, 0.05, 1.15)),
        ("Window.Back.Left", (-1.95, 3.01, 1.525), (1.3, 0.05, 1.15)),
        ("Window.Back.Right", (1.7, 3.01, 1.525), (1.3, 0.05, 1.15)),
        ("Window.East", (4.01, 0.0, 1.525), (0.05, 1.3, 1.15)),
    )
    for name, center, size in window_specs:
        _box_object(bpy, collection, name, center, size, glass_material)
    _add_roof(bpy, collection, roof_material)

    camera_data = bpy.data.cameras.new("Camera.Demo.Data")
    camera = bpy.data.objects.new("Camera.Demo", camera_data)
    collection.objects.link(camera)
    camera.location = (11.0, -13.0, 8.5)
    camera_data.lens = 48
    _point_camera(camera, (0.0, 0.0, 1.6))
    scene.camera = camera

    sun_data = bpy.data.lights.new("Sun.Demo.Data", "SUN")
    sun_data.energy = 2.0
    sun_data.angle = radians(25)
    sun = bpy.data.objects.new("Sun.Demo", sun_data)
    collection.objects.link(sun)
    sun.rotation_euler = (radians(28), radians(-18), radians(-35))

    area_data = bpy.data.lights.new("Area.Fill.Data", "AREA")
    area_data.energy = 650
    area_data.shape = "DISK"
    area_data.size = 5.0
    area = bpy.data.objects.new("Area.Fill", area_data)
    collection.objects.link(area)
    area.location = (-4.0, -3.0, 7.0)
    _point_camera(area, (0.0, 0.0, 1.0))

    world = bpy.data.worlds.new("World.Demo") if scene.world is None else scene.world
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.055, 0.075, 0.11, 1.0)
    background.inputs["Strength"].default_value = 0.35

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = "//renders/demo-preview.png"

    readme = bpy.data.texts.new("README | Illustrative demo")
    readme.write(
        "This generic 8 m x 6 m house is an illustrative, unaccepted demonstration.\n"
        "It is not a buildable design or a record of household requirements.\n"
        "Edit the repository builder, then use the guarded workflow to regenerate it.\n"
    )

    bpy.context.view_layer.update()
    return {
        "scene": scene.name,
        "status": scene["status"],
        "external_footprint_area_m2": scene["external_footprint_area_m2"],
        "objects": len(bpy.data.objects),
        "windows": len(window_specs),
    }
