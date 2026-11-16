"""Portable asset-catalog contract for the procedural house engine.

The catalog is deliberately plain JSON so it can be inspected before Blender is
available.  Blender integration remains lazy; importing this module never needs
``bpy``.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .persistence import read_json
from .transforms import finite_vector

CATALOG_SCHEMA_VERSION = 1
REQUIRED_ASSET_FIELDS = frozenset(
    {
        "id",
        "name",
        "classification",
        "collection",
        "datablock",
        "origin",
        "dimensions",
        "members",
        "materials",
        "source_hash",
    }
)
CLASSIFICATIONS = frozenset({"reusable_furniture", "reusable_equipment", "reusable_plant"})


class CatalogError(ValueError):
    """Raised when evidence cannot support an editable asset catalog."""


def validate_catalog(catalog: Mapping[str, Any]) -> None:
    """Validate the schema v1 payload without relying on Blender."""
    if not isinstance(catalog, Mapping):
        raise CatalogError("catalog must be an object")
    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise CatalogError(f"schema_version must be {CATALOG_SCHEMA_VERSION}")
    source = catalog.get("source")
    if not isinstance(source, Mapping) or not isinstance(source.get("sha256"), str):
        raise CatalogError("source.sha256 is required")
    blend = source.get("blend")
    if not isinstance(blend, str) or not blend or Path(blend).is_absolute():
        raise CatalogError("source.blend must be a path relative to the catalog")
    assets = catalog.get("assets")
    if not isinstance(assets, list) or not assets:
        raise CatalogError("assets must be a non-empty list")
    identifiers: set[str] = set()
    members: set[str] = set()
    for asset in assets:
        if not isinstance(asset, Mapping):
            raise CatalogError("every asset must be an object")
        missing = REQUIRED_ASSET_FIELDS - set(asset)
        if missing:
            raise CatalogError(f"asset missing fields: {sorted(missing)}")
        identifier = asset["id"]
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise CatalogError("asset ids must be non-empty and unique")
        identifiers.add(identifier)
        if asset["classification"] not in CLASSIFICATIONS:
            raise CatalogError(f"unknown asset classification: {asset['classification']!r}")
        if not isinstance(asset["name"], str) or not isinstance(asset["collection"], str):
            raise CatalogError("asset name and collection must be strings")
        if not isinstance(asset["datablock"], Mapping):
            raise CatalogError("asset datablock must be an object")
        finite_vector(asset["origin"], 3, "origin", CatalogError)
        finite_vector(asset["dimensions"], 3, "dimensions", CatalogError)
        if not isinstance(asset["members"], list) or not asset["members"]:
            raise CatalogError("asset members must be a non-empty list")
        if not all(isinstance(name, str) and name for name in asset["members"]):
            raise CatalogError("asset members must be non-empty strings")
        overlap = members.intersection(asset["members"])
        if overlap:
            raise CatalogError(f"object appears in multiple assets: {sorted(overlap)[:3]}")
        members.update(asset["members"])
        if not isinstance(asset["materials"], list) or not all(
            isinstance(name, str) for name in asset["materials"]
        ):
            raise CatalogError("asset materials must be a string list")
        if asset["source_hash"] != source["sha256"]:
            raise CatalogError("asset source_hash must match source.sha256")


def read_catalog(path: str | Path) -> dict[str, Any]:
    """Read and validate an asset catalog."""
    catalog = read_json(path)
    validate_catalog(catalog)
    return catalog


def asset_index(catalog: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Return stable asset IDs mapped to the records of a validated catalog."""
    return {asset["id"]: asset for asset in catalog["assets"]}
