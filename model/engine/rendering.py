"""Shared EEVEE or Cycles rendering for the render queue's views."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any

from .floor_view_graphics import (
    LABEL_PAPER_PADDING,
    fit_floor_labels,
    floor_window_symbols,
    room_label,
)
from .mesh_descriptors import level_collection
from .persistence import sha256_file as _sha256
from .render_inventory import (
    CUTAWAY_SUN_ENERGY,
    EEVEE_GI_CATEGORIES,
    EVENING_SUN_ENERGY,
    EXTERIOR_SUN_ENERGY,
    FLOOR_SUN_ENERGY,
    INTERIOR_PRESENTATION,
    INTERIOR_WORLD_ID,
    SHADOW_RESOLUTION_SCALE,
    VIEW_LOOK,
    VIEW_TRANSFORM,
    eevee_lighting,
)
from .transforms import multiply, rotation_xyz, translation

# Cycles stops sampling converged pixels early and denoises on the configured GPU.
CYCLES_ADAPTIVE_THRESHOLD = 0.01
# One tile covers every supported resolution: a single adaptive-sampling and denoise pass
# instead of a 2048 px grid with per-tile overscan and a tile EXR round-trip.
CYCLES_TILE_SIZE = 8192

# Off-white graphic backdrop and label cards for the furnished cutaways.
CUTAWAY_BACKDROP = (0.95, 0.93, 0.90, 1)


@contextmanager
def exterior_door_pose(bpy: Any, *, enabled: bool):
    """Close authored entry leaves and hardware for exteriors, restoring even on failure."""
    originals = []
    try:
        if enabled:
            from mathutils import Matrix

            for obj in bpy.data.objects:
                if not obj.get("Exterior closed pose"):
                    continue
                original = obj.matrix_world.copy()
                originals.append((obj, original))
                x, y, z = json.loads(obj["Door hinge local"])
                rotation = rotation_xyz(0, 0, -math.radians(obj["Swing degrees"]))
                around_hinge = multiply(
                    translation(x, y, z), multiply(rotation, translation(-x, -y, -z))
                )
                obj.matrix_world = Matrix(multiply(original, around_hinge))
        yield
    finally:
        for obj, original in originals:
            obj.matrix_world = original


def render_view_image(
    bpy: Any,
    *,
    view: Mapping[str, Any],
    quality: Mapping[str, Any],
    output_path: str | Path,
    sun: tuple[Any, Any],
) -> dict[str, Any]:
    """Render exactly one image so cancellation is observed between calls.

    ``view`` is one ``render_inventory.render_views`` entry and ``sun`` the key and fill
    rotations from ``render_inventory.sun_rotations``.
    """

    scene = bpy.data.scenes[view["scene"]]
    camera = bpy.data.objects[view["camera"]]
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    original_scene = bpy.context.window.scene
    original = [
        (scene, "camera", scene.camera),
        (scene, "world", scene.world),
        (scene.render, "engine", scene.render.engine),
        (scene.render, "filepath", scene.render.filepath),
        (scene.render, "resolution_x", scene.render.resolution_x),
        (scene.render, "resolution_y", scene.render.resolution_y),
        (scene.render, "resolution_percentage", scene.render.resolution_percentage),
        (scene.render, "film_transparent", scene.render.film_transparent),
        (
            scene.render.image_settings,
            "file_format",
            scene.render.image_settings.file_format,
        ),
        (
            scene.render.image_settings,
            "color_mode",
            scene.render.image_settings.color_mode,
        ),
        (
            scene.render.image_settings,
            "color_depth",
            scene.render.image_settings.color_depth,
        ),
        (scene.eevee, "taa_render_samples", scene.eevee.taa_render_samples),
        (scene.eevee, "shadow_resolution_scale", scene.eevee.shadow_resolution_scale),
        (scene.cycles, "device", scene.cycles.device),
        (scene.cycles, "samples", scene.cycles.samples),
        (scene.cycles, "use_adaptive_sampling", scene.cycles.use_adaptive_sampling),
        (scene.cycles, "adaptive_threshold", scene.cycles.adaptive_threshold),
        (scene.cycles, "use_denoising", scene.cycles.use_denoising),
        (scene.cycles, "denoiser", scene.cycles.denoiser),
        (scene.cycles, "denoising_use_gpu", scene.cycles.denoising_use_gpu),
        (scene.cycles, "tile_size", scene.cycles.tile_size),
        (scene.view_settings, "view_transform", scene.view_settings.view_transform),
        (scene.view_settings, "look", scene.view_settings.look),
        (scene.view_settings, "exposure", scene.view_settings.exposure),
        (scene.view_settings, "use_white_balance", scene.view_settings.use_white_balance),
        (
            scene.view_settings,
            "white_balance_temperature",
            scene.view_settings.white_balance_temperature,
        ),
        (camera.data, "ortho_scale", camera.data.ortho_scale),
    ]
    level = view.get("floor")
    floor_view = level is not None
    cutaway = bool(view.get("cutaway"))
    category = view.get("category")
    interior = INTERIOR_PRESENTATION[quality["engine"]] if category == "interiors" else None
    cycles = quality["engine"] == "CYCLES"
    lighting = [] if cycles else eevee_lighting(scene.eevee, gi=category in EEVEE_GI_CATEGORIES)
    original.extend((owner, key, getattr(owner, key)) for owner, key, _ in lighting)
    soft_world = None
    hidden_lights: list[tuple[Any, bool]] = []
    temporary_lights = []
    original_labels = []
    label_plates = []
    plate_material = None
    wall_meshes = []
    wall_materials = []
    hidden_curtains = []
    drawing_overlays = ExitStack()
    try:
        bpy.context.window.scene = scene
        scene.camera = camera
        scene.render.engine = quality["engine"]
        scene.render.resolution_x, scene.render.resolution_y = quality["resolution"]
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = False
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGB"
        scene.render.image_settings.color_depth = "8"
        if cycles:
            scene.cycles.device = "GPU"
            scene.cycles.samples = int(quality["samples"])
            scene.cycles.use_adaptive_sampling = True
            scene.cycles.adaptive_threshold = CYCLES_ADAPTIVE_THRESHOLD
            scene.cycles.use_denoising = True
            scene.cycles.denoiser = "OPENIMAGEDENOISE"
            scene.cycles.denoising_use_gpu = True
            scene.cycles.tile_size = CYCLES_TILE_SIZE
        else:
            scene.eevee.taa_render_samples = int(quality["samples"]) * (4 if cutaway else 1)
            scene.eevee.shadow_resolution_scale = SHADOW_RESOLUTION_SCALE
            for owner, key, value in lighting:
                setattr(owner, key, value)
        scene.view_settings.view_transform = VIEW_TRANSFORM
        scene.view_settings.look = VIEW_LOOK
        if interior:
            if not cycles:
                scene.world = bpy.data.worlds[INTERIOR_WORLD_ID]
            scene.view_settings.exposure = interior["exposure"]
            scene.view_settings.use_white_balance = True
            scene.view_settings.white_balance_temperature = interior["white_balance_temperature"]
        if floor_view:
            soft_world = bpy.data.worlds.new("Temporary / plan studio")
            soft_world.use_nodes = True
            background = soft_world.node_tree.nodes.get("Background")
            background.inputs["Color"].default_value = (
                CUTAWAY_BACKDROP if cutaway else (0.75, 0.80, 0.90, 1)
            )
            background.inputs["Strength"].default_value = 0.45 if cutaway else 0.8
            if cutaway:
                # Separate the graphic backdrop from the bright studio environment.
                nodes = soft_world.node_tree.nodes
                links = soft_world.node_tree.links
                backdrop = nodes.new("ShaderNodeBackground")
                backdrop.inputs["Color"].default_value = CUTAWAY_BACKDROP
                backdrop.inputs["Strength"].default_value = 3.0
                rays = nodes.new("ShaderNodeLightPath")
                mix = nodes.new("ShaderNodeMixShader")
                links.new(rays.outputs["Is Camera Ray"], mix.inputs[0])
                links.new(background.outputs[0], mix.inputs[1])
                links.new(backdrop.outputs[0], mix.inputs[2])
                links.new(mix.outputs[0], nodes.get("World Output").inputs["Surface"])
            scene.world = soft_world
            scene.view_settings.exposure = 0.0
            for obj in scene.objects:
                if obj.type == "LIGHT":
                    hidden_lights.append((obj, obj.hide_render))
                    obj.hide_render = True
        if cutaway:
            # Graphic section colors are temporary: never alter the specified finishes.
            for name, color in (
                ("wall face", (0.88, 0.86, 0.82, 1)),
                ("section edge", (0.52, 0.50, 0.47, 1)),
            ):
                material = bpy.data.materials.new("Temporary / " + name)
                material.use_nodes = True
                shader = material.node_tree.nodes.get("Principled BSDF")
                shader.inputs["Base Color"].default_value = color
                shader.inputs["Roughness"].default_value = 0.92
                wall_materials.append(material)
            for obj in bpy.data.collections[level_collection(level, "Walls low")].objects:
                mesh = obj.data.copy()
                wall_meshes.append((obj, obj.data, mesh))
                obj.data = mesh
                mesh.materials.clear()
                for material in wall_materials:
                    mesh.materials.append(material)
                for polygon in mesh.polygons:
                    polygon.material_index = int(polygon.normal.z > 0.9)
            # Drapes and ceiling-level fixtures would float above the low section cut.
            for obj in scene.objects:
                if obj.get("Cutaway hidden") or "full-height linen curtain" in obj.name:
                    hidden_curtains.append((obj, obj.hide_render))
                    obj.hide_render = True
        if floor_view:
            from mathutils import Matrix

            floors = {obj.get("Room ID"): obj for obj in scene.objects if obj.get("Room ID")}
            floor_labels = []
            for label in bpy.data.collections[level_collection(level, "Annotations")].objects:
                original_labels.append(
                    (label, label.matrix_world.copy(), label.data.body, label.data.size)
                )
                room_id = label.data.body.splitlines()[0]
                room = floors[room_id]
                floor_labels.append((label, room_id))
                anchor = label.matrix_world.translation.copy()
                anchor.z = (
                    max((room.matrix_world @ vertex.co).z for vertex in room.data.vertices) + 0.08
                )
                # Move toward the orthographic camera without shifting the room's screen anchor.
                anchor += camera.matrix_world.col[2].xyz * 10.0
                label.matrix_world = (
                    Matrix.Translation(anchor)
                    @ camera.matrix_world.to_quaternion().to_matrix().to_4x4()
                )
                label.data.size = 0.19 if cutaway else 0.21
                label.data.body = room_label(room, room_id, cutaway=cutaway)
            fit_floor_labels(bpy, scene, camera, floor_labels)
            drawing_overlays.enter_context(floor_window_symbols(bpy, scene, level))
            plate_material = bpy.data.materials.new("Temporary / label paper")
            plate_material.use_nodes = True
            nodes = plate_material.node_tree.nodes
            nodes.clear()
            emission = nodes.new("ShaderNodeEmission")
            emission.inputs["Color"].default_value = CUTAWAY_BACKDROP if cutaway else (1, 1, 1, 1)
            output_node = nodes.new("ShaderNodeOutputMaterial")
            plate_material.node_tree.links.new(emission.outputs[0], output_node.inputs["Surface"])
            for label, _, _, _ in original_labels:
                px, py = LABEL_PAPER_PADDING
                x0 = min(point[0] for point in label.bound_box) - px
                x1 = max(point[0] for point in label.bound_box) + px
                y0 = min(point[1] for point in label.bound_box) - py
                y1 = max(point[1] for point in label.bound_box) + py
                mesh = bpy.data.meshes.new("Temporary / label paper")
                mesh.from_pydata(
                    [
                        (x0, y0, -0.01),
                        (x1, y0, -0.01),
                        (x1, y1, -0.01),
                        (x0, y1, -0.01),
                    ],
                    [],
                    [(0, 1, 2, 3)],
                )
                plate = bpy.data.objects.new(mesh.name, mesh)
                scene.collection.objects.link(plate)
                plate.matrix_world = label.matrix_world.copy()
                mesh.materials.append(plate_material)
                label_plates.append((plate, mesh))
        # Direct light supplements the authored environment and room fixtures.
        # Interior EEVEE daylight leaves more contrast for the authored fixture layers.
        evening = bool(view.get("evening"))
        if floor_view:
            sun_energy = CUTAWAY_SUN_ENERGY if cutaway else FLOOR_SUN_ENERGY
        elif interior:
            sun_energy = interior["sun_energy"]
        else:
            sun_energy = EVENING_SUN_ENERGY if evening else EXTERIOR_SUN_ENERGY
        for name, rotation, energy in zip(("key", "fill"), sun, sun_energy, strict=True):
            light = bpy.data.lights.new("Temporary / " + name, "SUN")
            light.energy = energy
            light.angle = 0.5
            obj = bpy.data.objects.new(light.name, light)
            scene.collection.objects.link(obj)
            obj.rotation_euler = rotation
            temporary_lights.append((obj, light))
        scene.render.filepath = str(output)
        started = time.monotonic()
        with exterior_door_pose(bpy, enabled=category == "exteriors"):
            bpy.ops.render.render(write_still=True)
        seconds = round(time.monotonic() - started, 6)
        settings = {
            "engine": scene.render.engine,
            "resolution": list(quality["resolution"]),
            **(
                {
                    "samples": scene.cycles.samples,
                    "adaptive_threshold": scene.cycles.adaptive_threshold,
                    "denoiser": scene.cycles.denoiser,
                }
                if cycles
                else {
                    "samples": scene.eevee.taa_render_samples,
                    "raytracing": scene.eevee.use_raytracing,
                    "fast_gi": scene.eevee.use_fast_gi,
                    "shadow_resolution_scale": scene.eevee.shadow_resolution_scale,
                }
            ),
            "lighting": "warm white / neutral section studio"
            if cutaway
            else (
                "soft studio"
                if floor_view
                else "authored scene with key/fill suns"
                + (
                    f", {scene.view_settings.white_balance_temperature:.0f} K interior white balance"
                    if category == "interiors"
                    else ""
                )
            ),
            "view_transform": scene.view_settings.view_transform,
            "look": scene.view_settings.look,
            "exposure": scene.view_settings.exposure,
        }
    finally:
        drawing_overlays.close()
        for owner, key, value in original:
            setattr(owner, key, value)
        for obj, hidden in hidden_lights:
            obj.hide_render = hidden
        for obj, hidden in hidden_curtains:
            obj.hide_render = hidden
        for obj, original_mesh, mesh in wall_meshes:
            obj.data = original_mesh
            bpy.data.meshes.remove(mesh)
        for material in wall_materials:
            bpy.data.materials.remove(material)
        for plate, mesh in label_plates:
            bpy.data.objects.remove(plate, do_unlink=True)
            bpy.data.meshes.remove(mesh)
        if plate_material is not None:
            bpy.data.materials.remove(plate_material)
        for label, matrix, body, size in original_labels:
            label.matrix_world = matrix
            label.data.body = body
            label.data.size = size
        for obj, light in temporary_lights:
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.lights.remove(light)
        if soft_world is not None:
            bpy.data.worlds.remove(soft_world)
        bpy.context.window.scene = original_scene
    return {
        "path": str(output),
        "sha256": _sha256(output),
        "seconds": seconds,
        "settings": settings,
    }
