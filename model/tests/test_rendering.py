from copy import deepcopy
from types import SimpleNamespace

import pytest

from engine.render_inventory import INTERIOR_WORLD_ID, sun_rotations
from engine.rendering import exterior_door_pose

# A daylight world whose HDRI sun disc sits at texture azimuth -34.3 deg, 47.9 deg elevation.
STYLE = {
    "materials": [
        {
            "id": INTERIOR_WORLD_ID,
            "role": "world",
            "environment": {
                "map": "exterior/sky.hdr",
                "rotation_deg": 6.0,
                "sun": {"texture_azimuth_deg": -34.3, "elevation_deg": 47.9},
            },
        }
    ]
}
VIEWS = {
    stem: {"scene": "Scene", "camera": "Camera", "stem": stem, "filename": f"{stem}.png", **flags}
    for stem, flags in {
        "interior": {"category": "interiors"},
        "garden": {"category": "exteriors"},
        "site-plan": {"category": "plans"},
        "evening": {"category": "exteriors", "evening": True},
    }.items()
}


@pytest.mark.parametrize("fail", [False, True])
def test_exterior_pose_closes_leaf_and_hardware_and_restores_on_failure(monkeypatch, fail):
    import sys

    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=deepcopy))
    house = [[0, -1, 0, 17], [-1, 0, 0, 18.05], [0, 0, 1, 0], [0, 0, 0, 1]]

    class Object(dict):
        def __init__(self, exterior):
            super().__init__(
                {
                    "Exterior closed pose": exterior,
                    "Door hinge local": "[2, 3, 0]",
                    "Swing degrees": 90,
                }
            )
            self.matrix_world = deepcopy(house)

    leaf, handle, jamb = Object(True), Object(True), Object(False)
    bpy = SimpleNamespace(data=SimpleNamespace(objects=[leaf, handle, jamb]))

    def render():
        with exterior_door_pose(bpy, enabled=True):
            for obj in (leaf, handle):
                opened_vertex = [2, 4, 1, 1]
                world = [
                    sum(a * b for a, b in zip(row, opened_vertex, strict=True))
                    for row in obj.matrix_world
                ]
                assert world == pytest.approx([14, 15.05, 1, 1])
                assert obj["Swing degrees"] == 90
            assert jamb.matrix_world == house
            if fail:
                raise RuntimeError("render failed")

    if fail:
        with pytest.raises(RuntimeError, match="render failed"):
            render()
    else:
        render()
    assert all(obj.matrix_world == house for obj in (leaf, handle, jamb))
    with exterior_door_pose(bpy, enabled=False):
        assert leaf.matrix_world == house


@pytest.mark.parametrize("fail", [False, True])
@pytest.mark.parametrize(
    ("engine", "stem"),
    [
        ("BLENDER_EEVEE", "interior"),
        ("BLENDER_EEVEE", "garden"),
        ("BLENDER_EEVEE", "site-plan"),
        ("BLENDER_EEVEE", "evening"),
        ("CYCLES", "interior"),
    ],
)
def test_render_balances_interior_daylight_and_restores_scene(
    monkeypatch, tmp_path, engine, stem, fail
):
    import sys

    from engine import rendering
    from engine.presentation import configure_scene
    from engine.render_inventory import (
        EEVEE_GI_CATEGORIES,
        EEVEE_LIGHTING,
        EVENING_SUN_ENERGY,
        EXTERIOR_SUN_ENERGY,
        INTERIOR_PRESENTATION,
        SHADOW_RESOLUTION_SCALE,
    )

    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=deepcopy))

    class Object(dict):
        def __init__(self, name, data):
            super().__init__()
            self.name, self.data = name, data

    class Store(dict):
        def __init__(self, factory):
            super().__init__()
            self.factory = factory

        def new(self, name, data):
            result = self.factory(name, data)
            self[name] = result
            return result

        def remove(self, item, **_kwargs):
            del self[item.name]

        def __iter__(self):
            return iter(self.values())

    class Scene(dict):
        pass

    view = VIEWS[stem]
    sun = sun_rotations(STYLE)
    camera = Object(view["camera"], SimpleNamespace(ortho_scale=13.0))
    scene = Scene()
    scene.camera, scene.world = "saved camera", "saved world"
    scene.objects = []
    scene.view_layers = []
    scene.collection = SimpleNamespace(objects=SimpleNamespace(link=lambda _obj: None))
    scene.render = SimpleNamespace(
        engine="BLENDER_EEVEE",
        filepath="saved path",
        resolution_x=600,
        resolution_y=400,
        resolution_percentage=50,
        film_transparent=True,
        image_settings=SimpleNamespace(file_format="JPEG", color_mode="RGBA", color_depth="16"),
    )

    def eevee_settings():
        return SimpleNamespace(
            taa_render_samples=8,
            taa_samples=4,
            shadow_resolution_scale=1.0,
            use_raytracing=False,
            ray_tracing_method="PROBE",
            use_fast_gi=False,
            fast_gi_method="AMBIENT_OCCLUSION_ONLY",
            fast_gi_resolution="4",
            fast_gi_ray_count=1,
            fast_gi_step_count=4,
            fast_gi_distance=3.0,
            shadow_ray_count=1,
            shadow_step_count=1,
            ray_tracing_options=SimpleNamespace(
                resolution_scale="8", trace_max_roughness=0.1, use_denoise=False
            ),
        )

    scene.eevee = eevee_settings()
    scene.cycles = SimpleNamespace(
        device="CPU",
        samples=4,
        use_adaptive_sampling=False,
        adaptive_threshold=0.5,
        use_denoising=False,
        denoiser="OPTIX",
        denoising_use_gpu=False,
        tile_size=2048,
    )
    scene.view_settings = SimpleNamespace(
        view_transform="Standard",
        look="None",
        exposure=1.0,
        use_white_balance=False,
        white_balance_temperature=6500,
    )
    owners = [
        scene.render,
        scene.render.image_settings,
        scene.eevee,
        scene.eevee.ray_tracing_options,
        scene.cycles,
        scene.view_settings,
    ]
    original = [deepcopy(vars(owner)) for owner in owners]
    lights = Store(lambda name, kind: SimpleNamespace(name=name, type=kind))
    objects = Store(Object)
    objects[camera.name] = camera
    window = SimpleNamespace(scene="original active scene")
    interior_world = object()
    bpy = SimpleNamespace(
        context=SimpleNamespace(window=window),
        data=SimpleNamespace(
            scenes={view["scene"]: scene},
            objects=objects,
            lights=lights,
            worlds={INTERIOR_WORLD_ID: interior_world},
        ),
    )

    def render(*, write_still):
        assert write_still
        assert window.scene is scene and scene.camera is camera
        if engine == "CYCLES":
            assert scene.cycles.tile_size >= max(
                scene.render.resolution_x, scene.render.resolution_y
            )
            assert scene.cycles.denoising_use_gpu
        energy = tuple(light.energy for light in lights)
        rotations = tuple(
            obj.rotation_euler for obj in objects if obj.name.startswith("Temporary / ")
        )
        assert rotations == sun
        if engine == "BLENDER_EEVEE":
            assert scene.eevee.shadow_resolution_scale == SHADOW_RESOLUTION_SCALE
            profile = EEVEE_LIGHTING["gi" if view["category"] in EEVEE_GI_CATEGORIES else "studio"]
            for key, value in profile["eevee"].items():
                assert getattr(scene.eevee, key) == value, key
            for key, value in profile.get("ray_tracing_options", {}).items():
                assert getattr(scene.eevee.ray_tracing_options, key) == value, key
            assert scene.eevee.use_raytracing is (view["category"] != "plans")
        else:
            assert vars(scene.eevee.ray_tracing_options) == original[3]
        if view["category"] == "interiors":
            interior = INTERIOR_PRESENTATION[engine]
            assert energy == interior["sun_energy"]
            assert scene.view_settings.exposure == interior["exposure"]
            assert scene.view_settings.use_white_balance
            temperature = interior["white_balance_temperature"]
            assert scene.view_settings.white_balance_temperature == temperature
        else:
            assert scene.world == "saved world"
            assert energy == (EVENING_SUN_ENERGY if view.get("evening") else EXTERIOR_SUN_ENERGY)
            assert scene.view_settings.exposure == 1.0
        if engine == "BLENDER_EEVEE" and view["category"] == "interiors":
            assert scene.world is interior_world
            viewport = Scene()
            viewport.render = SimpleNamespace()
            viewport.eevee = eevee_settings()
            viewport.view_settings = SimpleNamespace()
            viewport.view_layers = []
            configure_scene(viewport, {"interior": True, "cutaway": "none"})
            assert vars(viewport.view_settings) == vars(scene.view_settings)
            assert vars(viewport.eevee.ray_tracing_options) == vars(scene.eevee.ray_tracing_options)
            assert {
                key: value
                for key, value in vars(viewport.eevee).items()
                if key in profile["eevee"] or key == "shadow_resolution_scale"
            } == {
                key: value
                for key, value in vars(scene.eevee).items()
                if key in profile["eevee"] or key == "shadow_resolution_scale"
            }
        if fail:
            raise RuntimeError("render failed")

    bpy.ops = SimpleNamespace(render=SimpleNamespace(render=render))
    monkeypatch.setattr(rendering, "_sha256", lambda _path: "render hash")
    arguments = {
        "view": view,
        "quality": {"engine": engine, "resolution": [900, 600], "samples": 16},
        "output_path": tmp_path / "render.png",
        "sun": sun,
    }
    if fail:
        with pytest.raises(RuntimeError, match="render failed"):
            rendering.render_view_image(bpy, **arguments)
    else:
        result = rendering.render_view_image(bpy, **arguments)
        assert result["settings"]["engine"] == engine
        assert result["settings"]["samples"] == 16
    assert [vars(owner) for owner in owners] == original
    assert scene.camera == "saved camera" and scene.world == "saved world"
    assert window.scene == "original active scene"
    assert not lights and list(objects) == [camera]
    assert bpy.data.worlds == {INTERIOR_WORLD_ID: interior_world}


def _source(rotation):
    """Azimuth and elevation in degrees of the direction a sun with this rotation comes from."""
    import math

    # A light shines along its local -Z; with X = 0 the XYZ Euler sends local +Z, the
    # direction back to the source, to (cos z sin y, sin z sin y, cos y).
    x, y, z = rotation
    assert x == 0.0
    source = (math.cos(z) * math.sin(y), math.sin(z) * math.sin(y), math.cos(y))
    return math.degrees(math.atan2(source[1], source[0])), math.degrees(math.asin(source[2]))


def test_key_sun_follows_the_interior_world_hdri_sun_and_fill_opposes_it():
    key, fill = sun_rotations(STYLE)
    # World azimuth is the texture azimuth minus the world rotation: -34.3 - 6.0.
    assert _source(key) == pytest.approx((-40.3, 47.9), abs=1e-6)
    assert _source(fill) == pytest.approx((139.7, 30.0), abs=1e-6)


def test_sun_rotations_require_the_hdri_sun_position():
    style = deepcopy(STYLE)
    del style["materials"][0]["environment"]["sun"]["elevation_deg"]
    with pytest.raises(ValueError, match="elevation_deg"):
        sun_rotations(style)
