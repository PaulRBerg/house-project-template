"""Deterministic worlds, lights, cameras, scenes and render-job setup."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .furnishings import ROLE_MATERIALS
from .mesh_descriptors import level_collection
from .persistence import transport_hash
from .render_inventory import (
    INTERIOR_PRESENTATION,
    QUALITY_PROFILES,
    RENDER_CATEGORIES,
    SCENE_CUTAWAYS,
    SHADOW_RESOLUTION_SCALE,
    VIEW_LOOK,
    VIEW_TRANSFORM,
    eevee_lighting,
)

# Plan labels use this style material when the design defines it.
ANNOTATION_INK_MATERIAL_ID = "mat-baseline-site-annotation-ink"
PLAN_LABEL_SUFFIX = "/plan-label"


class PresentationError(ValueError):
    pass


def _matrix(value: Any, field: str) -> list[list[float]]:
    if (
        not isinstance(value, Sequence)
        or len(value) != 4
        or any(not isinstance(row, Sequence) or len(row) != 4 for row in value)
    ):
        raise PresentationError(f"{field} must be a 4x4 matrix")
    result = [[float(item) for item in row] for row in value]
    if any(not math.isfinite(item) for row in result for item in row):
        raise PresentationError(f"{field} values must be finite")
    return result


def compile_presentation(
    design: Mapping[str, Any], compiled: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    components = {item["id"]: item for item in (compiled or {}).get("components", [])}
    lights = []
    for source in sorted(design.get("lights", []), key=lambda item: item["id"]):
        item = dict(source)
        item["matrix"] = _matrix(item.get("matrix"), f"{item['id']}.matrix")
        item["dependency_fingerprint"] = components.get(item["id"], {}).get(
            "fingerprint", transport_hash(item)
        )
        lights.append(item)
    cameras = []
    scenes: dict[str, dict[str, Any]] = {}
    jobs: list[dict[str, Any]] = []
    stems: set[str] = set()
    filenames: set[str] = set()
    for source in sorted(design.get("cameras", []), key=lambda item: item["id"]):
        item = dict(source)
        item["matrix"] = _matrix(item.get("matrix"), f"{item['id']}.matrix")
        item["dependency_fingerprint"] = components.get(item["id"], {}).get(
            "fingerprint", transport_hash(item)
        )
        for scene in item.pop("scene_definitions", []):
            if scene["id"] in scenes and scenes[scene["id"]] != scene:
                raise PresentationError(f"conflicting scene definition {scene['id']!r}")
            scenes[scene["id"]] = dict(scene)
        for job in item.pop("render_jobs", []):
            stem = job["stem"]
            if stem in stems:
                raise PresentationError(f"duplicate render stem {stem!r}")
            if job["filename"] in filenames:
                raise PresentationError(f"duplicate render filename {job['filename']!r}")
            if job["category"] not in RENDER_CATEGORIES:
                raise PresentationError(f"{stem}: unknown category {job['category']!r}")
            stems.add(stem)
            filenames.add(job["filename"])
            jobs.append({**job, "camera_id": item["id"]})
        cameras.append(item)
    _check_scenes(design, scenes, jobs)
    return {
        "generator": {"id": "engine.presentation", "version": "1.0.0"},
        "lights": lights,
        "cameras": cameras,
        "scenes": [scenes[key] for key in sorted(scenes)],
        "render_jobs": sorted(jobs, key=lambda job: job["stem"]),
        "fingerprint": transport_hash(
            {"lights": lights, "cameras": cameras, "scenes": scenes, "jobs": jobs}
        ),
    }


def _check_scenes(
    design: Mapping[str, Any],
    scenes: Mapping[str, Mapping[str, Any]],
    jobs: Sequence[Mapping[str, Any]],
) -> None:
    """Render jobs name declared scenes; floor scenes name design levels; one default at most."""
    levels = {level["id"] for level in design.get("levels", [])}
    for scene_id, scene in scenes.items():
        cutaway = scene.get("cutaway", "none")
        if cutaway not in SCENE_CUTAWAYS:
            raise PresentationError(f"{scene_id}: unknown cutaway {cutaway!r}")
        level = scene.get("level_id")
        if level is not None and level not in levels:
            raise PresentationError(f"{scene_id}: unknown level_id {level!r}")
        if cutaway == "section" and level is None:
            raise PresentationError(f"{scene_id}: a section cutaway needs a level_id")
    for job in jobs:
        if job["scene_id"] not in scenes:
            raise PresentationError(f"{job['stem']}: unknown scene_id {job['scene_id']!r}")
    if sum(bool(job.get("default")) for job in jobs) > 1:
        raise PresentationError("at most one render job may be the default view")


def apply_presentation(
    bpy: Any,
    presentation: Mapping[str, Any],
    *,
    worlds: Mapping[str, Any] | None = None,
) -> dict[str, list[Any]]:
    """Create or update editable cameras, lights and the scene variants."""
    from mathutils import Matrix  # type: ignore

    from .blender_datablocks import configure_light, ensure_collection

    created: dict[str, list[Any]] = {"cameras": [], "lights": [], "scenes": []}
    base_scene = bpy.context.scene
    presentation_collection = ensure_collection(bpy, "Presentation", link_existing=True)
    camera_objects: dict[str, Any] = {}
    base_claimed = False
    procedural_objects: dict[str, Any] = {}
    for obj in bpy.data.objects:
        if obj.get("procedural_id"):
            procedural_objects.setdefault(obj["procedural_id"], obj)

    def object_for(identifier: str, name: str) -> Any | None:
        return procedural_objects.get(identifier) or bpy.data.objects.get(name)

    for item in presentation["cameras"]:
        data = bpy.data.cameras.get(item["id"]) or bpy.data.cameras.new(item["id"])
        data.type = item.get("type", "PERSP")
        data.dof.use_dof = False
        data.lens = float(item.get("lens", 50))
        data.clip_start = float(item.get("clip_start", 0.05))
        data.clip_end = float(item.get("clip_end", 200))
        data.shift_x = float(item.get("shift_x", 0.0))
        data.shift_y = float(item.get("shift_y", 0.0))
        if data.type == "ORTHO":
            data.ortho_scale = float(item["ortho_scale"])
        obj = object_for(item["id"], item["name"]) or bpy.data.objects.new(item["name"], data)
        obj.name = item["name"]
        if presentation_collection not in obj.users_collection:
            presentation_collection.objects.link(obj)
        obj.matrix_world = Matrix(item["matrix"])
        obj["procedural_id"] = item["id"]
        camera_objects[item["id"]] = obj
        created["cameras"].append(obj)
    for item in presentation["lights"]:
        data = bpy.data.lights.get(item["id"]) or bpy.data.lights.new(item["id"], item["type"])
        data.type = item["type"]
        configure_light(data, item)
        obj = object_for(item["id"], item["name"]) or bpy.data.objects.new(item["name"], data)
        obj.name = item["name"]
        if presentation_collection not in obj.users_collection:
            presentation_collection.objects.link(obj)
        obj.matrix_world = Matrix(item["matrix"])
        obj["procedural_id"] = item["id"]
        created["lights"].append(obj)
    # Labels first: their collections must exist before scenes apply collection exclusions.
    configure_annotations(bpy)
    for item in presentation["scenes"]:
        scene = bpy.data.scenes.get(item["name"])
        if scene is None:
            if not base_claimed:
                scene = base_scene
                scene.name = item["name"]
                base_claimed = True
            else:
                scene = base_scene.copy()
                scene.name = item["name"]
        elif scene == base_scene:
            base_claimed = True
        scene.use_fake_user = True
        if presentation_collection not in scene.collection.children[:]:
            scene.collection.children.link(presentation_collection)
        scene.camera = camera_objects[item["camera_id"]]
        if worlds and item.get("world_id") in worlds:
            scene.world = worlds[item["world_id"]]
        scene["procedural_id"] = item["id"]
        scene["cutaway"] = item.get("cutaway", "none")
        configure_scene(scene, item)
        created["scenes"].append(scene)
    configure_mirror_probes(bpy)
    return created


def configure_scene(scene: Any, definition: Mapping[str, Any]) -> None:
    """Persist the same EEVEE settings and collection visibility used by renders."""
    final = QUALITY_PROFILES["eevee"]["final"]
    scene.render.engine = final["engine"]
    scene.render.resolution_x, scene.render.resolution_y = final["resolution"]
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = final["samples"]
    scene.eevee.taa_samples = 16
    scene.eevee.shadow_resolution_scale = SHADOW_RESOLUTION_SCALE
    # Garden, evening and room scenes get ray-traced GI; plan and cutaway scenes stay studio-lit.
    for owner, key, value in eevee_lighting(
        scene.eevee, gi=definition.get("cutaway", "none") == "none"
    ):
        setattr(owner, key, value)
    scene.view_settings.view_transform = definition.get("view_transform", VIEW_TRANSFORM)
    scene.view_settings.look = definition.get("look", VIEW_LOOK)
    # Interiors use the engine's interior balance; other scenes may author their own.
    temperature = definition.get("white_balance_temperature")
    scene.view_settings.use_white_balance = bool(definition.get("interior")) or bool(temperature)
    if definition.get("interior"):
        interior = INTERIOR_PRESENTATION[final["engine"]]
        scene.view_settings.exposure = interior["exposure"]
        scene.view_settings.white_balance_temperature = interior["white_balance_temperature"]
    else:
        scene.view_settings.exposure = float(definition.get("exposure", 0.0))
        if temperature:
            scene.view_settings.white_balance_temperature = float(temperature)
    excluded = set(definition.get("excluded_collections", []))
    scene["excluded_collections"] = sorted(excluded)

    def apply_exclusions(layer_collection):
        for child in layer_collection.children:
            child.exclude = child.name in excluded
            apply_exclusions(child)

    for layer in scene.view_layers:
        apply_exclusions(layer.layer_collection)


def configure_camera_viewport(space: Any) -> None:
    """Look through the scene camera without overlays in one 3D viewport space."""
    space.region_3d.view_perspective = "CAMERA"
    space.clip_end = 300
    space.overlay.show_overlays = False


def _room_floors(bpy: Any) -> dict[str, list[Any]]:
    """Generated finished-floor objects keyed by their room ID."""
    floors: dict[str, list[Any]] = {}
    for obj in bpy.data.objects:
        if obj.get("Room ID"):
            floors.setdefault(obj["Room ID"], []).append(obj)
    return floors


def _room_center(floors: Sequence[Any]) -> list[float]:
    points = [obj.matrix_world @ vertex.co for obj in floors for vertex in obj.data.vertices]
    return [sum(point[axis] for point in points) / len(points) for axis in range(3)]


def configure_annotations(bpy: Any) -> None:
    """Keep one plan label per generated room in its level's Annotations collection.

    Each label's first line is its room ID; floor renders restyle and fit the labels.
    Their collections are linked into every scene so scene exclusions apply to them.
    """
    from mathutils import Matrix, Vector

    from .floor_view_graphics import room_label

    ink = bpy.data.materials.get(ANNOTATION_INK_MATERIAL_ID)
    rooms = _room_floors(bpy)
    # An incremental update keeps old objects, so drop labels of rooms that no longer exist.
    for obj in list(bpy.data.objects):
        label_id = obj.get("procedural_id") or ""
        if (
            label_id.endswith(PLAN_LABEL_SUFFIX)
            and label_id.removesuffix(PLAN_LABEL_SUFFIX) not in rooms
        ):
            curve = obj.data
            bpy.data.objects.remove(obj)
            if curve is not None and curve.users == 0:
                bpy.data.curves.remove(curve)
    for room_id, floors in sorted(rooms.items()):
        room = floors[0]
        family = level_collection(room["Floor level"], "Annotations")
        collection = bpy.data.collections.get(family) or bpy.data.collections.new(family)
        for scene in bpy.data.scenes:
            if collection not in scene.collection.children[:]:
                scene.collection.children.link(collection)
        name = f"{room_id}{PLAN_LABEL_SUFFIX}"
        label = bpy.data.objects.get(name)
        if label is None:
            text = bpy.data.curves.new(name, "FONT")
            text.align_x = "CENTER"
            text.align_y = "TOP_BASELINE"
            text.extrude = 0.0004
            label = bpy.data.objects.new(name, text)
        if collection not in label.users_collection:
            collection.objects.link(label)
        label["procedural_id"] = name
        label.data.body = room_label(room, room_id, cutaway=False)
        center = Vector(_room_center(floors))
        center.z = max((obj.matrix_world @ v.co).z for obj in floors for v in obj.data.vertices)
        center.z += 2.5
        label.matrix_world = Matrix.Translation(center) @ Matrix.Rotation(-math.pi / 2, 4, "Z")
        label.data.size = 0.21
        if ink:
            label.data.materials.clear()
            label.data.materials.append(ink)


def mirror_probe_matrix(points, normal, room_center):
    """Fit a plane probe to a mirror's world bounds with its +Z facing the room."""

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))

    length = math.sqrt(dot(normal, normal))
    normal = [value / length for value in normal]
    center = [sum(p[axis] for p in points) / len(points) for axis in range(3)]
    if (
        dot(normal, [target - source for target, source in zip(room_center, center, strict=True)])
        < 0
    ):
        normal = [-value for value in normal]
    # Mirrors are vertical; align the probe's Y axis with their height.
    right = [-normal[1], normal[0], 0.0]
    length = math.sqrt(dot(right, right))
    right = [value / length for value in right]
    up = [
        normal[1] * right[2] - normal[2] * right[1],
        normal[2] * right[0] - normal[0] * right[2],
        normal[0] * right[1] - normal[1] * right[0],
    ]
    bounds = [
        (min(dot(p, axis) for p in points), max(dot(p, axis) for p in points))
        for axis in (right, up, normal)
    ]
    # The probe sits just in front of the reflective surface, avoiding backface capture.
    offsets = [(low + high) / 2 for low, high in bounds[:2]] + [bounds[2][1] + 0.01]
    center = [
        sum(axis[i] * offset for axis, offset in zip((right, up, normal), offsets, strict=True))
        for i in range(3)
    ]
    half_width, half_height = [(high - low) / 2 for low, high in bounds[:2]]
    return [
        [right[i] * half_width, up[i] * half_height, normal[i], center[i]] for i in range(3)
    ] + [[0, 0, 0, 1]]


def configure_mirror_probes(bpy: Any) -> None:
    """Maintain an EEVEE planar capture in front of every mirror-finished furnishing part."""
    from mathutils import Matrix

    floors = _room_floors(bpy)
    mirrors = [
        obj
        for obj in bpy.data.objects
        if obj.get("material_id") == ROLE_MATERIALS["mirror"] and obj.get("room_id") in floors
    ]
    centers = {
        room_id: _room_center(floors[room_id]) for room_id in {m["room_id"] for m in mirrors}
    }
    for mirror in mirrors:
        identifier = mirror["procedural_id"] + "/reflection-plane"
        probe = bpy.data.objects.get(identifier)
        if probe is None:
            data = bpy.data.lightprobes.new(identifier, "PLANE")
            probe = bpy.data.objects.new(identifier, data)
        # Keep captures with their mirror so all floor/scene exclusions also apply.
        for collection in mirror.users_collection:
            if collection not in probe.users_collection:
                collection.objects.link(probe)
        normal = (
            mirror.matrix_world.to_3x3().inverted().transposed()
            @ max(mirror.data.polygons, key=lambda face: face.area).normal
        )
        points = [tuple(mirror.matrix_world @ vertex.co) for vertex in mirror.data.vertices]
        probe.matrix_world = Matrix(
            mirror_probe_matrix(points, tuple(normal), centers[mirror["room_id"]])
        )
        probe.data.influence_distance = 0.1
        probe.data.clip_start = 0.01
        probe["procedural_id"] = identifier
