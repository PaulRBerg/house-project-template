"""Normalize a validated design into fingerprinted incremental components."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .assets import asset_index
from .design_package import ENTITY_COLLECTIONS, validate_design
from .double_height import cut_voids
from .geometry import as_polygon, polygon_area
from .persistence import normalize_json as _normalize
from .persistence import stable_hash

COMPILER_ID = "engine.compiler"
COMPILER_VERSION = "1.0.0"


def make_component(
    id: str,
    kind: str,
    payload: Mapping[str, Any],
    dependencies: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Create one immutable-shape compiler component.

    Dependency fingerprints propagate into this component's fingerprint, while the
    public ``dependencies`` field remains a portable list of IDs.
    """

    if not id or not kind:
        raise ValueError("component id and kind must be non-empty")
    dependency_ids: list[str] = []
    dependency_hashes: list[str] = []
    for dependency in dependencies:
        if dependency["id"] in dependency_ids:
            raise ValueError(f"duplicate dependency {dependency['id']!r} for {id}")
        dependency_ids.append(dependency["id"])
        dependency_hashes.append(dependency["fingerprint"])
    normalized_payload = _normalize(payload)
    body = {
        "id": id,
        "kind": kind,
        "payload": normalized_payload,
        "dependencies": dependency_ids,
    }
    fingerprint_body = dict(body)
    fingerprint_body["dependency_fingerprints"] = dependency_hashes
    fingerprint_body["generator"] = {
        "id": COMPILER_ID,
        "version": COMPILER_VERSION,
    }
    return {**body, "fingerprint": stable_hash(fingerprint_body)}


def _entity_payload(entity: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entity.items() if key != "id"}


def _geometry_payload(entity: Mapping[str, Any]) -> dict[str, Any]:
    """Keep material assignment, at any depth, out of geometry fingerprints."""

    def strip(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {key: strip(item) for key, item in value.items() if key != "material_id"}
        if isinstance(value, list):
            return [strip(item) for item in value]
        return value

    return strip({key: value for key, value in entity.items() if key != "id"})


def frame_members(design: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Columns and beams of the concept frame in ID order; grid axes carry no geometry."""

    return sorted(
        (member for member in design.get("structure", []) if member["kind"] != "axis"),
        key=lambda member: member["id"],
    )


def frame_member_measures(member: Mapping[str, Any]) -> dict[str, float]:
    """Nominal centre-line length and gross concrete volume of one column or beam.

    Beams run between column centres, so gross volumes overlap at the nodes; the
    totals are concept quantities, not a structural take-off.
    """

    depth = member["top_z_m"] - member["bottom_z_m"]
    if member["kind"] == "column":
        section_x, section_y = member["section_m"]
        return {"length_m": depth, "volume_m3": section_x * section_y * depth}
    length = math.dist(member["start"], member["end"])
    return {"length_m": length, "volume_m3": length * member["width_m"] * depth}


def frame_totals(members: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    """Column count, beam centre-line length and gross concrete volume of the frame."""

    measures = [(member, frame_member_measures(member)) for member in members]
    return {
        "structure_column_count": sum(member["kind"] == "column" for member in members),
        "structure_beam_length_m": round(
            sum(item["length_m"] for member, item in measures if member["kind"] == "beam"), 6
        ),
        "structure_concrete_m3": round(sum(item["volume_m3"] for _, item in measures), 6),
    }


def _asset_digest(asset_catalog: Mapping[str, Any] | None, asset_id: str) -> str:
    if asset_catalog is None:
        return stable_hash({"asset_id": asset_id, "state": "unresolved"})
    asset = asset_index(asset_catalog).get(asset_id)
    if asset is None:
        return stable_hash({"asset_id": asset_id, "state": "missing"})
    return stable_hash(asset)


def _canonical_design_source(design: Mapping[str, Any]) -> dict[str, Any]:
    """Canonicalize semantically unordered entity collections for source hashing."""

    source = _normalize(design)
    for collection in ENTITY_COLLECTIONS:
        if collection in source:
            source[collection] = sorted(source[collection], key=lambda entity: entity["id"])
    if "semantic_refs" in source:
        source["semantic_refs"] = sorted(
            source["semantic_refs"], key=lambda reference: reference["entity_id"]
        )
    evidence = source.get("baseline_evidence")
    if evidence is not None:
        evidence["room_finished_floors"] = sorted(
            evidence["room_finished_floors"], key=lambda record: record["room_id"]
        )
    return source


def source_fingerprint(normalized: Mapping[str, Any]) -> str:
    """Fingerprint a validated design independently of entity order."""

    return stable_hash(_canonical_design_source(normalized))


def compile_design(
    design: Mapping[str, Any], asset_catalog: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Compile JSON design data into deterministic, dependency-aware components."""

    normalized = validate_design(design)
    components: dict[str, dict[str, Any]] = {}

    def add(
        component_id: str,
        kind: str,
        payload: Mapping[str, Any],
        dependencies: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        if component_id in components:
            raise ValueError(f"duplicate component id: {component_id}")
        component = make_component(component_id, kind, payload, dependencies)
        components[component_id] = component
        return component

    parcel = add(
        normalized["parcel"]["id"],
        "parcel",
        _entity_payload(normalized["parcel"]),
    )
    design_root = add(
        normalized["id"],
        "design",
        {
            "schema_version": normalized["schema_version"],
            "units": normalized["units"],
            "transform": normalized["transform"],
            "accepted_metrics": normalized.get("accepted_metrics", {}),
            "source": normalized.get("source", {}),
            "generator": {"id": COMPILER_ID, "version": COMPILER_VERSION},
        },
        [parcel],
    )
    for material in sorted(normalized.get("materials", []), key=lambda entity: entity["id"]):
        add(material["id"], "material", _entity_payload(material), [design_root])
    for level in sorted(normalized["levels"], key=lambda entity: entity["id"]):
        add(level["id"], "level", _entity_payload(level), [design_root])

    def level_dependency(entity: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [components[entity["level_id"]]]

    def add_material_binding(entity: Mapping[str, Any], target: Mapping[str, Any]) -> None:
        material_id = entity.get("material_id")
        if not material_id:
            return
        add(
            f"binding-{entity['id']}-material",
            "material_binding",
            {"target_id": entity["id"], "material_id": material_id},
            [target, components[material_id]],
        )

    openings_by_wall: dict[str, list[dict[str, Any]]] = {}
    for opening in normalized["openings"]:
        opening_payload = {
            key: value for key, value in opening.items() if key not in ("wall_id", "material_id")
        }
        openings_by_wall.setdefault(opening["wall_id"], []).append(opening_payload)
    for wall in sorted(normalized["walls"], key=lambda entity: entity["id"]):
        payload = _geometry_payload(wall)
        payload["openings"] = sorted(
            openings_by_wall.get(wall["id"], []), key=lambda opening: opening["id"]
        )
        component = add(wall["id"], "wall", payload, level_dependency(wall))
        add_material_binding(wall, component)
    walls_by_level: dict[str, list[dict[str, Any]]] = {}
    for wall in normalized["walls"]:
        walls_by_level.setdefault(wall["level_id"], []).append(components[wall["id"]])
    for room in sorted(normalized["rooms"], key=lambda entity: entity["id"]):
        payload = _geometry_payload(room)
        payload["floor_generation"] = {
            "method": "zone_minus_wall_footprints",
            "fallback_inset_m": room["floor_inset_m"],
        }
        dependencies = level_dependency(room) + sorted(
            walls_by_level.get(room["level_id"], []), key=lambda component: component["id"]
        )
        component = add(room["id"], "room", payload, dependencies)
        add_material_binding(room, component)
    for opening in sorted(normalized["openings"], key=lambda entity: entity["id"]):
        wall = components[opening["wall_id"]]
        component = add(
            opening["id"],
            "opening",
            _geometry_payload(opening),
            [wall, components[wall["payload"]["level_id"]]],
        )
        add_material_binding(opening, component)
    for slab in sorted(normalized["slabs"], key=lambda entity: entity["id"]):
        component = add(slab["id"], "slab", _geometry_payload(slab), level_dependency(slab))
        add_material_binding(slab, component)
    for void in sorted(normalized.get("voids", []), key=lambda entity: entity["id"]):
        add(void["id"], "void", _geometry_payload(void), level_dependency(void))
    for member in frame_members(normalized):
        component = add(
            member["id"], "structural_member", _geometry_payload(member), level_dependency(member)
        )
        add_material_binding(member, component)
    for roof in sorted(normalized["roofs"], key=lambda entity: entity["id"]):
        dependencies = (
            [components[roof["level_id"]]] if roof.get("level_id") is not None else [design_root]
        )
        component = add(roof["id"], "roof", _geometry_payload(roof), dependencies)
        add_material_binding(roof, component)
    for stair in sorted(normalized["stairs"], key=lambda entity: entity["id"]):
        add(
            stair["id"],
            "stair",
            _entity_payload(stair),
            [components[stair["from_level_id"]], components[stair["to_level_id"]]],
        )
    for collection, kind in (
        ("lights", "light"),
        ("cameras", "camera"),
        ("site_components", "site_component"),
    ):
        for entity in sorted(normalized.get(collection, []), key=lambda item: item["id"]):
            add(entity["id"], kind, _entity_payload(entity), [design_root])
    for furnishing in sorted(normalized.get("furnishings", []), key=lambda entity: entity["id"]):
        payload = _geometry_payload(furnishing)
        dependencies = [design_root]
        room_id = furnishing.get("room_id")
        if room_id is not None:
            if room_id not in components or components[room_id]["kind"] != "room":
                raise ValueError(f"{furnishing['id']}: unknown room_id {room_id!r}")
            dependencies.append(components[room_id])
        asset_id = furnishing.get("asset_id")
        if asset_id is not None:
            payload["asset_digest"] = _asset_digest(asset_catalog, asset_id)
        component = add(furnishing["id"], "furnishing", payload, dependencies)
        add_material_binding(furnishing, component)

    room_areas = {room["id"]: round(polygon_area(room["zone"]), 6) for room in normalized["rooms"]}
    wall_lengths = {
        wall["id"]: round(math.dist(wall["start"], wall["end"]), 6) for wall in normalized["walls"]
    }
    opening_areas = {
        opening["id"]: round(opening["width"] * (opening["head"] - opening["sill"]), 6)
        for opening in normalized["openings"]
    }
    slab_areas = {
        slab["id"]: round(
            cut_voids(normalized, as_polygon(slab["polygon"]), slab_id=slab["id"]).area, 6
        )
        for slab in normalized["slabs"]
    }
    roof_areas = {
        roof["id"]: round(polygon_area(roof["polygon"]), 6) for roof in normalized["roofs"]
    }
    quantities = {
        "parcel_area_m2": round(polygon_area(normalized["parcel"]["polygon"]), 6),
        "room_zone_area_m2": room_areas,
        "room_zone_total_m2": round(sum(room_areas.values()), 6),
        "wall_length_m": wall_lengths,
        "wall_length_total_m": round(sum(wall_lengths.values()), 6),
        "opening_area_m2": opening_areas,
        "opening_area_total_m2": round(sum(opening_areas.values()), 6),
        "slab_plan_area_m2": slab_areas,
        "slab_plan_area_total_m2": round(sum(slab_areas.values()), 6),
        "roof_plan_area_m2": roof_areas,
        "roof_plan_area_total_m2": round(sum(roof_areas.values()), 6),
        **frame_totals(frame_members(normalized)),
    }
    ordered_components = [components[key] for key in sorted(components)]
    output = {
        "schema_version": 1,
        "units": "m",
        "design_id": normalized["id"],
        "source_fingerprint": source_fingerprint(normalized),
        "asset_catalog_fingerprint": stable_hash(asset_catalog or {}),
        "generator": {"id": COMPILER_ID, "version": COMPILER_VERSION},
        "components": ordered_components,
        "quantities": _normalize(quantities),
    }
    output["fingerprint"] = stable_hash(output)
    return output
