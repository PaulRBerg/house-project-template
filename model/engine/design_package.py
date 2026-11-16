"""Loading and validation for the versioned JSON design package."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from copy import deepcopy
from functools import cache
from itertools import pairwise
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from shapely.geometry import Point

from . import paths
from .geometry import roof_covering_z, validate_polygon
from .persistence import read_json
from .transforms import determinant3

SUPPLEMENTAL_FILES = {
    "furnishings.json": ("furnishings",),
    "style.json": ("materials", "lights", "cameras"),
    "site.json": ("site_components",),
}


ENTITY_COLLECTIONS = (
    "levels",
    "rooms",
    "walls",
    "openings",
    "slabs",
    "voids",
    "roofs",
    "stairs",
    "structure",
    "furnishings",
    "materials",
    "lights",
    "cameras",
    "site_components",
)


# P 100-1/2013 minimum concept frame sections: art. 5.3.2.2 (column side) and
# art. 5.3.2.1 (beam width and width/depth ratio; wide-shallow band beams are exempt
# from the ratio). The structural engineer sizes the actual members.
MIN_COLUMN_SECTION_M = 0.30
MIN_BEAM_WIDTH_M = 0.20
MIN_BEAM_WIDTH_TO_DEPTH = 0.25

# Concept membrane warm-roof allowance at the drain, subordinate to the coordinated
# energy and waterproofing design; this is not a regulatory insulation minimum.
MIN_ROOF_BUILDUP_M = 0.20


class DesignValidationError(ValueError):
    """Raised when a design package is structurally or semantically invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = read_json(path)
    except FileNotFoundError as exc:
        raise DesignValidationError(f"missing design file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DesignValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DesignValidationError(f"{path} must contain a JSON object")
    return value


def load_design(directory: str | Path) -> dict[str, Any]:
    """Load ``house.json`` and merge the required supplemental design files.

    Supplemental files own disjoint top-level arrays. Each file must exist and
    contain exactly the keys assigned to it, preventing a missing, typo'd or
    partial file from disappearing silently during compilation.
    """

    root = Path(directory)
    design = _read_json(root / "house.json")
    for filename, keys in SUPPLEMENTAL_FILES.items():
        supplement = _read_json(root / filename)
        missing = [key for key in keys if key not in supplement]
        unexpected = sorted(set(supplement) - set(keys))
        if missing or unexpected:
            details = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if unexpected:
                details.append(f"unexpected {', '.join(unexpected)}")
            raise DesignValidationError(f"{filename}: {'; '.join(details)}")
        for key in keys:
            if key in design:
                raise DesignValidationError(
                    f"{filename}: top-level key {key!r} already exists in house.json"
                )
            design[key] = supplement[key]
    return validate_design(design)


@cache
def _validator() -> Draft202012Validator:
    return Draft202012Validator(_read_json(paths.SCHEMA))


def _json_path(error: Any) -> str:
    return ".".join(str(part) for part in error.absolute_path) or "<root>"


def _collect_entities(design: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    entities: dict[str, Mapping[str, Any]] = {}
    for collection in ENTITY_COLLECTIONS:
        for entity in design.get(collection, []):
            entity_id = entity["id"]
            if entity_id in entities:
                raise DesignValidationError(f"duplicate entity id: {entity_id}")
            entities[entity_id] = entity
    return entities


def _check_transform(transform: list[list[float]]) -> None:
    if any(not math.isfinite(value) for row in transform for value in row):
        raise DesignValidationError("transform values must be finite")
    if transform[3] != [0, 0, 0, 1]:
        raise DesignValidationError("transform must be an affine 4x4 matrix")
    # The upper-left 3x3 must be invertible. This direct determinant avoids a
    # numerical dependency in the package loader.
    determinant = determinant3(transform)
    if abs(determinant) < 1e-12:
        raise DesignValidationError("transform must be invertible")


def _check_material_references(design: Mapping[str, Any]) -> None:
    """Every ``material_id``, ``*_material_id`` or ``material_ids`` entry names a material."""

    material_ids = {material["id"] for material in design["materials"]}

    def walk(value: Any, owner: str) -> None:
        if isinstance(value, Mapping):
            owner = value.get("id", owner)
            for key, item in value.items():
                if key == "material_id" or key.endswith("_material_id"):
                    if item not in material_ids:
                        raise DesignValidationError(f"{owner}: unknown {key} {item!r}")
                elif key == "material_ids":
                    for material_id in item:
                        if material_id not in material_ids:
                            raise DesignValidationError(f"{owner}: unknown {key} {material_id!r}")
                else:
                    walk(item, owner)
        elif isinstance(value, list):
            for item in value:
                walk(item, owner)

    walk(design, "<design>")


def _check_structure(design: Mapping[str, Any], levels: Mapping[str, Any]) -> None:
    for member in design.get("structure", []):
        if member["kind"] == "axis":
            continue
        member_id = member["id"]
        if member["level_id"] not in levels:
            raise DesignValidationError(f"{member_id}: unknown level_id {member['level_id']!r}")
        if member["top_z_m"] <= member["bottom_z_m"]:
            raise DesignValidationError(f"{member_id}: top_z_m must exceed bottom_z_m")
        if member["kind"] == "column":
            if min(member["section_m"]) < MIN_COLUMN_SECTION_M - 1e-9:
                raise DesignValidationError(
                    f"{member_id}: column section below the {MIN_COLUMN_SECTION_M:g} m "
                    "P 100-1/2013 minimum"
                )
        else:
            if math.dist(member["start"], member["end"]) <= 1e-9:
                raise DesignValidationError(f"{member_id}: beam length must be positive")
            if member["width_m"] < MIN_BEAM_WIDTH_M - 1e-9:
                raise DesignValidationError(
                    f"{member_id}: beam width below the {MIN_BEAM_WIDTH_M:g} m P 100-1/2013 minimum"
                )
            depth = member["top_z_m"] - member["bottom_z_m"]
            if (
                member["placement"] != "band"
                and member["width_m"] < MIN_BEAM_WIDTH_TO_DEPTH * depth - 1e-9
            ):
                raise DesignValidationError(
                    f"{member_id}: beam width/depth below the {MIN_BEAM_WIDTH_TO_DEPTH:g} "
                    "P 100-1/2013 minimum"
                )


def _check_wall_finishes(design: Mapping[str, Any], walls: Mapping[str, Any]) -> None:
    for room in design["rooms"]:
        for accent in room.get("wall_finish", {}).get("accents", []):
            wall = walls.get(accent["wall_id"])
            if wall is None or wall["level_id"] != room["level_id"]:
                raise DesignValidationError(
                    f"{room['id']}: accent wall_id {accent['wall_id']!r} is not on its level"
                )
            length = math.dist(wall["start"], wall["end"])
            lo, hi = accent.get("span_m", (0, length))
            if not 0 <= lo < hi <= length + 1e-9:
                raise DesignValidationError(
                    f"{room['id']}: accent span on {wall['id']} must increase within the wall"
                )


def validate_design(design: Mapping[str, Any]) -> dict[str, Any]:
    """Validate schema, geometry, references and wall-opening relationships.

    The returned deep copy is safe for compiler normalization; the input is not
    mutated. Constraint evaluation and budget mappings intentionally live above
    this structural validation layer.
    """

    if not isinstance(design, Mapping):
        raise DesignValidationError("design must be a mapping")
    candidate = deepcopy(dict(design))
    errors = sorted(
        _validator().iter_errors(candidate),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        rendered = "; ".join(f"{_json_path(error)}: {error.message}" for error in errors[:8])
        if len(errors) > 8:
            rendered += f"; and {len(errors) - 8} more"
        raise DesignValidationError(rendered)

    _check_transform(candidate["transform"])
    entities = _collect_entities(candidate)
    levels = {level["id"]: level for level in candidate["levels"]}
    walls = {wall["id"]: wall for wall in candidate["walls"]}

    validate_polygon(candidate["parcel"]["polygon"])
    for collection, polygon_key in (
        ("rooms", "zone"),
        ("slabs", "polygon"),
        ("voids", "polygon"),
        ("roofs", "polygon"),
        ("site_components", "polygon"),
    ):
        for entity in candidate.get(collection, []):
            if polygon_key in entity:
                try:
                    polygon = validate_polygon(entity[polygon_key])
                except ValueError as exc:
                    raise DesignValidationError(f"{entity['id']}: {exc}") from exc
                if collection == "rooms" and not polygon.covers(Point(entity["anchor"])):
                    raise DesignValidationError(
                        f"{entity['id']}: anchor must lie in or on the room zone"
                    )

    for collection in ("rooms", "walls", "slabs"):
        for entity in candidate[collection]:
            if entity["level_id"] not in levels:
                raise DesignValidationError(
                    f"{entity['id']}: unknown level_id {entity['level_id']!r}"
                )
    from .double_height import validate_voids

    validate_voids(candidate)
    for roof in candidate["roofs"]:
        if roof.get("level_id") is not None and roof["level_id"] not in levels:
            raise DesignValidationError(f"{roof['id']}: unknown level_id {roof['level_id']!r}")
        low_edge = min(roof_covering_z(roof, point) for point in roof["polygon"]["outer"])
        if low_edge - roof["deck_z_m"] < MIN_ROOF_BUILDUP_M - 1e-9:
            raise DesignValidationError(
                f"{roof['id']}: build-up above deck_z_m below {MIN_ROOF_BUILDUP_M:g} m at the low edge"
            )
    for stair in candidate["stairs"]:
        for key in ("from_level_id", "to_level_id"):
            if stair[key] not in levels:
                raise DesignValidationError(f"{stair['id']}: unknown {key} {stair[key]!r}")

    _check_material_references(candidate)
    _check_structure(candidate, levels)
    _check_wall_finishes(candidate, walls)

    openings_by_wall: dict[str, list[tuple[float, float, str]]] = {}
    for opening in candidate["openings"]:
        wall_id = opening["wall_id"]
        wall = walls.get(wall_id)
        if wall is None:
            raise DesignValidationError(f"{opening['id']}: unknown wall_id {wall_id!r}")
        length = math.dist(wall["start"], wall["end"])
        lo = opening["offset"]
        hi = lo + opening["width"]
        if hi > length + 1e-9:
            raise DesignValidationError(
                f"{opening['id']}: opening span {lo:g}..{hi:g} exceeds "
                f"wall {wall_id!r} length {length:g}"
            )
        if opening["head"] > levels[wall["level_id"]]["clear_height_m"] + 1e-9:
            raise DesignValidationError(f"{opening['id']}: head exceeds level clear height")
        if "reveal" in opening:
            if wall["role"] != "exterior":
                raise DesignValidationError(f"{opening['id']}: a reveal needs an exterior wall")
            if opening["reveal"]["depth_m"] >= wall["thickness"]:
                raise DesignValidationError(
                    f"{opening['id']}: reveal depth_m must stay below the wall thickness"
                )
        openings_by_wall.setdefault(wall_id, []).append((lo, hi, opening["id"]))
    for wall_id, spans in openings_by_wall.items():
        spans.sort()
        for (_, previous_hi, previous_id), (lo, _, opening_id) in pairwise(spans):
            if lo < previous_hi - 1e-9:
                raise DesignValidationError(
                    f"{previous_id} and {opening_id}: overlapping openings on {wall_id}"
                )

    for reference in candidate["semantic_refs"]:
        if (
            reference["entity_id"] not in (candidate["id"], candidate["parcel"]["id"])
            and reference["entity_id"] not in entities
        ):
            raise DesignValidationError(
                f"semantic_refs: unknown entity_id {reference['entity_id']!r}"
            )
    room_ids = {room["id"] for room in candidate["rooms"]}
    evidence_ids: set[str] = set()
    for evidence in candidate.get("baseline_evidence", {}).get("room_finished_floors", []):
        room_id = evidence["room_id"]
        if room_id not in room_ids:
            raise DesignValidationError(f"baseline_evidence: unknown room_id {room_id!r}")
        if room_id in evidence_ids:
            raise DesignValidationError(f"baseline_evidence: duplicate room_id {room_id!r}")
        evidence_ids.add(room_id)
        try:
            floor = validate_polygon(evidence["polygon"])
        except ValueError as exc:
            raise DesignValidationError(f"baseline_evidence {room_id}: {exc}") from exc
        if not math.isclose(floor.area, evidence["area_m2"], abs_tol=1e-4):
            raise DesignValidationError(
                f"baseline_evidence {room_id}: polygon area does not match area_m2"
            )
    return candidate
