from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from engine.blender_runtime import _assign_material_bindings, _reset_scene
from engine.runtime_bundle import compare_runtime_bundles, compile_runtime_bundle


@pytest.fixture(scope="module")
def bundle():
    return compile_runtime_bundle()


def test_noop_and_material_only_do_not_rebuild_geometry(bundle) -> None:
    unchanged = copy.deepcopy(bundle)
    assert compare_runtime_bundles(bundle, unchanged)["mode"] == "noop"
    changed = copy.deepcopy(bundle)
    changed["materials"]["materials"][0]["roughness"] = 0.123
    changed["materials"]["materials"][0]["parameter_fingerprint"] = "changed"
    changed["materials"]["fingerprint"] = "changed"
    changed["runtime_fingerprint"] = "changed"
    difference = compare_runtime_bundles(bundle, changed)
    assert difference["mode"] == "material-only"
    assert difference["added"] == []
    assert difference["changed"] == []
    assert difference["removed"] == []


def test_retained_site_mesh_uses_updated_or_removed_material_binding() -> None:
    class Object(dict):
        pass

    obj = Object(procedural_id="terrace-floor", material_id="old")
    mesh = SimpleNamespace(materials=["old material"])
    obj.data = mesh
    bpy = SimpleNamespace(data=SimpleNamespace(objects=[obj]))
    descriptor = {
        "id": "terrace-floor",
        "material_binding": {"material_id": "stone", "slot": "body"},
    }
    bundle = {"site_components": {"meshes": [descriptor]}}
    _assign_material_bindings(bpy, {"stone": "new material"}, bundle)
    assert obj.data is mesh
    assert obj["material_id"] == "stone"
    assert mesh.materials == ["new material"]
    descriptor["material_binding"]["material_id"] = None
    _assign_material_bindings(bpy, {"stone": "new material"}, bundle)
    assert obj.data is mesh
    assert obj["material_id"] == ""
    assert mesh.materials == []


def test_fresh_reset_drops_every_collection_including_linked_stale_ones() -> None:
    class Datablocks(list):
        def remove(self, item, do_unlink=False):
            super().remove(item)

    stale = SimpleNamespace(name="Exterior | Terrace & balcony", users=7)
    kept_name = SimpleNamespace(name="Exterior | Terrace", users=1)
    scenes = Datablocks([SimpleNamespace(name="01 Garden"), SimpleNamespace(name="02 Plan")])
    bpy = SimpleNamespace(
        data=SimpleNamespace(
            objects=Datablocks(), scenes=scenes, collections=Datablocks([stale, kept_name])
        )
    )
    _reset_scene(bpy)
    assert list(bpy.data.collections) == []
    assert [scene.name for scene in bpy.data.scenes] == ["Procedural build"]
