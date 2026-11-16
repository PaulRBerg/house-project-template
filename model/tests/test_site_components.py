from copy import deepcopy

import pytest
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union

from engine.site_components import SiteComponentError, compile_site_components


def _mesh_footprint(mesh):
    matrix = mesh["transform"]
    vertices = mesh.get("vertices", mesh.get("geometry", {}).get("vertices", []))
    points = [
        [sum(matrix[i][j] * vertex[j] for j in range(3)) + matrix[i][3] for i in range(2)]
        for vertex in vertices
    ]
    return MultiPoint(points).convex_hull


@pytest.fixture(scope="module")
def result(design, asset_catalog):
    """The baseline site-component compile, shared read-only by the tests that only inspect it."""
    return compile_site_components(design, asset_catalog)


def test_setback_subjects_stay_inside_the_setback_and_carry_the_terrace_furniture(
    design, requirements, result
):
    subjects = {item["id"] for item in design["site_components"] if item.get("setback_subject")}
    assert subjects
    footprints = {}
    for mesh in result["meshes"]:
        if mesh["component_id"] in subjects:
            assert mesh["properties"]["Setback subject"]
            footprints[mesh["id"]] = _mesh_footprint(mesh)
        else:
            assert "Setback subject" not in mesh.get("properties", {})
    inset = Polygon(design["parcel"]["polygon"]["outer"]).buffer(
        -requirements["setback"]["minimum_m"]
    )
    assert footprints and all(inset.covers(footprint) for footprint in footprints.values())

    terrace = unary_union(
        [footprint for key, footprint in footprints.items() if key.startswith("terrace-floor")]
    )
    furniture = [
        item["id"] for item in design["site_components"] if item["purpose"] == "terrace-furniture"
    ]
    for mesh in result["meshes"]:
        if mesh["component_id"] in furniture:
            assert terrace.covers(_mesh_footprint(mesh)), mesh["id"]
    for placement in result["placements"]:
        if placement["component_id"] in furniture:
            assert terrace.contains(
                Point(placement["transform"][0][3], placement["transform"][1][3])
            )


def test_generated_site_kits_own_their_warm_lights():
    design = _parcel_design()
    design["site_components"] = [
        {
            "id": "site-terrace-light",
            "kind": "generated_site",
            "purpose": "terrace-lighting",
            "collection": "Exterior | Terrace",
            "parts": [
                {
                    "id": "terrace-pendant",
                    "position": [6, 8, 2.4],
                    "dimensions": [0.4, 0.4, 0.5],
                    "generated": {"kind": "pendant", "params": {"temperature": 2700}},
                }
            ],
        }
    ]
    result = compile_site_components(design)
    assert result["lights"]
    for light in result["lights"]:
        assert light["component_id"] == "site-terrace-light"
        assert light["collection"] == "Exterior | Terrace"
        assert light["id"].startswith("terrace-pendant/light-")
        assert light["temperature"] == 2700
    assert result["meshes"] and {mesh["component_id"] for mesh in result["meshes"]} == {
        "site-terrace-light"
    }
    assert all(mesh["properties"]["generated_kind"] == "pendant" for mesh in result["meshes"])


def _parcel_design(**parcel):
    """A synthetic design holding only a 24 x 40 m parcel and no site components."""
    outline = [[0, 0], [24, 0], [24, 40], [0, 40]]
    return {"parcel": {"id": "parcel", "polygon": {"outer": outline, "holes": []}, **parcel}}


def test_parcel_ground_and_setback_outline_follow_the_parcel_and_setback():
    from engine.site_components import PARCEL_GROUND_Z_M, SETBACK_OUTLINE_Z_M

    assert compile_site_components(_parcel_design(), setback_m=2.0)["meshes"] == []
    design = _parcel_design(ground_material_id="mat_grass", setback_material_id="mat_accent")
    meshes = compile_site_components(design, setback_m=2.0)["meshes"]
    ground = next(mesh for mesh in meshes if mesh["id"] == "parcel/ground")
    assert ground["material_binding"]["material_id"] == "mat_grass"
    assert _mesh_footprint(ground).area == pytest.approx(24 * 40)
    assert ground["transform"][2][3] == PARCEL_GROUND_Z_M
    bands = [mesh for mesh in meshes if mesh["id"].startswith("parcel/setback-")]
    assert len(bands) == 4
    assert {mesh["transform"][2][3] for mesh in bands} == {SETBACK_OUTLINE_Z_M}
    inset = unary_union([_mesh_footprint(mesh) for mesh in bands])
    # The bands trace the 2 m inset: a 20 x 36 m rectangle.
    assert inset.bounds == pytest.approx((2 - 0.025, 2 - 0.025, 22 + 0.025, 38 + 0.025))
    wider = compile_site_components(design, setback_m=3.0)["meshes"]
    assert {mesh["id"] for mesh in wider} == {mesh["id"] for mesh in meshes}
    assert (
        next(m for m in wider if m["id"] == "parcel/setback-00")["geometry_fingerprint"]
        != (bands[0]["geometry_fingerprint"])
    )


def test_geometry_hash_tracks_position_but_not_material(design):
    design = deepcopy(design)
    design["site_components"] = [
        {
            "id": "box",
            "kind": "path",
            "position": [1, 2, 0],
            "rotation": [0, 0, 0],
            "dimensions": [2, 1, 0.1],
            "primitive": "box",
            "material_id": "mat_stone_grey",
        }
    ]

    def box():
        return next(m for m in compile_site_components(design)["meshes"] if m["id"] == "box")

    baseline = box()
    design["site_components"][0]["material_id"] = "mat_oak"
    recolored = box()
    assert baseline["geometry_fingerprint"] == recolored["geometry_fingerprint"]
    design["site_components"][0]["position"][0] += 1
    moved = box()
    assert baseline["geometry_fingerprint"] != moved["geometry_fingerprint"]


def test_reusable_site_assets_cannot_be_resized(design, asset_catalog):
    changed = deepcopy(design)
    asset = next(item for item in changed["site_components"] if item.get("asset_id"))
    changed["site_components"] = [asset]
    asset["dimensions"][0] += 0.1
    with pytest.raises(SiteComponentError, match="fixed"):
        compile_site_components(changed, asset_catalog)
