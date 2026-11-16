from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine import paths
from engine.assets import CatalogError, read_catalog, validate_catalog


def _catalog() -> dict:
    return {
        "schema_version": 1,
        "source": {"blend": "baseline-assets.blend", "sha256": "source-hash"},
        "assets": [
            {
                "id": "reusable-furniture:living:sofa:9cc19defb20e",
                "name": "Living sofa",
                "classification": "reusable_furniture",
                "collection": "G | Furniture • Living",
                "datablock": {"objects": ["sofa"], "types": ["MESH"], "meshes": ["sofa"]},
                "origin": [0, 0, 0],
                "dimensions": [1, 2, 3],
                "members": ["sofa"],
                "materials": ["linen"],
                "source_hash": "source-hash",
            }
        ],
    }


def test_catalog_is_valid_outside_blender(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(_catalog()))
    assert read_catalog(path)["assets"][0]["name"] == "Living sofa"


def test_catalog_rejects_absolute_source_blend() -> None:
    catalog = _catalog()
    catalog["source"]["blend"] = "/abs/baseline-assets.blend"
    with pytest.raises(CatalogError, match="relative"):
        validate_catalog(catalog)


def test_catalog_hash_matches_shipped_asset_library(asset_catalog) -> None:
    library = paths.ASSETS / asset_catalog["source"]["blend"]
    assert library == paths.ASSET_LIBRARY
    assert hashlib.sha256(library.read_bytes()).hexdigest() == asset_catalog["source"]["sha256"]


def test_terrace_dining_chairs_are_whole_disjoint_catalog_assets(asset_catalog) -> None:
    catalog = asset_catalog
    chairs = [
        asset
        for asset in catalog["assets"]
        if asset["id"].startswith("reusable-furniture:exterior-furniture:terrace-dining-chair-")
    ]
    assert len(chairs) == 8
    assert all(asset["dimensions"] == [0.4725, 0.470001, 0.837575] for asset in chairs)
    assert all(len(asset["members"]) == 6 for asset in chairs)
    assert all(
        asset["materials"]
        == [
            "03 · Pale natural oak | fine longitudinal grain.002",
            "06 · Oatmeal woven linen.002",
        ]
        for asset in chairs
    )
    assert all(asset["source_hash"] == catalog["source"]["sha256"] for asset in chairs)
    members = [member for asset in chairs for member in asset["members"]]
    assert len(members) == len(set(members)) == 48
    assert {member for member in members if "/ soft seat." in member} == {
        f"Terrace / dining chair / soft seat.{suffix:03d}" for suffix in range(8, 16)
    }
    assert not any(
        asset["id"] == "reusable-furniture:exterior-furniture:terrace-dining-chair:9e81d5de961a"
        for asset in catalog["assets"]
    )
