from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from engine import paths
from engine.design_package import DesignValidationError, load_design, validate_design
from engine.persistence import read_json


@pytest.fixture(scope="module")
def house() -> dict:
    return read_json(paths.DESIGN / "house.json")


def test_validation_rejects_duplicate_ids_and_unknown_references(design: dict) -> None:
    duplicate = deepcopy(design)
    duplicate["rooms"][1]["id"] = duplicate["rooms"][0]["id"]
    with pytest.raises(DesignValidationError, match="duplicate entity id"):
        validate_design(duplicate)

    unknown = deepcopy(design)
    unknown["openings"][0]["wall_id"] = "wall-does-not-exist"
    with pytest.raises(DesignValidationError, match="unknown wall_id"):
        validate_design(unknown)


def test_validation_rejects_opening_past_wall_end(design: dict) -> None:
    invalid = deepcopy(design)
    invalid["openings"][0]["width"] = 100
    with pytest.raises(DesignValidationError, match="exceeds wall"):
        validate_design(invalid)


def test_sliding_operation_requires_two_terrace_panels_and_explicit_sense(design: dict) -> None:
    changed = deepcopy(design)
    opening = next(item for item in changed["openings"] if item["kind"] == "terrace")
    opening.update(
        operation="sliding",
        panel_count=2,
        slide_direction="toward-end",
    )
    validated = validate_design(changed)
    assert (
        next(item for item in validated["openings"] if item["id"] == opening["id"])["operation"]
        == "sliding"
    )

    missing_sense = deepcopy(changed)
    del next(item for item in missing_sense["openings"] if item["id"] == opening["id"])[
        "slide_direction"
    ]
    with pytest.raises(DesignValidationError, match="slide_direction"):
        validate_design(missing_sense)

    wrong_panel_count = deepcopy(changed)
    next(item for item in wrong_panel_count["openings"] if item["id"] == opening["id"])[
        "panel_count"
    ] = 3
    with pytest.raises(DesignValidationError, match="2 was expected"):
        validate_design(wrong_panel_count)


def _write_package(root: Path, house: dict, **supplements: dict) -> None:
    (root / "house.json").write_text(json.dumps(house), encoding="utf-8")
    for filename in ("furnishings.json", "style.json", "site.json"):
        content = supplements.get(
            filename.removesuffix(".json"), read_json(paths.DESIGN / filename)
        )
        if content is not None:
            (root / filename).write_text(json.dumps(content), encoding="utf-8")


def test_loader_merges_supported_supplements(house: dict, tmp_path: Path) -> None:
    _write_package(
        tmp_path, house, furnishings={"furnishings": [{"id": "chair-1", "room_id": "G-LIV"}]}
    )
    loaded = load_design(tmp_path)
    assert loaded["furnishings"] == [{"id": "chair-1", "room_id": "G-LIV"}]
    assert loaded["materials"] == read_json(paths.DESIGN / "style.json")["materials"]


@pytest.mark.parametrize("supplement", ["furnishings", "style", "site"])
def test_loader_requires_every_supplement(house: dict, tmp_path: Path, supplement: str) -> None:
    _write_package(tmp_path, house, **{supplement: None})
    with pytest.raises(DesignValidationError, match=f"missing design file: .*{supplement}.json"):
        load_design(tmp_path)


def test_loader_rejects_partial_supplement(house: dict, tmp_path: Path) -> None:
    root = tmp_path
    _write_package(root, house, style={"materials": []})
    with pytest.raises(DesignValidationError, match="missing lights, cameras"):
        load_design(root)


def _member(design: dict, kind: str) -> dict:
    return next(member for member in design["structure"] if member["kind"] == kind)


def test_structure_is_accepted_and_invalid_frame_members_are_rejected(design: dict) -> None:
    validated = validate_design(design)
    assert {member["kind"] for member in validated["structure"]} == {"column", "beam", "axis"}

    cases = [
        ("column", {"level_id": "X"}, "unknown level_id"),
        ("column", {"material_id": "material-missing"}, "unknown material_id"),
        ("column", {"section_m": [0.25, 0.3]}, "column section below"),
        ("beam", {"width_m": 0.18}, "beam width below"),
        ("beam", {"top_z_m": 2.0, "bottom_z_m": 2.0}, "top_z_m must exceed"),
        (
            "beam",
            {"width_m": 0.2, "bottom_z_m": 3.0, "top_z_m": 3.9, "placement": "upturned"},
            "beam width/depth below",
        ),
        ("axis", {"level_id": "G"}, "False schema"),
    ]
    for kind, changes, message in cases:
        invalid = deepcopy(design)
        _member(invalid, kind).update(changes)
        with pytest.raises(DesignValidationError, match=message):
            validate_design(invalid)

    zero_length = deepcopy(design)
    beam = _member(zero_length, "beam")
    beam["end"] = list(beam["start"])
    with pytest.raises(DesignValidationError, match="beam length must be positive"):
        validate_design(zero_length)


def test_band_beams_are_exempt_from_the_width_to_depth_ratio(design: dict) -> None:
    band = deepcopy(design)
    _member(band, "beam").update(width_m=0.2, bottom_z_m=3.0, top_z_m=3.9, placement="band")
    validate_design(band)
    deep = deepcopy(band)
    _member(deep, "beam")["placement"] = "downstand"
    with pytest.raises(DesignValidationError, match="width/depth"):
        validate_design(deep)


def test_roof_build_up_must_clear_the_minimum_above_the_deck(design: dict) -> None:
    thin = deepcopy(design)
    roof = thin["roofs"][0]
    roof["deck_z_m"] = roof["base_z_m"] - 0.1
    with pytest.raises(DesignValidationError, match="build-up"):
        validate_design(thin)


def test_wall_finish_references_must_resolve(design: dict) -> None:
    valid = deepcopy(design)
    room = next(item for item in valid["rooms"] if item["id"] == "G-HALL")
    room["wall_finish"] = {
        "material_id": "mat_plaster_white",
        "wainscot": {"material_id": "mat_oak", "height_m": 0.9},
        "accents": [
            {"wall_id": "wall-g-hall-north", "material_id": "mat_sage", "span_m": [0.5, 2.0]}
        ],
    }
    validate_design(valid)
    cases = [
        ({"material_id": "mat-missing"}, "unknown material_id"),
        ({"wainscot": {"material_id": "mat-missing", "height_m": 0.9}}, "material_id"),
        ({"accents": [{"wall_id": "wall-u-lobby-north", "material_id": "mat_sage"}]}, "level"),
        (
            {
                "accents": [
                    {"wall_id": "wall-g-hall-north", "material_id": "mat_sage", "span_m": [2, 9]}
                ]
            },
            "must increase within the wall",
        ),
        ({"paint": "white"}, "Additional properties"),
    ]
    for changes, message in cases:
        invalid = deepcopy(valid)
        next(item for item in invalid["rooms"] if item["id"] == "G-HALL")["wall_finish"].update(
            changes
        )
        with pytest.raises(DesignValidationError, match=message):
            validate_design(invalid)


def _first_with_material(value):
    if isinstance(value, dict):
        if "material_id" in value:
            return value
        value = list(value.values())
    if isinstance(value, list):
        return next(filter(None, map(_first_with_material, value)), None)
    return None


@pytest.mark.parametrize("collection", ["walls", "openings", "slabs", "roofs", "site_components"])
def test_every_material_reference_must_resolve(design: dict, collection: str) -> None:
    invalid = deepcopy(design)
    entity = _first_with_material(invalid[collection])
    entity["material_id"] = "material-typo"
    with pytest.raises(DesignValidationError, match=f"{entity['id']}: unknown material_id"):
        validate_design(invalid)


def test_exterior_finish_and_reveal_contracts_are_enforced(design: dict) -> None:
    def wall(changed: dict) -> dict:
        return next(item for item in changed["walls"] if item["id"] == "wall-g-east")

    def window(changed: dict) -> dict:
        return next(item for item in changed["openings"] if item["id"] == "window-g-liv-east")

    stone = {"material_ids": ["mat_stone_grey"], "course_heights_m": [0.09]}
    stone["length_range_m"] = [0.4, 0.9]
    cases = [
        (lambda d: wall(d)["finish"].update(style="graphite"), "style"),
        (lambda d: wall(d)["finish"].update(style="stone"), "style"),
        (lambda d: wall(d)["finish"].pop("stone"), "'stone' is a required"),
        (lambda d: wall(d)["finish"].update(style="plain", stone=stone), "should not be valid"),
        (lambda d: wall(d)["finish"].update(stone_material_id="mat_stone_grey"), "Additional"),
        (lambda d: wall(d).pop("finish"), "'finish' is a required"),
        (
            lambda d: wall(d)["finish"].update(
                style="ledgestone", stone={**stone, "material_ids": ["mat-missing"]}
            ),
            "unknown material_ids 'mat-missing'",
        ),
        (
            lambda d: window(d).update(
                reveal={"lining_material_id": "mat_dark_wood", "depth_m": wall(d)["thickness"]}
            ),
            "below the wall thickness",
        ),
        (
            lambda d: window(d).update(
                reveal={
                    "lining_material_id": "mat_dark_wood",
                    "depth_m": 0.2,
                    "surround_m": 0.1,
                }
            ),
            "surround_material_id",
        ),
        (
            lambda d: next(o for o in d["openings"] if o["id"] == "door-g-bath").update(
                reveal={"lining_material_id": "mat_dark_wood", "depth_m": 0.05}
            ),
            "needs an exterior wall",
        ),
    ]
    valid = deepcopy(design)
    wall(valid)["finish"].update(style="ledgestone", stone=stone)
    window(valid)["reveal"] = {"lining_material_id": "mat_dark_wood", "depth_m": 0.2}
    validate_design(valid)
    for change, message in cases:
        invalid = deepcopy(valid)
        change(invalid)
        with pytest.raises(DesignValidationError, match=message):
            validate_design(invalid)
