from types import SimpleNamespace

import pytest

from engine.floor_view_graphics import (
    floor_window_symbols,
    glazing_symbol,
    place_labels,
    rectangles_overlap,
    room_label,
)


def test_compact_labels_keep_plan_identity_and_measured_area():
    room = {
        "Room name": "A long full room name",
        "Room label": "Cameră tehnică",
        "Room total area m²": 5.723,
    }
    assert room_label(room, "G-TECH", cutaway=False) == "G-TECH\nCameră tehnică\n5.7 m²"
    assert room_label(room, "G-TECH", cutaway=True) == "Cameră tehnică\n5.7 m²"


def test_packing_moves_conflicting_card_within_its_room_candidates():
    bounds = (-0.6, -0.3, 0.6, 0.3)
    specifications = [
        ("bath", bounds, [(0, 0)]),
        ("hall", bounds, [(0.8, 0), (0.8, -0.8)]),
        ("stair", bounds, [(1.6, 0), (1.6, -0.8), (1.6, 0.8)]),
    ]
    result = place_labels(specifications)
    assert result["bath"] == (0, 0)
    assert result["hall"] == (0.8, -0.8)
    rectangles = [
        (x + bounds[0], y + bounds[1], x + bounds[2], y + bounds[3]) for x, y in result.values()
    ]
    assert not any(
        rectangles_overlap(a, b) for i, a in enumerate(rectangles) for b in rectangles[i + 1 :]
    )
    assert place_labels([("a", bounds, [(0, 0)]), ("b", bounds, [(0, 0)])]) is None


def test_high_sill_glazing_symbol_retains_live_position_and_span():
    points = [(x, y, z) for x in (3, 5) for y in (7, 7.018) for z in (1.7, 2.4)]
    vertices, faces, slots = glazing_symbol(points, 1.086)
    assert len(faces) == 5 and slots == [0, 1, 1, 1, 1]
    assert min(p[0] for p in vertices) == pytest.approx(3, abs=0.002)
    assert max(p[0] for p in vertices) == pytest.approx(5, abs=0.002)
    assert {round(p[2], 3) for p in vertices} == {1.086, 1.087}


@pytest.mark.parametrize("fail", [None, "render", "link"])
def test_window_overlay_cleans_created_resources_and_leaves_panes_untouched(fail):
    class Vector(list):
        @property
        def z(self):
            return self[2]

    class Matrix:
        def __matmul__(self, value):
            return value

    class Store(list):
        def __init__(self, factory):
            super().__init__()
            self.factory = factory

        def new(self, *args):
            item = self.factory(*args)
            self.append(item)
            return item

        def remove(self, item, **_kwargs):
            super().remove(item)

    class Mesh:
        materials = None

        def __init__(self, name):
            self.name, self.materials = name, []

        def from_pydata(self, vertices, edges, faces):
            self.vertices = vertices
            self.polygons = [SimpleNamespace(material_index=0) for _ in faces]

    def material(name):
        node = SimpleNamespace(
            inputs={"Color": SimpleNamespace(default_value=None), "Surface": 0}, outputs=[0]
        )
        return SimpleNamespace(
            name=name,
            node_tree=SimpleNamespace(
                nodes=SimpleNamespace(clear=lambda: None, new=lambda _name: node),
                links=SimpleNamespace(new=lambda *_args: None),
            ),
        )

    class Object(dict):
        matrix_world = Matrix()

    floor = Object({"Room ID": "G-BATH", "Floor level": "G"})
    floor.data = SimpleNamespace(vertices=[SimpleNamespace(co=Vector((0, 0, 0.006)))])
    pane = Object({"Floor level": "G", "Opening ID": "window-bath", "material_id": "mat_glass"})
    pane.data = SimpleNamespace(
        vertices=[SimpleNamespace(co=Vector(p)) for p in ((3, 7, 1.7), (5, 7, 2.4))]
    )
    upper_pane = Object(
        {"Floor level": "U", "Opening ID": "upper-window", "material_id": "mat_glass"}
    )
    upper_pane.data = pane.data

    def link(_obj):
        if fail == "link":
            raise RuntimeError("link failed")

    scene = SimpleNamespace(
        objects=[floor, pane, upper_pane],
        collection=SimpleNamespace(objects=SimpleNamespace(link=link)),
    )
    objects = Store(lambda name, mesh: SimpleNamespace(name=name, data=mesh))
    meshes, materials = Store(Mesh), Store(material)
    bpy = SimpleNamespace(data=SimpleNamespace(objects=objects, meshes=meshes, materials=materials))

    def render():
        with floor_window_symbols(bpy, scene, "G"):
            assert len(objects) == 1 and len(meshes) == 1 and len(materials) == 2
            assert not objects[0].visible_shadow
            assert min(p[2] for p in meshes[0].vertices) == pytest.approx(1.086)
            if fail == "render":
                raise RuntimeError("render failed")

    if fail:
        with pytest.raises(RuntimeError, match=f"{fail} failed"):
            render()
    else:
        render()
    assert not objects and not meshes and not materials
    assert pane["Opening ID"] == "window-bath"
    assert scene.objects == [floor, pane, upper_pane]
