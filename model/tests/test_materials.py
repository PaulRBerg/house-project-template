import math
from copy import deepcopy
from types import SimpleNamespace

import pytest

from engine import paths
from engine.compiler import compile_design
from engine.materials import (
    ENVIRONMENT_COLORSPACE,
    ENVIRONMENT_SUN_DEFAULTS,
    MaterialError,
    apply_materials,
    compile_materials,
)
from engine.persistence import read_json


@pytest.fixture(scope="module")
def source_manifest():
    return read_json(paths.SCENE_MANIFEST)


def test_complete_baseline_style_has_required_architecture_slots(design, source_manifest):
    identifiers = {
        item["id"]
        for item in compile_materials(design, source_manifest=source_manifest)["materials"]
    }
    assert {
        "mat_oak",
        "mat_metal_dark",
        "mat_glass",
        "mat_stone_grey",
        "mat_soil",
        "mat_plaster_white",
        "mat_pv",
        "material-floor-oak",
        "material-floor-stone",
        "material-wall-ceramic-brick",
    }.issubset(identifiers)


def test_material_parameter_change_does_not_rebuild_geometry(
    design, asset_catalog, source_manifest
):
    changed = deepcopy(design)
    material = next(item for item in changed["materials"] if item["id"] == "mat_cabinetry_chalk")
    before_compiled = compile_design(design, asset_catalog)
    before_materials = compile_materials(
        design,
        before_compiled,
        source_manifest=source_manifest,
    )
    material["color"][0] += 0.05
    after_compiled = compile_design(changed, asset_catalog)
    after_materials = compile_materials(
        changed,
        after_compiled,
        source_manifest=source_manifest,
    )
    before_room = next(item for item in before_compiled["components"] if item["id"] == "G-LIV")
    after_room = next(item for item in after_compiled["components"] if item["id"] == "G-LIV")
    assert before_room["fingerprint"] == after_room["fingerprint"]
    before = next(
        item for item in before_materials["materials"] if item["id"] == "mat_cabinetry_chalk"
    )
    after = next(
        item for item in after_materials["materials"] if item["id"] == "mat_cabinetry_chalk"
    )
    assert before["parameter_fingerprint"] != after["parameter_fingerprint"]
    assert after["parameter_overrides"] == {"color": material["color"]}


def test_baseline_catalog_defaults_do_not_override_native_shader(design, source_manifest):
    descriptors = compile_materials(design, source_manifest=source_manifest)["materials"]
    ceramic = next(item for item in descriptors if item["id"] == "mat_ceramic_white")
    assert ceramic["parameter_overrides"] == {}


def test_accepted_style_remains_override_in_next_fresh_candidate(design, source_manifest):
    accepted = deepcopy(design)
    material = next(item for item in accepted["materials"] if item["id"] == "mat_sage")
    material["roughness"] = 0.72
    descriptor = next(
        item
        for item in compile_materials(
            accepted,
            source_manifest=source_manifest,
        )["materials"]
        if item["id"] == "mat_sage"
    )
    assert descriptor["source_parameters"]["roughness"] == 0.8
    assert descriptor["parameter_overrides"] == {"roughness": 0.72}


def test_style_update_reaches_tagged_asset_material_copy():
    class Socket:
        default_value = None
        is_linked = False

    class Shader:
        type = "BSDF_PRINCIPLED"

        def __init__(self):
            self.inputs = {
                "Base Color": Socket(),
                "Roughness": Socket(),
                "Metallic": Socket(),
                "IOR": Socket(),
                "Alpha": Socket(),
            }

    class Material(dict):
        def __init__(self, name):
            super().__init__()
            self.name = name
            self.diffuse_color = None
            self.use_nodes = False
            self.node_tree = type("Tree", (), {"nodes": [Shader()]})()

    class Materials(list):
        def get(self, name):
            return next((item for item in self if item.name == name), None)

        def new(self, name):
            item = Material(name)
            self.append(item)
            return item

    style = Material("mat_oak")
    asset_copy = Material("Sofa oak copy")
    asset_copy["procedural_source_material_id"] = "mat_oak"
    material_owner = Materials([style, asset_copy])
    bpy = type(
        "Bpy",
        (),
        {
            "data": type(
                "Data",
                (),
                {"materials": material_owner, "worlds": Materials()},
            )()
        },
    )()
    descriptor = {
        "id": "mat_oak",
        "role": "material",
        "source_name": "03 · Pale natural oak.002",
        "color": [0.2, 0.3, 0.4, 1.0],
        "roughness": 0.45,
        "alpha": 0.25,
        "surface_render_method": "BLENDED",
        "parameter_overrides": {
            "color": [0.2, 0.3, 0.4, 1.0],
            "roughness": 0.45,
        },
        "parameter_fingerprint": "changed-style",
    }

    apply_materials(bpy, [descriptor])

    assert asset_copy.diffuse_color == (0.2, 0.3, 0.4, 1.0)
    assert asset_copy.node_tree.nodes[0].inputs["Alpha"].default_value == 0.25
    assert asset_copy.surface_render_method == "BLENDED"
    assert asset_copy["parameter_fingerprint"] == "changed-style"
    assert len(material_owner) == 2


class _Socket:
    def __init__(self, node, name):
        self.node, self.name = node, name
        self.default_value = None
        self.is_linked = False


class _Node:
    def __init__(self, kind):
        self.type = kind
        self.inputs = _Sockets(self)
        self.outputs = _Sockets(self)
        self.image = None


class _Sockets(dict):
    def __init__(self, node):
        super().__init__()
        self.node = node

    def __missing__(self, name):
        socket = self[name] = _Socket(self.node, name)
        return socket


class _Nodes(list):
    def new(self, kind):
        node = _Node(kind)
        self.append(node)
        return node

    def get(self, kind):
        return next((node for node in self if node.type == kind), None)


class _World(dict):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.use_nodes = False
        background = _Node("Background")
        background.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1.0)
        links = []
        self.node_tree = SimpleNamespace(
            nodes=_Nodes([background]),
            links=SimpleNamespace(new=lambda out, into: links.append((out, into)), items=links),
        )


class _Worlds(list):
    def get(self, name):
        return next((item for item in self if item.name == name), None)

    def new(self, name):
        item = _World(name)
        self.append(item)
        return item


def _world_bpy(world):
    loaded = []

    def load(path, *, check_existing):
        assert check_existing
        image = SimpleNamespace(filepath=path, colorspace_settings=SimpleNamespace(name="sRGB"))
        loaded.append(image)
        return image

    return SimpleNamespace(
        data=SimpleNamespace(
            materials=[], worlds=_Worlds([world]), images=SimpleNamespace(load=load)
        ),
        path=SimpleNamespace(relpath=lambda path: "//" + path.rsplit("/model/", 1)[1]),
    ), loaded


def _world_descriptor(design, source_manifest, **changes):
    changed = deepcopy(design)
    world = next(item for item in changed["materials"] if item["id"] == "world-daylight")
    world.update(changes)
    return next(
        item
        for item in compile_materials(changed, source_manifest=source_manifest)["materials"]
        if item["id"] == "world-daylight"
    )


@pytest.mark.parametrize("sun", [None, {"threshold": 4.0, "angle_deg": 2.0}])
def test_environment_world_rebuilds_hdri_tree_and_extracts_sun(design, source_manifest, sun):
    environment = {"map": "exterior/sky.hdr", "rotation_deg": 90.0}
    if sun:
        environment["sun"] = sun
    descriptor = _world_descriptor(design, source_manifest, environment=environment, strength=1.25)
    world = _World("world-daylight")
    bpy, loaded = _world_bpy(world)

    apply_materials(bpy, [descriptor])

    nodes = world.node_tree.nodes
    assert [node.type for node in nodes] == [
        "ShaderNodeTexCoord",
        "ShaderNodeMapping",
        "ShaderNodeTexEnvironment",
        "ShaderNodeBackground",
        "ShaderNodeOutputWorld",
    ]
    coordinates, mapping, texture, background, output = nodes
    assert [
        (out.node, out.name, into.node, into.name) for out, into in world.node_tree.links.items
    ] == [
        (coordinates, "Generated", mapping, "Vector"),
        (mapping, "Vector", texture, "Vector"),
        (texture, "Color", background, "Color"),
        (background, "Background", output, "Surface"),
    ]
    assert mapping.inputs["Rotation"].default_value == pytest.approx((0, 0, math.pi / 2))
    assert background.inputs["Strength"].default_value == 1.25
    assert loaded == [texture.image]
    assert texture.image.filepath == "//assets/exterior/sky.hdr"
    assert texture.image.colorspace_settings.name == ENVIRONMENT_COLORSPACE
    expected = {**ENVIRONMENT_SUN_DEFAULTS, **(sun or {})}
    assert world.use_sun_shadow is True
    assert world.sun_threshold == expected["threshold"]
    assert world.sun_angle == pytest.approx(math.radians(expected["angle_deg"]))
    assert world.sun_shadow_maximum_resolution == expected["shadow_resolution_m"]
    assert (
        descriptor["parameter_fingerprint"]
        != _world_descriptor(
            design,
            source_manifest,
            environment={**environment, "rotation_deg": 45.0},
            strength=1.25,
        )["parameter_fingerprint"]
    )


def test_world_without_environment_keeps_background_and_sun_untouched(design, source_manifest):
    plain = deepcopy(design)
    next(item for item in plain["materials"] if item["id"] == "world-daylight").pop("environment")
    descriptor = _world_descriptor(plain, source_manifest, strength=0.5)
    world = _World("world-daylight")
    bpy, loaded = _world_bpy(world)

    apply_materials(bpy, [descriptor])

    (background,) = world.node_tree.nodes
    assert background.inputs["Strength"].default_value == 0.5
    assert background.inputs["Color"].default_value == tuple(descriptor["color"])
    assert not loaded
    assert not hasattr(world, "use_sun_shadow") and not hasattr(world, "sun_threshold")


def test_environment_requires_world_role_and_map(design, source_manifest):
    with pytest.raises(MaterialError, match="environment"):
        _world_descriptor(design, source_manifest, environment={"rotation_deg": 0.0})
