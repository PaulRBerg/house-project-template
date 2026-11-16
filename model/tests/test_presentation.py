import sys
from copy import deepcopy
from types import SimpleNamespace

import pytest

from engine.presentation import (
    PresentationError,
    apply_presentation,
    compile_presentation,
    configure_annotations,
    configure_scene,
)
from engine.render_inventory import EEVEE_LIGHTING, SHADOW_RESOLUTION_SCALE, render_views


@pytest.mark.parametrize("reuse", [False, True])
def test_camera_refresh_disables_depth_of_field_in_new_and_reused_data(monkeypatch, reuse):
    class Object(dict):
        def __init__(self, name, data):
            super().__init__(procedural_id="camera-test")
            self.name, self.data, self.users_collection = name, data, []

    class Objects(list):
        def get(self, name):
            return next((obj for obj in self if obj.name == name), None)

        def new(self, name, data):
            obj = Object(name, data)
            self.append(obj)
            return obj

    class Cameras(dict):
        def new(self, name):
            self[name] = SimpleNamespace(dof=SimpleNamespace(use_dof=True))
            return self[name]

    cameras, objects = Cameras(), Objects()
    original = cameras.new("camera-test") if reuse else None
    if reuse:
        objects.append(Object("Existing camera", original))
    collection = SimpleNamespace(
        objects=SimpleNamespace(link=lambda obj: obj.users_collection.append(collection))
    )
    base = SimpleNamespace(collection=SimpleNamespace(children=[collection]))
    bpy = SimpleNamespace(
        context=SimpleNamespace(scene=base),
        data=SimpleNamespace(
            cameras=cameras, objects=objects, collections={"Presentation": collection}, materials={}
        ),
    )
    monkeypatch.setitem(
        sys.modules, "mathutils", SimpleNamespace(Matrix=lambda value: value, Vector=object)
    )
    definition = {
        "cameras": [{"id": "camera-test", "name": "Camera", "matrix": [[1]], "lens": 28}],
        "lights": [],
        "scenes": [],
    }

    result = apply_presentation(bpy, definition)

    [camera] = result["cameras"]
    assert camera.data is cameras["camera-test"]
    if reuse:
        assert camera.data is original
    assert camera.data.dof.use_dof is False
    assert camera.data.lens == 28 and len(objects) == 1


def test_scenes_cover_the_render_inventory_and_isolate_floors(design):
    result = compile_presentation(design)
    assert {job["stem"] for job in result["render_jobs"]} == {
        view["stem"] for view in render_views(design)
    }
    levels = [level["id"] for level in design["levels"]]
    for scene in result["scenes"]:
        excluded = set(scene["excluded_collections"])
        own = scene.get("level_id")
        if own is None:
            # Eye-level and site views hide every plan label.
            if scene["cutaway"] == "none":
                assert {"Site | Annotations", *(f"{level} | Annotations" for level in levels)} <= (
                    excluded
                ), scene["id"]
            continue
        for other in levels:
            if other != own:
                assert f"{other} | Floors" in excluded, scene["id"]
                assert f"{other} | Annotations" in excluded, scene["id"]
        assert f"{own} | Floors" not in excluded, scene["id"]


def test_duplicate_render_stem_is_rejected(design):
    changed = deepcopy(design)
    first = next(item for item in changed["cameras"] if item["render_jobs"])
    second = next(item for item in changed["cameras"] if item is not first and item["render_jobs"])
    second["render_jobs"][0]["stem"] = first["render_jobs"][0]["stem"]
    with pytest.raises(PresentationError, match="duplicate render stem"):
        compile_presentation(changed)


def test_scene_refresh_preserves_identity():
    class Scene(dict):
        render = SimpleNamespace()
        eevee = SimpleNamespace(ray_tracing_options=SimpleNamespace())
        view_settings = SimpleNamespace()
        view_layers = []

    scene = Scene({"procedural_id": "scene-garden", "uuid": "addon-owned"})

    configure_scene(scene, {"excluded_collections": ["U | Annotations"]})
    configure_scene(scene, {"excluded_collections": ["U | Annotations"]})

    assert dict(scene) == {
        "procedural_id": "scene-garden",
        "uuid": "addon-owned",
        "excluded_collections": ["U | Annotations"],
    }
    assert scene.render.engine == "BLENDER_EEVEE"


def test_resized_room_refreshes_its_plan_label_without_changing_identity(monkeypatch):
    class Vector(list):
        @property
        def z(self):
            return self[2]

        @z.setter
        def z(self, value):
            self[2] = value

    class Matrix:
        @staticmethod
        def Translation(center):
            return Identity(tuple(center))

        @staticmethod
        def Rotation(*_args):
            return Identity()

    class Identity:
        def __init__(self, translation=None):
            self.translation = translation

        def __matmul__(self, other):
            return other if self.translation is None else self

    class Store(dict):
        def __iter__(self):
            return iter(self.values())

        def new(self, name, data=None):
            self[name] = Label(name, data) if data is not None else Collection(name)
            return self[name]

    class Collection(SimpleNamespace):
        def __init__(self, name):
            super().__init__(name=name, objects=SimpleNamespace(link=self._link))

        def _link(self, obj):
            obj.users_collection.append(self)

    class Label(dict):
        def __init__(self, name, data):
            super().__init__()
            self.name, self.data, self.users_collection = name, data, []

    class Curves(dict):
        def new(self, name, _kind):
            self[name] = SimpleNamespace(body="", materials=[])
            return self[name]

    class Children(list):
        def link(self, collection):
            self.append(collection)

    class Room(dict):
        matrix_world = Identity()
        data = SimpleNamespace(
            vertices=[SimpleNamespace(co=Vector((x, y, 3.3))) for x in (0, 4) for y in (0, 3)]
        )

    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=Matrix, Vector=Vector))
    room = Room(
        {
            "Room ID": "U-CHILD",
            "Room name": "Camera copilului",
            "Floor level": "U",
            "Room total area m²": 12.4353,
        }
    )
    objects = Store(floor=room)
    scene = SimpleNamespace(collection=SimpleNamespace(children=Children()))
    bpy = SimpleNamespace(
        data=SimpleNamespace(
            objects=objects,
            materials={},
            collections=Store(),
            curves=Curves(),
            scenes=[scene],
        )
    )

    configure_annotations(bpy)
    label = objects["U-CHILD/plan-label"]
    assert label.data.body == "U-CHILD\nCamera copilului\n12.4 m²"
    assert [collection.name for collection in label.users_collection] == ["U | Annotations"]
    assert scene.collection.children == label.users_collection
    assert label.matrix_world.translation == pytest.approx((2.0, 1.5, 5.8))

    room["Room total area m²"] = 14.766
    configure_annotations(bpy)
    assert objects["U-CHILD/plan-label"] is label
    assert label.data.body == "U-CHILD\nCamera copilului\n14.8 m²"
    assert len(label.users_collection) == 1 and len(scene.collection.children) == 1


def test_level_scenes_hide_the_frame_and_other_scenes_show_it(design):
    scenes = {scene["id"]: scene for scene in compile_presentation(design)["scenes"]}
    frames = {f"{level['id']} | Frame" for level in design["levels"]}
    for scene_id, scene in scenes.items():
        excluded = set(scene["excluded_collections"])
        if scene.get("level_id"):
            assert frames <= excluded, scene_id
        else:
            assert not frames & excluded, scene_id


def test_saved_scenes_persist_gi_for_eye_level_views_and_studio_for_plans(design):
    class Scene(dict):
        pass

    scenes = compile_presentation(design)["scenes"]
    lit = set()
    for definition in scenes:
        scene = Scene()
        scene.render = SimpleNamespace()
        scene.eevee = SimpleNamespace(ray_tracing_options=SimpleNamespace())
        scene.view_settings = SimpleNamespace()
        scene.view_layers = []
        configure_scene(scene, definition)
        profile = EEVEE_LIGHTING["gi" if scene.eevee.use_raytracing else "studio"]
        assert {key: getattr(scene.eevee, key) for key in profile["eevee"]} == profile["eevee"]
        assert vars(scene.eevee.ray_tracing_options) == profile.get("ray_tracing_options", {})
        assert scene.eevee.shadow_resolution_scale == SHADOW_RESOLUTION_SCALE
        if scene.eevee.use_raytracing:
            lit.add(definition["id"])
    assert lit == {
        definition["id"] for definition in scenes if definition.get("cutaway", "none") == "none"
    }
    interiors = {definition["id"] for definition in scenes if definition.get("interior")}
    assert interiors and interiors <= lit
    assert {definition["id"] for definition in scenes if definition.get("level_id")}.isdisjoint(lit)


@pytest.mark.parametrize(
    ("definition", "balanced", "temperature"),
    [({"white_balance_temperature": 7500}, True, 7500.0), ({}, False, None)],
)
def test_scene_may_author_its_own_white_balance(definition, balanced, temperature):
    class Scene(dict):
        pass

    scene = Scene()
    scene.render = SimpleNamespace()
    scene.eevee = SimpleNamespace(ray_tracing_options=SimpleNamespace())
    scene.view_settings = SimpleNamespace(white_balance_temperature=None)
    scene.view_layers = []
    configure_scene(scene, {"exposure": -0.35, **definition})
    assert scene.view_settings.use_white_balance is balanced
    assert scene.view_settings.white_balance_temperature == temperature
    assert scene.view_settings.exposure == -0.35


@pytest.mark.parametrize("side", [-1, 1])
def test_mirror_probe_fits_moved_surface_and_faces_room(side):
    from engine.presentation import mirror_probe_matrix

    # Bounds describe four disconnected door fronts, with a thin backing thickness.
    points = [(x, y, z) for x in (13, 15.3) for y in (6, 6.02) for z in (4.1, 5.7)]
    matrix = mirror_probe_matrix(points, (0, 1, 0), (14, 6.01 + side, 4.2))
    assert [row[2] for row in matrix[:3]] == [0, side, 0]
    assert [row[3] for row in matrix[:3]] == pytest.approx(
        [14.15, 6.03 if side == 1 else 5.99, 4.9]
    )
    assert sum(row[0] ** 2 for row in matrix[:3]) ** 0.5 == pytest.approx(1.15)
    assert sum(row[1] ** 2 for row in matrix[:3]) ** 0.5 == pytest.approx(0.8)
    # A right-handed probe frame is required even when the house transform is mirrored.
    assert matrix[0][0] * matrix[2][1] * matrix[1][2] * -1 > 0


def test_mirror_probe_refresh_reuses_capture_and_follows_wardrobe_collections(monkeypatch):
    from engine.presentation import configure_mirror_probes

    class Matrix:
        def __matmul__(self, value):
            return value

        def to_3x3(self):
            return self

        def inverted(self):
            return self

        def transposed(self):
            return self

    class Object(dict):
        def __init__(self, name, data):
            super().__init__()
            self.name, self.data, self.users_collection = name, data, []
            self.matrix_world = Matrix()

    class Store(dict):
        def __iter__(self):
            return iter(self.values())

        def new(self, name, data):
            self[name] = Object(name, data)
            return self[name]

    class Probes(dict):
        def new(self, name, kind):
            self[name] = SimpleNamespace(type=kind)
            return self[name]

    collection = SimpleNamespace(
        objects=SimpleNamespace(link=lambda obj: obj.users_collection.append(collection))
    )
    points = [(x, y, z) for x in (3, 5) for y in (7, 7.02) for z in (4, 5.6)]
    mirror = Object(
        "mirror",
        SimpleNamespace(
            vertices=[SimpleNamespace(co=p) for p in points],
            polygons=[SimpleNamespace(area=3.2, normal=(0, 1, 0))],
        ),
    )
    mirror.update(
        room_id="U-MBED", material_id="mat_mirror", procedural_id="wardrobe/fronts-mirror"
    )
    mirror.users_collection = [collection]
    floor = Object("floor", SimpleNamespace(vertices=[SimpleNamespace(co=(4, 8, 3.3))]))
    floor["Room ID"] = "U-MBED"
    objects = Store(mirror=mirror, floor=floor)
    probes = Probes()
    bpy = SimpleNamespace(data=SimpleNamespace(objects=objects, lightprobes=probes))
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=deepcopy))
    configure_mirror_probes(bpy)
    for vertex in mirror.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x, y + 0.2, z)
    configure_mirror_probes(bpy)
    assert len(probes) == 1 and len(objects) == 3
    probe = objects["wardrobe/fronts-mirror/reflection-plane"]
    assert probe.users_collection == [collection]
    assert probe.data.type == "PLANE"
    assert probe.data.clip_start == 0.01 and probe.data.influence_distance == 0.1
    assert probe.matrix_world[1][3] == pytest.approx(7.23)
