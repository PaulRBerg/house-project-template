"""Render queue derivation, delivery filenames and quality profiles; stdlib only.

``render_views`` reads the queue from the ``render_jobs`` and ``scene_definitions`` that
``design/style.json`` cameras declare, in declaration order. Floor views name their
``floor`` (the scene's ``level_id``); furnished cutaways also set ``cutaway``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

# Engine-defined render categories: each names an output folder and a lighting path.
RENDER_CATEGORIES = ("exteriors", "interiors", "plans")
# Scene ``cutaway`` modes: ``none`` renders the authored scene, ``plan`` an orthographic
# floor or site plan and ``section`` a furnished cutaway of one level.
SCENE_CUTAWAYS = ("none", "plan", "section")


def render_views(style: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the render queue the style's cameras declare, in declaration order."""
    scenes = {
        definition["id"]: definition
        for camera in style["cameras"]
        for definition in camera.get("scene_definitions", [])
    }
    views = []
    for camera in style["cameras"]:
        for job in camera.get("render_jobs", []):
            scene = scenes.get(job["scene_id"])
            if scene is None:
                raise ValueError(f"{job['stem']}: unknown scene_id {job['scene_id']!r}")
            view = {
                "scene": scene["name"],
                "camera": camera["name"],
                "stem": job["stem"],
                "filename": job["filename"],
                "category": job["category"],
                "default": bool(job.get("default")),
            }
            if scene.get("level_id"):
                view["floor"] = scene["level_id"]
            if scene.get("cutaway") == "section":
                view["cutaway"] = True
            if scene.get("evening"):
                view["evening"] = True
            views.append(view)
    return views


def default_view(style: Mapping[str, Any]) -> dict[str, Any]:
    """The view the saved file and the interactive presentation open on.

    A job flagged ``default`` wins; otherwise the first declared job.
    """
    views = render_views(style)
    if not views:
        raise ValueError("style.json cameras declare no render_jobs")
    return next((view for view in views if view["default"]), views[0])


DRAWING_FILENAMES = {
    "parcel-ground-drawing.png": "Plan arhitectural parter.png",
    "parcel-upper-drawing.png": "Plan arhitectural etaj.png",
    "parcel-ground-structure.png": "Plan structura parter.png",
    "parcel-upper-structure.png": "Plan structura etaj.png",
}

VIEW_TRANSFORM = "AgX"
VIEW_LOOK = "AgX - Medium High Contrast"
# A separate authored sky restrains EEVEE's unoccluded interior environment fill.
INTERIOR_WORLD_ID = "world-interior-daylight"
# Interior colour management and temporary key/fill sun energies per engine. EEVEE
# interiors are lit mostly by the blue daylight HDRI sky, so 7500 K neutralizes its cast.
INTERIOR_PRESENTATION = {
    "BLENDER_EEVEE": {
        "white_balance_temperature": 7500,
        "exposure": 0.3,
        "sun_energy": (1.0, 0.2),
    },
    "CYCLES": {
        "white_balance_temperature": 5000,
        "exposure": 0.0,
        "sun_energy": (3.0, 0.8),
    },
}
# The fill sun shines from opposite the key at this elevation.
SUN_FILL_ELEVATION_DEG = 30.0


def sun_rotations(style: Mapping[str, Any]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return the temporary key and fill sun ``Object.rotation_euler`` (XYZ radians).

    A sun shines along its local -Z. The key comes from the HDRI sun of the interior
    daylight world, so interior sunlight agrees with the sky the windows show: its
    ``environment.sun`` records where the sun disc sits in the map
    (``texture_azimuth_deg``, ``elevation_deg``), and the world azimuth is that texture
    azimuth minus the world's ``rotation_deg``. The fill comes from the opposite side.
    """
    world = next((item for item in style["materials"] if item["id"] == INTERIOR_WORLD_ID), None)
    environment = (world or {}).get("environment", {})
    sun = environment.get("sun", {})
    if "texture_azimuth_deg" not in sun or "elevation_deg" not in sun:
        raise ValueError(
            f"{INTERIOR_WORLD_ID} needs environment.sun.texture_azimuth_deg and elevation_deg"
        )
    azimuth = float(sun["texture_azimuth_deg"]) - float(environment.get("rotation_deg", 0.0))

    def rotation(azimuth_deg: float, elevation_deg: float) -> tuple[float, ...]:
        return (0.0, math.radians(90.0 - elevation_deg), math.radians(azimuth_deg))

    return (
        rotation(azimuth, float(sun["elevation_deg"])),
        rotation(azimuth + 180.0, SUN_FILL_ELEVATION_DEG),
    )


# Temporary key/fill sun energies for the other views. Exterior HDRI worlds extract their
# own shadowing sun, so a temporary key would cast a second shadow set. Evening views keep
# only a faint fill under the low evening sky.
EXTERIOR_SUN_ENERGY = (0.0, 0.0)
EVENING_SUN_ENERGY = (0.0, 0.08)
FLOOR_SUN_ENERGY = (2.0, 0.6)
CUTAWAY_SUN_ENERGY = (2.2, 1.0)
# Full-scale shadow maps from the authored fixtures overflow EEVEE's shadow pool and drop
# shadows; 0.75 fits the pool and matches an overflow-free full-scale render.
SHADOW_RESOLUTION_SCALE = 0.75
# EEVEE lighting profiles as Blender 5.2 property names, keyed by owner: ``eevee`` is
# ``Scene.eevee`` (SceneEEVEE) and ``ray_tracing_options`` is its RaytraceEEVEE. ``gi``
# screen-traces reflections and refraction up to ``trace_max_roughness`` and resolves
# rougher (diffuse) surfaces with fast GI horizon scan, so interiors receive bounce light;
# a ``trace_max_roughness`` of 1.0 would disable fast GI. ``studio`` keeps the plan and
# cutaway views flat and cheap.
EEVEE_LIGHTING = {
    "gi": {
        "eevee": {
            "use_raytracing": True,
            "ray_tracing_method": "SCREEN",
            "use_fast_gi": True,
            "fast_gi_method": "GLOBAL_ILLUMINATION",
            "fast_gi_resolution": "2",
            "fast_gi_ray_count": 2,
            "fast_gi_step_count": 8,
            "fast_gi_distance": 0.0,
            "shadow_ray_count": 2,
            "shadow_step_count": 6,
        },
        "ray_tracing_options": {
            "resolution_scale": "2",
            "trace_max_roughness": 0.5,
            "use_denoise": True,
        },
    },
    "studio": {"eevee": {"use_raytracing": False, "use_fast_gi": False}},
}
# Render categories lit with the ``gi`` profile; every other view uses ``studio``.
EEVEE_GI_CATEGORIES = frozenset({"exteriors", "interiors"})


def eevee_lighting(eevee, *, gi):
    """Return ``(owner, property, value)`` for one EEVEE lighting profile on ``Scene.eevee``."""
    profile = EEVEE_LIGHTING["gi" if gi else "studio"]
    return [
        (eevee if owner == "eevee" else getattr(eevee, owner), key, value)
        for owner, settings in profile.items()
        for key, value in settings.items()
    ]


# EEVEE is the default; Cycles path-traces higher-quality, much slower images on request.
# Cycles interiors are sample-bound (0.37 s per sample at 3600 x 2400 on the M5 Max) and
# adaptive sampling stops nothing at the 0.01 threshold, so the sample cap sets the time.
# 256 denoised samples are indistinguishable from 512 at 100 % and render in half the time.
QUALITY_PROFILES = {
    "eevee": {
        "preview": {"resolution": [900, 600], "samples": 16, "engine": "BLENDER_EEVEE"},
        "final": {"resolution": [1800, 1200], "samples": 32, "engine": "BLENDER_EEVEE"},
    },
    "cycles": {
        "preview": {"resolution": [1200, 800], "samples": 128, "engine": "CYCLES"},
        "final": {"resolution": [3600, 2400], "samples": 256, "engine": "CYCLES"},
    },
}
