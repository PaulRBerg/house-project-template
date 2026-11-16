from __future__ import annotations

import math
from copy import deepcopy

import pytest
from shapely.geometry import LineString, Point, Polygon

from engine import paths
from engine.compiler import frame_members
from engine.geometry import furnishing_footprint, map_plan
from engine.persistence import evidence_fingerprint
from engine.requirements import (
    brief_records,
    check_actual_geometry,
    check_design,
)


def test_brief_parser_reads_first_column_ids_and_inherits_h2_stage(tmp_path):
    root = tmp_path
    (root / "a.md").write_text(
        """# A

| ID | Spațiu | Poziție |
| --- | --- | --- |
| `CTX-01` | Context   compact | A doua celulă |

## La gri

### Subsecțiune

| ID | Bun | Cantitate | Integrare |
| --- | --- | --- | --- |
| `ACT-01` | Echipament | 1 | Text   normalizat |

## Referințe

| `CTX-02` | Context după o secțiune fără etapă |
""",
        encoding="utf-8",
    )
    records = brief_records(root)

    assert set(records) == {"CTX-01", "ACT-01", "CTX-02"}
    assert records["CTX-01"]["stage"] is None
    assert records["ACT-01"]["stage"] == "La gri"
    assert records["CTX-02"]["stage"] is None
    assert records["ACT-01"]["content"] == "Echipament | 1 | Text normalizat"


def test_brief_parser_rejects_duplicate_first_column_id(tmp_path):
    root = tmp_path
    (root / "a.md").write_text("| `DUP-01` | Prima |\n", encoding="utf-8")
    (root / "b.md").write_text("| `DUP-01` | A doua |\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate brief record DUP-01"):
        brief_records(root)


def test_prebuild_report_rejects_overlapping_room_zones(design, requirements, check_by_id):
    changed = deepcopy(design)
    changed["rooms"][1]["zone"] = deepcopy(changed["rooms"][0]["zone"])
    changed["rooms"][1]["anchor"] = deepcopy(changed["rooms"][0]["anchor"])
    report = check_design(changed, requirements, paths.BRIEF)
    overlap = check_by_id(report, "room-overlap:G")
    assert overlap["status"] == "fail"
    assert report["summary"]["decision"] == "reject"


def test_pv_module_count_follows_authored_roof_arrays(
    design, requirements, prebuild_report, check_by_id
):
    check = check_by_id(prebuild_report, "pv-modules")
    authored = sum(
        roof["pv"]["columns"] * roof["pv"]["rows"] for roof in design["roofs"] if roof.get("pv")
    )
    assert check["status"] == "pass"
    assert check["evidence"]["actual"] == authored == requirements["pv_modules"]["count"]
    assert check["evidence"]["requirement_ids"] == requirements["pv_modules"]["requirement_ids"]

    changed = deepcopy(design)
    next(roof for roof in changed["roofs"] if roof.get("pv"))["pv"]["columns"] -= 1
    check = check_by_id(check_design(changed, requirements, paths.BRIEF), "pv-modules")
    assert check["status"] == "fail"


def test_authored_clear_height_uses_concept_tolerance(design, requirements, check_by_id):
    target = requirements["clear_heights"]["levels_m"]["G"]
    changed = deepcopy(design)
    ground = next(level for level in changed["levels"] if level["id"] == "G")
    ground["clear_height_m"] = target
    report = check_design(changed, requirements, paths.BRIEF)
    check = check_by_id(report, "clear-height:G")
    assert check["status"] == "pass"
    assert (
        check["evidence"]["recorded_minimum_m"]
        == requirements["clear_heights"]["minimum_habitable_m"]
    )

    ground["clear_height_m"] = requirements["clear_heights"]["minimum_habitable_m"] - 0.01
    check = check_by_id(check_design(changed, requirements, paths.BRIEF), "clear-height:G")
    assert check["status"] == "fail"
    ground["clear_height_m"] = target
    # Height variants above the accepted ordinary-room target require review.
    ground["clear_height_m"] += 0.15
    report = check_design(changed, requirements, paths.BRIEF)
    check = check_by_id(report, "clear-height:G")
    assert check["status"] == "review"


@pytest.mark.parametrize(("direction", "active_panel"), [("toward-end", 0), ("toward-start", 1)])
def test_explicit_sliding_openings_report_resolved_leaf_and_sense(
    design, requirements, check_by_id, direction, active_panel
):
    changed = deepcopy(design)
    sliding = [opening for opening in changed["openings"] if opening.get("operation") == "sliding"]
    assert sliding
    for opening in sliding:
        opening["slide_direction"] = direction
    report = check_design(changed, requirements, paths.BRIEF)
    for opening in sliding:
        operation = check_by_id(report, f"opening-operation:{opening['id']}")
        assert operation["status"] == "pass"
        assert operation["evidence"]["slide_direction"] == direction
        assert operation["evidence"]["active_panel"] == active_panel
    operability = check_by_id(report, "opening:operability")
    assert operability["status"] == "review"
    ids = [opening["id"] for opening in sliding]
    assert operability["evidence"]["explicit_operation_ids"] == ids
    assert set(ids).isdisjoint(operability["evidence"]["unresolved_opening_ids"])
    assert operability["evidence"]["unresolved_opening_ids"]


def test_stair_geometry_follows_recorded_romanian_rule(
    design, requirements, prebuild_report, check_by_id
):
    report = prebuild_report
    check = check_by_id(report, "stair:np057:stair-main")
    assert check["status"] == "pass"
    stair = design["stairs"][0]
    rise = design["levels"][1]["elevation_m"] - design["levels"][0]["elevation_m"]
    expected = 100 * (2 * rise / stair["riser_count"] + stair["tread_depth_m"])
    assert check["evidence"]["formula_cm"] == pytest.approx(expected, abs=1e-3)
    assert check["evidence"]["risers_per_flight"] == stair["riser_count"] // 2

    changed = deepcopy(design)
    changed["stairs"][0]["tread_depth_m"] = 0.25
    report = check_design(changed, requirements, paths.BRIEF)
    check = check_by_id(report, "stair:np057:stair-main")
    assert check["status"] == "fail"
    assert report["summary"]["decision"] == "reject"


def test_authored_corridor_widths_are_review_only(
    design, requirements, prebuild_report, check_by_id
):
    rule = requirements["corridor_width"]
    rooms = {room["id"]: room for room in design["rooms"]}
    for room_id in rule["room_ids"]:
        check = check_by_id(prebuild_report, f"corridor:authored:{room_id}")
        assert check["status"] == "review"
        assert check["evidence"]["requirement_ids"] == rule["requirement_ids"]
        assert check["evidence"]["minimum_m"] == rule["minimum_m"]
        zone = Polygon(rooms[room_id]["zone"]["outer"])
        if zone.area == pytest.approx(zone.minimum_rotated_rectangle.area):
            x0, y0, x1, y1 = zone.bounds
            assert check["evidence"]["zone_min_width_m"] == pytest.approx(
                min(x1 - x0, y1 - y0), abs=0.002
            )
    assert check_by_id(prebuild_report, "brief-references")["status"] == "pass"


def test_outdoor_presence_requires_explicit_semantic_purpose(design, requirements, check_by_id):
    changed = deepcopy(design)
    for component in changed.get("site_components", []):
        if component.get("purpose") == "parking":
            del component["purpose"]
    rule = next(
        rule for rule in requirements["required_site_components"] if "parking" in rule["kinds"]
    )
    report = check_design(changed, requirements, paths.BRIEF)
    parking = check_by_id(report, f"site:{rule['requirement_id']}")
    assert parking["status"] == "fail"
    assert parking["evidence"]["missing"] == ["parking"]


def test_required_equipment_requires_explicit_semantic_purpose(design, requirements, check_by_id):
    changed = deepcopy(design)
    shower = next(
        furnishing
        for furnishing in changed["furnishings"]
        if furnishing.get("room_id") == "G-BATH" and furnishing.get("purpose") == "shower"
    )
    assert "shower" in shower["id"]
    shower["purpose"] = "furnishing"
    report = check_design(changed, requirements, paths.BRIEF)
    equipment = check_by_id(report, "equipment:RM-BATH-01")
    assert equipment["status"] == "fail"
    assert "shower" in equipment["evidence"]["missing"]


def test_combined_requirements_preserve_every_required_semantic_part(
    design, requirements, check_by_id
):
    changed = deepcopy(design)
    tub = next(
        furnishing
        for furnishing in changed["furnishings"]
        if furnishing.get("purpose") == "bathtub"
    )
    tub["purpose"] = "furnishing"
    gate = next(
        component
        for component in changed["site_components"]
        if component.get("purpose") == "pedestrian-gate"
    )
    gate["purpose"] = "furnishing"
    report = check_design(changed, requirements, paths.BRIEF)

    bathroom_rule = next(
        rule for rule in requirements["required_equipment"] if "bathtub" in rule["purposes"]
    )
    gate_rule = next(
        rule
        for rule in requirements["required_site_components"]
        if "pedestrian-gate" in rule["kinds"]
    )
    bathroom = check_by_id(report, f"equipment:{bathroom_rule['requirement_id']}")
    gates = check_by_id(report, f"site:{gate_rule['requirement_id']}")
    assert bathroom["status"] == "fail"
    assert bathroom["evidence"]["missing"] == ["bathtub"]
    assert gates["status"] == "fail"
    assert gates["evidence"]["missing"] == ["pedestrian-gate"]


def test_future_provisions_and_forbidden_equipment_keep_constraints_and_review_notes(
    design, requirements, prebuild_report, check_by_id
):
    for rule in requirements["review_only"]:
        note = check_by_id(prebuild_report, "review:" + "+".join(rule["requirement_ids"]))
        assert note["status"] == "review"
        assert note["evidence"]["requirement_ids"] == rule["requirement_ids"]
        assert note["message"] == rule["reason"]

    # A future, not-yet-built battery provision and a forbidden electric water heater.
    catalog = deepcopy(requirements)
    catalog["required_site_components"].append(
        {"requirement_id": "EN-07", "kinds": ["future-battery-provision"], "built": False}
    )
    catalog["forbidden_equipment"] = [
        {"requirement_id": "EN-04", "purposes": ["electric-water-heater"]}
    ]
    changed = deepcopy(design)
    provision = {
        "id": "site-future-battery",
        "name": "Rezervă pentru baterie",
        "kind": "generated_site",
        "purpose": "future-battery-provision",
        "built": False,
        "parts": [
            {
                "id": "battery-provision",
                "primitive": "box",
                "position": [3, 3, 0.05],
                "dimensions": [0.6, 0.4, 0.1],
                "material_id": "mat_stone_grey",
            }
        ],
    }
    changed["site_components"].append(provision)
    report = check_design(changed, catalog, paths.BRIEF)
    link = check_by_id(report, "site:EN-07")
    tank = check_by_id(report, "forbidden-equipment:EN-04")
    assert link["status"] == "pass"
    assert link["evidence"]["expected_built"] is False
    assert tank["status"] == "pass"

    provision["built"] = True
    changed["site_components"][0]["purpose"] = "electric-water-heater"
    changed_report = check_design(changed, catalog, paths.BRIEF)
    assert check_by_id(changed_report, "site:EN-07")["status"] == "fail"
    tank = check_by_id(changed_report, "forbidden-equipment:EN-04")
    assert tank["status"] == "fail"
    assert tank["evidence"]["found"] == [changed["site_components"][0]["id"]]


def test_postbuild_uses_mesh_surfaces_for_clear_height(voided_design, requirements, check_by_id):
    design = voided_design
    prebuild = check_design(design, requirements, paths.BRIEF)
    objects = []
    setback_subject = design["roofs"][0]["id"]
    void = design["voids"][0]
    x0, y0, x1, y1 = map_plan(void["polygon"], design["transform"]).bounds

    def add_object(
        component_id: str,
        kind: str,
        level_id: str | None = None,
        z: float = 0,
        gross_role: str | None = None,
    ) -> None:
        # Keep the excluded volume clear of the intermediate ceiling/slab and upper floors.
        blocking = component_id in {
            sid for void in design.get("voids", []) for sid in void["cut_slab_ids"]
        }
        shift = 10 if blocking or (kind == "room_floor" and level_id == "U") else 0
        vertices = [
            [x0 + shift, y0, z],
            [x1 + shift, y0, z],
            [x1 + shift, y1, z],
            [x0 + shift, y1, z],
        ]
        if kind == "void":
            region = map_plan(void["polygon"], design["transform"])
            vertices = [[x, y, z] for x, y in list(region.exterior.coords)[:-1]]
        faces = [list(range(len(vertices)))]
        properties = {"Setback subject": component_id == setback_subject}
        if level_id:
            properties["Floor level"] = level_id
        if gross_role:
            properties["Gross area role"] = gross_role
            properties["Gross boundary source"] = component_id
        if kind == "room_floor":
            properties["Room ID"] = component_id
        objects.append(
            {
                "id": f"actual-{component_id}",
                "component_id": component_id,
                "kind": kind,
                "vertices_world": vertices,
                "faces": faces,
                "properties": properties,
                "evaluated_geometry_fingerprint": evidence_fingerprint(vertices, faces),
            }
        )

    for collection, kind in (
        ("rooms", "room_floor"),
        ("walls", "wall"),
        ("openings", "opening"),
        ("roofs", "roof"),
        ("stairs", "stair"),
        ("site_components", "site_component"),
    ):
        for entity in design.get(collection, []):
            level_id = entity.get("level_id")
            z = next(
                (level["elevation_m"] for level in design["levels"] if level["id"] == level_id),
                0,
            )
            if kind == "room_floor":
                z += next(
                    level["floor_top_offset_m"]
                    for level in design["levels"]
                    if level["id"] == level_id
                )
            gross_role = None
            if collection == "walls" and entity.get("role") == "exterior":
                gross_role = "finished-exterior-boundary"
            add_object(entity["id"], kind, level_id, z, gross_role)
    for void in design.get("voids", []):
        add_object(void["id"], "void", void["level_id"], gross_role="excluded-void")
    for slab in design["slabs"]:
        kind = "ceiling" if slab.get("role") == "ceiling" else "slab"
        z = slab["base_z_m"] if kind == "ceiling" else 0
        add_object(slab["id"], kind, slab["level_id"], z)
    for member in frame_members(design):
        add_object(member["id"], member["kind"], member["level_id"], member["bottom_z_m"])
    for furnishing in design.get("furnishings", []):
        if furnishing.get("containment_policy") != "none" and all(
            float(value) > 0 for value in furnishing.get("dimensions", ())
        ):
            add_object(furnishing["id"], "furnishing")
    evidence = {
        "evidence_kind": "exported_mesh",
        "coordinate_space": "world",
        "source_fingerprint": prebuild["source_fingerprint"],
        "saved_blend_sha256": "a" * 64,
        "provenance": {"exporter": "test", "exported_at": "2026-09-21T00:00:00Z"},
        "objects": objects,
    }
    report = check_actual_geometry(design, requirements, paths.BRIEF, evidence)
    coverage = check_by_id(report, "actual-geometry-coverage")
    ground = check_by_id(report, "clear-height:actual:G")
    assert coverage["status"] == "pass"
    assert ground["status"] == "pass"
    level = next(level for level in design["levels"] if level["id"] == "G")
    ceiling = next(slab for slab in design["slabs"] if slab["id"] == "ceiling-g")
    assert ground["evidence"]["actual_m"] == pytest.approx(
        ceiling["base_z_m"] - level["elevation_m"] - level["floor_top_offset_m"]
    )
    assert ground["evidence"]["concept_tolerance_m"] == 0.10

    measured = report["actual_quantities"]
    near = deepcopy(requirements)
    near["gross_area"]["cap_m2"] = measured["house_finished_gross_m2"] - 0.01
    near["setback"]["minimum_m"] = measured["minimum_setback_m"] + 0.001
    near_report = check_actual_geometry(design, near, paths.BRIEF, evidence)
    near_gross = check_by_id(near_report, "gross-area:actual-finished")
    near_setback = check_by_id(near_report, "setback:actual")
    assert near_gross["status"] == "review"
    assert near_setback["status"] == "review"

    excessive = deepcopy(requirements)
    excessive["gross_area"]["cap_m2"] = measured["house_finished_gross_m2"] - 0.2
    excessive["setback"]["minimum_m"] = measured["minimum_setback_m"] + 0.02
    excessive_report = check_actual_geometry(design, excessive, paths.BRIEF, evidence)
    excessive_gross = check_by_id(excessive_report, "gross-area:actual-finished")
    excessive_setback = check_by_id(excessive_report, "setback:actual")
    assert excessive_gross["status"] == "fail"
    assert excessive_setback["status"] == "fail"


def test_structure_clearance_fails_when_a_column_hits_furniture(
    design, requirements, prebuild_report, check_by_id
):
    assert check_by_id(prebuild_report, "structure:clearance")["status"] == "pass"
    changed = deepcopy(design)
    column = next(m for m in changed["structure"] if m["kind"] == "column" and m["level_id"] == "G")
    rooms = {room["id"]: room for room in changed["rooms"]}
    wardrobe = next(
        item
        for item in changed["furnishings"]
        if rooms[item["room_id"]]["level_id"] == "G"
        and (item.get("generated") or {}).get("kind") == "joinery"
        and item.get("containment_policy") == "floor"
    )
    room = rooms[wardrobe["room_id"]]
    column["center"] = list(furnishing_footprint(room, wardrobe).centroid.coords[0])
    changed["structure"].append(
        {
            **deepcopy(column),
            "id": "column-free-standing",
            "center": [2.0, 3.0],
        }
    )
    report = check_design(changed, requirements, paths.BRIEF)
    clearance = check_by_id(report, "structure:clearance")
    assert clearance["status"] == "fail"
    assert {
        (item["member_id"], item["obstacle_id"]) for item in clearance["evidence"]["collisions"]
    } >= {(column["id"], wardrobe["id"])}
    assert check_by_id(report, "structure:free-standing:column-free-standing")["status"] == (
        "review"
    )


def test_structure_clearance_checks_upturned_beams_in_the_storey_above(
    design, requirements, check_by_id
):
    changed = deepcopy(design)
    walls = {wall["id"]: wall for wall in changed["walls"]}
    upper = next(level for level in changed["levels"] if level["id"] == "U")

    def door_midpoint(door):
        (x0, y0), (x1, y1) = walls[door["wall_id"]]["start"], walls[door["wall_id"]]["end"]
        length = math.dist((x0, y0), (x1, y1))
        t = (door["offset"] + door["width"] / 2) / length
        return Point(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    beam, door = next(
        (beam, door)
        for door in changed["openings"]
        if door["kind"] == "door" and walls[door["wall_id"]]["level_id"] == "U"
        for beam in changed["structure"]
        if beam["kind"] == "beam"
        and beam["level_id"] == "G"
        and LineString([beam["start"], beam["end"]])
        .buffer(beam["width_m"] / 2, cap_style="flat")
        .contains(door_midpoint(door))
    )
    assert beam["top_z_m"] <= upper["elevation_m"] + upper["floor_top_offset_m"]
    beam["top_z_m"] = upper["elevation_m"] + 0.3  # Upturned into the upper doorway.
    clearance = check_by_id(check_design(changed, requirements, paths.BRIEF), "structure:clearance")
    assert clearance["status"] == "fail"
    assert (beam["id"], door["id"]) in {
        (item["member_id"], item["obstacle_id"]) for item in clearance["evidence"]["collisions"]
    }


def test_required_equipment_fails_without_any_furnishings(design, requirements, check_by_id):
    changed = deepcopy(design)
    changed["furnishings"] = []
    report = check_design(changed, requirements, paths.BRIEF)
    for rule in requirements["required_equipment"]:
        assert check_by_id(report, f"equipment:{rule['requirement_id']}")["status"] == "fail"
    assert report["summary"]["decision"] == "reject"
