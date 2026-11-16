"""Evidence-backed requirement checks for procedural design candidates."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import unary_union

from . import paths
from .actual_geometry_checks import check_actual_placements_and_passages, check_result
from .architectural_details import DEFAULT_DOOR_SWING_DEG, stairs
from .architecture import Builder
from .circulation_checks import (
    actual_bath_access_check,
    actual_corridor_checks,
    authored_corridor_checks,
)
from .compiler import compile_design, frame_members, source_fingerprint
from .design_package import DesignValidationError, validate_design
from .geometry import as_polygon, furnishing_footprint, wall_footprint
from .persistence import read_json
from .quantities import PASSAGE_OPENING_KINDS, design_quantities, measured_mesh_quantities
from .transforms import wall_point

GROSS_MEASUREMENT_TOLERANCE_M2 = 0.1
SETBACK_MEASUREMENT_TOLERANCE_M = 0.01
CONCEPT_NEAR_LIMIT_MIN_M2 = 2.0
CONCEPT_NEAR_LIMIT_FRACTION = 0.01
CLEAR_HEIGHT_CONCEPT_TOLERANCE_M = 0.10
STRUCTURE_CLASH_AREA_M2 = 1e-6

COMPLETION_STAGES = ("La roșu", "La gri", "La cheie", "La mutat", "Extra")
RECORD_ID_PATTERN = re.compile(r"`([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)`\Z")
H2_PATTERN = re.compile(r"^##\s+(.+?)\s*$")


def _table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped[1:-1])]


def _normalized_content(cells: Sequence[str]) -> str:
    return " | ".join(re.sub(r"\s+", " ", cell.replace(r"\|", "|").strip()) for cell in cells)


REQUIREMENTS_SCHEMA_VERSION = 3


def load_requirements(path: str | Path) -> dict[str, Any]:
    value = read_json(path)
    if value.get("schema_version") != REQUIREMENTS_SCHEMA_VERSION:
        raise ValueError(f"requirements schema_version must be {REQUIREMENTS_SCHEMA_VERSION}")
    return value


def _cited_requirements(value: Any) -> set[str]:
    """Every brief record a requirement rule cites through ``requirement_id(s)``."""
    if isinstance(value, Mapping):
        cited = {value["requirement_id"]} if "requirement_id" in value else set()
        cited.update(value.get("requirement_ids", []))
        for key, item in value.items():
            if key not in {"requirement_id", "requirement_ids"}:
                cited |= _cited_requirements(item)
        return cited
    if isinstance(value, list):
        return set().union(*(_cited_requirements(item) for item in value))
    return set()


def brief_records(brief_root: str | Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(Path(brief_root).glob("*.md")):
        if path.name in paths.USER_OWNED_FILES:
            continue
        stage: str | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            heading = H2_PATTERN.match(line)
            if heading:
                value = heading.group(1)
                stage = value if value in COMPLETION_STAGES else None
                continue
            cells = _table_cells(line)
            if not cells:
                continue
            identifier = RECORD_ID_PATTERN.fullmatch(cells[0])
            if identifier is None or len(cells) < 2:
                continue
            record_id = identifier.group(1)
            if record_id in records:
                raise ValueError(f"duplicate brief record {record_id}")
            records[record_id] = {
                "record_id": record_id,
                "stage": stage,
                "content": _normalized_content(cells[1:]),
                "source": path.name,
            }
    return records


def _room_overlap_checks(design: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks = []
    by_level: dict[str, list[Mapping[str, Any]]] = {}
    for room in design["rooms"]:
        by_level.setdefault(room["level_id"], []).append(room)
    for level, rooms in by_level.items():
        overlaps = []
        zones = [as_polygon(room["zone"]) for room in rooms]
        for index, first in enumerate(rooms):
            for offset, second in enumerate(rooms[index + 1 :], start=index + 1):
                area = zones[index].intersection(zones[offset]).area
                if area > 1e-7:
                    overlaps.append(
                        {"rooms": [first["id"], second["id"]], "area_m2": round(area, 6)}
                    )
        checks.append(
            check_result(
                f"room-overlap:{level}",
                "fail" if overlaps else "pass",
                "Room zones overlap." if overlaps else "Room zones have disjoint interiors.",
                overlaps=overlaps,
            )
        )
    return checks


def _opening_adjacent_rooms(design: Mapping[str, Any]) -> dict[str, list[str]]:
    rooms_by_level: dict[str, list[tuple[str, Any]]] = {}
    for room in design["rooms"]:
        rooms_by_level.setdefault(room["level_id"], []).append(
            (room["id"], as_polygon(room["zone"]))
        )
    walls = {wall["id"]: wall for wall in design["walls"]}
    result: dict[str, list[str]] = {}
    for opening in design["openings"]:
        wall = walls[opening["wall_id"]]
        midpoint = Point(wall_point(wall, opening["offset"] + opening["width"] / 2))
        probe = midpoint.buffer(max(0.16, wall["thickness"] / 2 + 0.08))
        adjacent = [
            room_id for room_id, zone in rooms_by_level[wall["level_id"]] if zone.intersects(probe)
        ]
        result[opening["id"]] = sorted(adjacent)
    return result


def _opening_room_pairs(
    design: Mapping[str, Any], adjacent: Mapping[str, list[str]]
) -> set[frozenset[str]]:
    return {
        frozenset(adjacent[opening["id"]])
        for opening in design["openings"]
        if opening["kind"] in PASSAGE_OPENING_KINDS
        and opening["sill"] <= 0.05
        and len(adjacent[opening["id"]]) == 2
    }


def _furnishing_checks(design: Mapping[str, Any]) -> list[dict[str, Any]]:
    furnishings = design.get("furnishings", [])
    if not furnishings:
        return [
            check_result(
                "furnishings",
                "review",
                "No furnishing plan is present; containment, clearance and fixtures are unresolved.",
            )
        ]
    rooms = {room["id"]: room for room in design["rooms"]}
    checks = []
    unmodeled_clearances = []
    for furnishing in furnishings:
        room = rooms[furnishing["room_id"]]
        policy = furnishing.get("containment_policy", "floor")
        if policy in {"room-envelope", "none"}:
            checks.append(
                check_result(
                    f"furnishing:{furnishing['id']}",
                    "pass",
                    "Explicit containment policy excludes this integrated or non-spatial element from floor-footprint gating.",
                    room_id=room["id"],
                    containment_policy=policy,
                )
            )
            continue
        footprint = furnishing_footprint(room, furnishing)
        clearance = furnishing_footprint(room, furnishing, clearance=True)
        clearance_values = furnishing.get("clearance_m", {})
        clearance_modeled = furnishing.get("clearance_status") == "modeled" or (
            furnishing.get("clearance_status") is None
            and any(float(value) > 0 for value in clearance_values.values())
        )
        if not clearance_modeled:
            unmodeled_clearances.append(furnishing["id"])
        room_polygon = as_polygon(room["zone"])
        checks.append(
            check_result(
                f"furnishing:{furnishing['id']}",
                "review",
                "Containment is preliminary until generated finished-floor polygons are supplied.",
                room_id=room["id"],
                footprint_contained=room_polygon.covers(footprint),
                clearance_contained=room_polygon.covers(clearance) if clearance_modeled else None,
                geometry_basis="authored-room-zone",
            )
        )
    if unmodeled_clearances:
        checks.append(
            check_result(
                "furnishing-clearance-model",
                "review",
                "Baseline operating clearances are explicitly not modeled and cannot support acceptance.",
                furnishing_ids=sorted(unmodeled_clearances),
                count=len(unmodeled_clearances),
            )
        )
    circulation = [item for item in furnishings if item.get("purpose") == "circulation-zone"]
    if not circulation:
        checks.append(
            check_result("circulation", "review", "No modeled circulation zones are declared.")
        )
    else:
        obstacles = [item for item in furnishings if item.get("purpose") != "circulation-zone"]
        collisions = []
        for zone in circulation:
            zone_polygon = furnishing_footprint(rooms[zone["room_id"]], zone)
            for obstacle in obstacles:
                if (
                    obstacle["room_id"] == zone["room_id"]
                    and zone_polygon.intersection(
                        furnishing_footprint(rooms[obstacle["room_id"]], obstacle)
                    ).area
                    > 1e-7
                ):
                    collisions.append([zone["id"], obstacle["id"]])
        checks.append(
            check_result(
                "circulation",
                "fail" if collisions else "pass",
                "Modeled circulation is obstructed."
                if collisions
                else "Modeled circulation zones are clear.",
                collisions=collisions,
            )
        )
    return checks


def _equipment_checks(
    design: Mapping[str, Any], catalog: Mapping[str, Any]
) -> list[dict[str, Any]]:
    furnishings = design["furnishings"]
    checks = []
    for rule in catalog.get("required_equipment", []):
        room_items = [item for item in furnishings if item.get("room_id") == rule["room_id"]]
        actual_purposes = {item.get("purpose") for item in room_items}
        missing = [purpose for purpose in rule["purposes"] if purpose not in actual_purposes]
        checks.append(
            check_result(
                f"equipment:{rule['requirement_id']}",
                "fail" if missing else "pass",
                "Required modeled equipment is missing."
                if missing
                else "Required modeled equipment is present.",
                room_id=rule["room_id"],
                missing=missing,
                requirement_ids=[rule["requirement_id"]],
            )
        )
    return checks


def _member_footprint(member: Mapping[str, Any]) -> Polygon:
    if member["kind"] == "column":
        (x, y), (sx, sy) = member["center"], member["section_m"]
        return box(x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2)
    return as_polygon(wall_footprint(member["start"], member["end"], member["width_m"]))


def _door_leaf_zone(wall: Mapping[str, Any], opening: Mapping[str, Any]) -> Polygon:
    """Plan zone a door leaf occupies while operating: the pocket or the swing sector."""

    lo, width = opening["offset"], opening["width"]
    if opening.get("door_style") == "sliding-pocket":
        shift = -width if opening["slide_direction"] == "toward-start" else width
        return as_polygon(
            wall_footprint(
                wall_point(wall, lo + shift),
                wall_point(wall, lo + width + shift),
                wall["thickness"],
            )
        )
    hinge_end = opening.get("hinge") == "end"
    hinge = wall_point(wall, lo + width if hinge_end else lo)
    toward = wall_point(wall, lo if hinge_end else lo + width)
    start_angle = math.atan2(toward[1] - hinge[1], toward[0] - hinge[0])
    swing = math.radians(opening.get("swing_deg", DEFAULT_DOOR_SWING_DEG))
    sweep = -swing if hinge_end else swing
    arc = [
        (
            hinge[0] + width * math.cos(start_angle + sweep * step / 16),
            hinge[1] + width * math.sin(start_angle + sweep * step / 16),
        )
        for step in range(17)
    ]
    return Polygon([tuple(hinge), *arc])


def _structure_obstacles(
    design: Mapping[str, Any],
) -> list[tuple[str, str, str, Polygon, float, float]]:
    """(kind, id, level, plan footprint, bottom z, top z) of everything a frame member must clear."""

    levels = {level["id"]: level for level in design["levels"]}
    rooms = {room["id"]: room for room in design["rooms"]}
    obstacles = []
    for furnishing in design.get("furnishings", []):
        dimensions = furnishing.get("dimensions", ())
        if furnishing.get("purpose") == "circulation-zone" or not all(
            float(value) > 0 for value in dimensions
        ):
            continue
        room = rooms[furnishing["room_id"]]
        base = levels[room["level_id"]]["elevation_m"] + float(furnishing["position"][2])
        height = float(dimensions[2])
        obstacles.append(
            (
                "furnishing",
                furnishing["id"],
                room["level_id"],
                furnishing_footprint(room, furnishing),
                base - height / 2,
                base + height / 2,
            )
        )
    walls = {wall["id"]: wall for wall in design["walls"]}
    for opening in design["openings"]:
        wall = walls[opening["wall_id"]]
        base = levels[wall["level_id"]]["elevation_m"]
        lo, hi = opening["offset"], opening["offset"] + opening["width"]
        zones = [
            as_polygon(
                wall_footprint(wall_point(wall, lo), wall_point(wall, hi), wall["thickness"])
            )
        ]
        if opening["kind"] == "door":
            zones.append(_door_leaf_zone(wall, opening))
        obstacles.append(
            (
                "opening",
                opening["id"],
                wall["level_id"],
                unary_union(zones),
                base + opening["sill"],
                base + opening["head"],
            )
        )
    builder = Builder(design, compile_design(design))
    stairs(builder)
    for mesh in builder.meshes:
        z_values = [vertex[2] for vertex in mesh["vertices"]]
        obstacles.append(
            (
                "stair",
                mesh["id"],
                mesh["properties"]["Floor level"],
                MultiPoint([vertex[:2] for vertex in mesh["vertices"]]).convex_hull,
                min(z_values),
                max(z_values),
            )
        )
    return obstacles


def _structure_checks(design: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Frame members below the ceiling must clear furnishings, door zones and stair parts."""

    members = frame_members(design)
    if not members:
        return []
    # Occupied height band (floor to ceiling) of each storey; a member counts where it enters one,
    # so ground-level upturned beams are checked against the storey above.
    storeys = {
        level["id"]: (
            level["elevation_m"],
            min(
                (
                    slab["base_z_m"]
                    for slab in design["slabs"]
                    if slab["level_id"] == level["id"] and slab.get("role") == "ceiling"
                ),
                default=level["elevation_m"] + level["clear_height_m"],
            ),
        )
        for level in design["levels"]
    }
    obstacles = _structure_obstacles(design)
    wall_footprints: dict[str, list[Polygon]] = {}
    for wall in design["walls"]:
        wall_footprints.setdefault(wall["level_id"], []).append(
            as_polygon(wall_footprint(wall["start"], wall["end"], wall["thickness"]))
        )
    collisions = []
    checks = []
    for member in members:
        level_id = member["level_id"]
        footprint = _member_footprint(member)
        if member["kind"] == "column" and not any(
            footprint.intersects(wall) for wall in wall_footprints.get(level_id, [])
        ):
            checks.append(
                check_result(
                    f"structure:free-standing:{member['id']}",
                    "review",
                    "Column touches no wall; confirm it reads as an intended free-standing column.",
                    mark=member["mark"],
                    level_id=level_id,
                )
            )
        for kind, obstacle_id, obstacle_level, shape, low, high in obstacles:
            floor, ceiling = storeys[obstacle_level]
            bottom = max(member["bottom_z_m"], floor, low)
            if min(member["top_z_m"], ceiling, high) - bottom <= 1e-6:
                continue
            overlap = footprint.intersection(shape).area
            if overlap > STRUCTURE_CLASH_AREA_M2:
                collisions.append(
                    {
                        "member_id": member["id"],
                        "mark": member["mark"],
                        "obstacle_kind": kind,
                        "obstacle_id": obstacle_id,
                        "overlap_m2": round(overlap, 6),
                    }
                )
    checks.insert(
        0,
        check_result(
            "structure:clearance",
            "fail" if collisions else "pass",
            "Frame members below the ceiling collide with furnishings, door zones or stair parts."
            if collisions
            else "Frame members below the ceiling clear furnishings, door zones and stair parts.",
            member_count=len(members),
            collisions=collisions,
        ),
    )
    return checks


def _brief_checks(
    design: Mapping[str, Any],
    catalog: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Every record the catalogue or the design's semantic_refs cite must exist in the brief.

    Review notes pass through.
    """

    cited = _cited_requirements(catalog)
    cited.update(
        record for reference in design["semantic_refs"] for record in reference["requirements"]
    )
    missing = sorted(cited - set(records))
    checks = [
        check_result(
            "brief-references",
            "fail" if missing else "pass",
            "Referenced brief records are missing from the brief."
            if missing
            else "Every referenced brief record exists in the brief.",
            missing_record_ids=missing,
        )
    ]
    for rule in catalog.get("review_only", []):
        checks.append(
            check_result(
                "review:" + "+".join(rule["requirement_ids"]),
                "review",
                rule["reason"],
                requirement_ids=rule["requirement_ids"],
            )
        )
    return checks


def _stair_geometry_checks(
    design: Mapping[str, Any], catalog: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Check each authored stair against the recorded NP 057-02 step relation and flight limit."""

    rule = catalog.get("stair_geometry")
    if not rule:
        return []
    checks = []
    for stair in design.get("stairs", []):
        riser_cm = stair["riser_height_m"] * 100
        tread_cm = stair["tread_depth_m"] * 100
        formula_cm = 2 * riser_cm + tread_cm
        risers_per_flight = math.ceil(stair["riser_count"] / int(rule.get("flights", 1)))
        in_band = rule["formula_min_cm"] - 1e-9 <= formula_cm <= rule["formula_max_cm"] + 1e-9
        flight_ok = risers_per_flight <= int(rule["max_risers_per_flight"])
        checks.append(
            check_result(
                f"stair:np057:{stair['id']}",
                "pass" if in_band and flight_ok else "fail",
                "Stair step relation and flight length satisfy the recorded Romanian rule."
                if in_band and flight_ok
                else "Stair step relation or flight length breaks the recorded Romanian rule.",
                formula_cm=round(formula_cm, 3),
                band_cm=[rule["formula_min_cm"], rule["formula_max_cm"]],
                riser_mm=round(riser_cm * 10, 1),
                tread_mm=round(tread_cm * 10, 1),
                risers_per_flight=risers_per_flight,
                max_risers_per_flight=int(rule["max_risers_per_flight"]),
                source=rule.get("source"),
                requirement_ids=rule["requirement_ids"],
            )
        )
    return checks


def _gross_area_check(
    check_id: str,
    area: float,
    rule: Mapping[str, Any],
    messages: tuple[str, str, str],
    area_key: str,
) -> dict[str, Any]:
    """Classify a gross area against the cap: fail, near-limit review, or pass."""
    cap = float(rule["cap_m2"])
    margin = cap - area
    near_limit = max(CONCEPT_NEAR_LIMIT_MIN_M2, cap * CONCEPT_NEAR_LIMIT_FRACTION)
    exceeds, near, within = messages
    if area > cap + GROSS_MEASUREMENT_TOLERANCE_M2:
        status, message = "fail", exceeds
    elif margin <= near_limit:
        status, message = "review", near
    else:
        status, message = "pass", within
    return check_result(
        check_id,
        status,
        message,
        **{area_key: area},
        cap_m2=cap,
        margin_m2=round(margin, 6),
        concept_near_limit_m2=near_limit,
        measurement_tolerance_m2=GROSS_MEASUREMENT_TOLERANCE_M2,
        requirement_ids=rule["requirement_ids"],
    )


def _clear_height_status(actual: float | None, expected: float, minimum: float) -> str:
    # Evaluated Blender float coordinates lose micrometres on subtraction. This
    # numeric allowance is separate from the much larger concept-design tolerance.
    if actual is None or actual < minimum - 1e-5:
        return "fail"
    # The tiny epsilon keeps a nominal 0.10 m drift inside the concept tolerance.
    within = abs(actual - expected) <= CLEAR_HEIGHT_CONCEPT_TOLERANCE_M + 1e-6
    return "pass" if within else "review"


def _summary(checks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {
        status: sum(check["status"] == status for check in checks)
        for status in ("pass", "fail", "review")
    }
    return {
        "decision": "reject"
        if counts["fail"]
        else ("requires-review" if counts["review"] else "accept"),
        "counts": counts,
    }


def check_design(
    design: Mapping[str, Any],
    catalog: Mapping[str, Any],
    brief_root: str | Path,
) -> dict[str, Any]:
    """Run the pre-build gate; intended data can never satisfy post-build checks."""

    try:
        candidate = validate_design(design)
    except DesignValidationError as exc:
        checks = [check_result("structural-validation", "fail", str(exc))]
        return {
            "schema_version": 1,
            "phase": "pre-build",
            "summary": _summary(checks),
            "checks": checks,
        }
    records = brief_records(brief_root)
    checks = [
        check_result(
            "structural-validation",
            "pass",
            "Schema, IDs, references, polygons and openings are valid.",
        )
    ]
    checks.extend(_brief_checks(candidate, catalog, records))
    checks.extend(_room_overlap_checks(candidate))

    programme = catalog["programme"]
    expected = programme["rooms"]
    actual = {room["id"]: room["level_id"] for room in candidate["rooms"]}
    checks.append(
        check_result(
            "required-programme",
            "pass" if actual == expected else "fail",
            "Required room programme and levels match."
            if actual == expected
            else "Required room programme or level assignment changed.",
            missing=sorted(set(expected) - set(actual)),
            unexpected=sorted(set(actual) - set(expected)),
            wrong_level=sorted(
                room_id
                for room_id in set(expected) & set(actual)
                if expected[room_id] != actual[room_id]
            ),
            requirement_ids=programme["requirement_ids"],
        )
    )
    opening_rooms = _opening_adjacent_rooms(candidate)
    room_pairs = _opening_room_pairs(candidate, opening_rooms)
    for rule in catalog["direct_connections"]:
        connected = frozenset(rule["rooms"]) in room_pairs
        checks.append(
            check_result(
                "connection:" + ":".join(rule["rooms"]),
                "pass" if connected else "fail",
                "Required direct connection is modeled."
                if connected
                else "Required direct connection is missing or blocked.",
                rooms=rule["rooms"],
                requirement_ids=rule["requirement_ids"],
            )
        )
    single_window = catalog.get("single_window", {"room_ids": []})
    for room_id in single_window["room_ids"]:
        opening_count = sum(
            opening["kind"] in {"window", "double"}
            and opening_rooms.get(opening["id"]) == [room_id]
            for opening in candidate["openings"]
        )
        checks.append(
            check_result(
                f"single-window:{room_id}",
                "pass" if opening_count == 1 else "fail",
                "Room has exactly one exterior glazed opening."
                if opening_count == 1
                else "Room does not have exactly one exterior glazed opening.",
                count=opening_count,
                requirement_ids=single_window["requirement_ids"],
            )
        )
    explicit_operations = [
        opening for opening in candidate["openings"] if opening.get("operation") == "sliding"
    ]
    for opening in explicit_operations:
        active_panel = 1 if opening["slide_direction"] == "toward-start" else 0
        checks.append(
            check_result(
                f"opening-operation:{opening['id']}",
                "pass",
                "Two-panel sliding operation is explicitly encoded relative to the wall direction.",
                operation="sliding",
                panel_count=opening["panel_count"],
                active_panel=active_panel,
                slide_direction=opening["slide_direction"],
            )
        )
    unresolved_operability = [
        opening["id"]
        for opening in candidate["openings"]
        if opening["kind"] in {"terrace", "window", "double"} and not opening.get("operation")
    ]
    checks.append(
        check_result(
            "opening:operability",
            "review",
            "Operation is encoded only for explicitly configured openings; other glazed-opening operability remains unresolved.",
            explicit_operation_ids=[opening["id"] for opening in explicit_operations],
            unresolved_opening_ids=unresolved_operability,
        )
    )
    if pv_rule := catalog.get("pv_modules"):
        pv_count = sum(
            roof["pv"]["columns"] * roof["pv"]["rows"]
            for roof in candidate["roofs"]
            if roof.get("pv")
        )
        checks.append(
            check_result(
                "pv-modules",
                "pass" if pv_count == pv_rule["count"] else "fail",
                "Authored roof PV arrays hold the required module count."
                if pv_count == pv_rule["count"]
                else "Authored roof PV arrays do not hold the required module count.",
                expected=pv_rule["count"],
                actual=pv_count,
                requirement_ids=pv_rule["requirement_ids"],
            )
        )
    checks.extend(_furnishing_checks(candidate))
    checks.extend(_equipment_checks(candidate, catalog))
    site_components = candidate.get("site_components", [])
    site_purposes = {component.get("purpose") for component in site_components}
    for rule in catalog.get("required_site_components", []):
        matching = [
            component for component in site_components if component.get("purpose") in rule["kinds"]
        ]
        missing = [kind for kind in rule["kinds"] if kind not in site_purposes]
        minimum_count = int(rule.get("minimum_count", 1))
        count_ok = len(matching) >= minimum_count
        expected_built = rule.get("built")
        built_ok = expected_built is None or all(
            component.get("built") is expected_built for component in matching
        )
        present = not missing and count_ok and built_ok
        checks.append(
            check_result(
                f"site:{rule['requirement_id']}",
                "pass" if present else "fail",
                "Required outdoor provision is modeled."
                if present
                else "Required outdoor provision is missing.",
                required_kinds=rule["kinds"],
                missing=missing,
                minimum_count=minimum_count,
                actual_count=len(matching),
                expected_built=expected_built,
                built_matches=built_ok,
                requirement_ids=[rule["requirement_id"]],
            )
        )
    equipment = [*candidate.get("furnishings", []), *site_components]
    for rule in catalog.get("forbidden_equipment", []):
        found = [item["id"] for item in equipment if item.get("purpose") in rule["purposes"]]
        checks.append(
            check_result(
                f"forbidden-equipment:{rule['requirement_id']}",
                "fail" if found else "pass",
                "Forbidden equipment is explicitly modeled."
                if found
                else "No forbidden equipment is declared in the semantic design.",
                forbidden_purposes=rule["purposes"],
                found=found,
                requirement_ids=[rule["requirement_id"]],
            )
        )

    quantities = design_quantities(candidate)
    checks.append(
        _gross_area_check(
            "gross-area:authored-wall-body",
            quantities["house_wall_body_gross_m2"],
            catalog["gross_area"],
            (
                "Authored wall-body area exceeds the finished-gross target beyond concept measurement tolerance.",
                "Authored wall-body area is close to the finished-gross target; retain concept-stage uncertainty.",
                "Authored wall-body gross area is below the finished-gross target; saved mesh evidence is still required.",
            ),
            "wall_body_gross_m2",
        )
    )
    checks.append(
        check_result(
            "gross-area:actual-finished",
            "review",
            "Finished gross area requires independent evaluated mesh evidence.",
            requirement_ids=catalog["gross_area"]["requirement_ids"],
        )
    )
    setback = catalog["setback"]
    checks.append(
        check_result(
            "setback:actual",
            "review",
            f"The {setback['minimum_m']:g} m setback requires independent evaluated mesh "
            "footprints; authored bounds are not evidence.",
            requirement_ids=setback["requirement_ids"],
        )
    )
    level_heights = {level["id"]: level["clear_height_m"] for level in candidate["levels"]}
    clear_heights = catalog["clear_heights"]
    minimum_height = float(clear_heights["minimum_habitable_m"])
    for level_id, expected_height in clear_heights["levels_m"].items():
        actual_height = level_heights.get(level_id)
        status = _clear_height_status(actual_height, expected_height, minimum_height)
        checks.append(
            check_result(
                f"clear-height:{level_id}",
                status,
                "Authored clear height is within the nominal concept tolerance."
                if status == "pass"
                else (
                    "Authored clear height is missing or below the recorded minimum threshold."
                    if status == "fail"
                    else "Authored clear height differs materially from nominal intent and needs review."
                ),
                expected_m=expected_height,
                actual_m=actual_height,
                concept_tolerance_m=CLEAR_HEIGHT_CONCEPT_TOLERANCE_M,
                recorded_minimum_m=minimum_height,
                requirement_ids=clear_heights["requirement_ids"],
            )
        )
    checks.extend(_stair_geometry_checks(candidate, catalog))
    checks.extend(authored_corridor_checks(candidate, catalog))
    checks.extend(_structure_checks(candidate))
    return {
        "schema_version": 1,
        "phase": "pre-build",
        "source_fingerprint": source_fingerprint(candidate),
        "summary": _summary(checks),
        "quantities": quantities,
        "checks": checks,
    }


def check_actual_geometry(
    design: Mapping[str, Any],
    catalog: Mapping[str, Any],
    brief_root: str | Path,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Run post-build checks against evaluated world-space geometry exported from the saved blend."""

    prebuild = check_design(design, catalog, brief_root)
    checks = [
        check
        for check in prebuild["checks"]
        if check["id"] not in {"gross-area:actual-finished", "setback:actual"}
    ]
    setback = catalog["setback"]
    try:
        measured = measured_mesh_quantities(design, evidence, float(setback["minimum_m"]))
    except (TypeError, ValueError, KeyError) as exc:
        checks.append(check_result("actual-geometry-evidence", "fail", str(exc)))
        return {**prebuild, "phase": "post-build", "summary": _summary(checks), "checks": checks}
    expected_components = {
        entity["id"]
        for collection in ("rooms", "walls", "slabs", "roofs", "stairs", "site_components")
        for entity in design.get(collection, [])
    }
    expected_components.update(member["id"] for member in frame_members(design))
    expected_components.update(
        opening["id"]
        for opening in design.get("openings", [])
        if opening.get("kind") not in {"open"}
    )
    expected_components.update(
        furnishing["id"]
        for furnishing in design.get("furnishings", [])
        if furnishing.get("containment_policy", "floor") == "floor"
        and all(float(value) > 0 for value in furnishing.get("dimensions", ()))
    )
    actual_components = set(measured["component_ids"])
    missing_components = sorted(expected_components - actual_components)
    checks.append(
        check_result(
            "actual-geometry-coverage",
            "fail" if missing_components else "pass",
            "Actual export omits generated semantic components."
            if missing_components
            else "Actual export covers every generated semantic component.",
            missing_component_ids=missing_components,
        )
    )
    checks.extend(check_actual_placements_and_passages(design, evidence))
    opening_rooms = _opening_adjacent_rooms(design)
    checks.extend(actual_corridor_checks(design, catalog, evidence, opening_rooms))
    if "main_bathroom_access" in catalog:
        checks.append(actual_bath_access_check(design, catalog, evidence, opening_rooms))
    checks.append(
        _gross_area_check(
            "gross-area:actual-finished",
            measured["house_finished_gross_m2"],
            catalog["gross_area"],
            (
                "Actual finished gross area exceeds the household target beyond concept measurement tolerance.",
                "Actual finished gross area is within the target but close enough to retain concept-stage uncertainty.",
                "Actual finished gross area is within the household target.",
            ),
            "finished_gross_m2",
        )
    )
    required_setback = float(setback["minimum_m"])
    measured_setback = float(measured["minimum_setback_m"])
    setback_shortfall = required_setback - measured_setback
    inconsistent_setbacks = [
        item
        for item in measured["setbacks"]
        if not item["inside_inset"] and item["clearance_m"] >= required_setback
    ]
    setback_status = (
        "fail"
        if setback_shortfall > SETBACK_MEASUREMENT_TOLERANCE_M or inconsistent_setbacks
        else ("review" if setback_shortfall > 0 else "pass")
    )
    checks.append(
        check_result(
            "setback:actual",
            setback_status,
            "Actual building footprints breach the parcel inset beyond concept measurement tolerance or have inconsistent geometry."
            if setback_status == "fail"
            else (
                "Actual minimum setback is within concept measurement tolerance of the target and needs review."
                if setback_status == "review"
                else "Actual tagged building footprints are inside the parcel inset."
            ),
            minimum_setback_m=measured_setback,
            required_m=required_setback,
            shortfall_m=max(0.0, round(setback_shortfall, 6)),
            measurement_tolerance_m=SETBACK_MEASUREMENT_TOLERANCE_M,
            inconsistent_geometry=inconsistent_setbacks,
            requirement_ids=setback["requirement_ids"],
        )
    )
    clear_heights = catalog["clear_heights"]
    minimum_height = float(clear_heights["minimum_habitable_m"])
    for level_id, expected_height in clear_heights["levels_m"].items():
        actual_height = measured["finished_clear_height_by_level_m"][level_id]
        delta = actual_height - expected_height
        status = _clear_height_status(actual_height, expected_height, minimum_height)
        checks.append(
            check_result(
                f"clear-height:actual:{level_id}",
                status,
                "Concept mesh clear height is within the nominal design tolerance."
                if status == "pass"
                else (
                    "Actual mesh clear height is below the recorded minimum threshold."
                    if status == "fail"
                    else "Concept mesh clear height differs materially from nominal intent and needs review."
                ),
                expected_m=expected_height,
                actual_m=actual_height,
                delta_m=round(delta, 6),
                concept_tolerance_m=CLEAR_HEIGHT_CONCEPT_TOLERANCE_M,
                recorded_minimum_m=minimum_height,
                requirement_ids=clear_heights["requirement_ids"],
            )
        )
    return {
        **prebuild,
        "phase": "post-build",
        "summary": _summary(checks),
        "actual_quantities": measured,
        "checks": checks,
    }
