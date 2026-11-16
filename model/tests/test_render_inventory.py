"""The render queue derives from style.json cameras; presentation rejects inconsistent jobs."""

from copy import deepcopy

import pytest

from engine.presentation import PresentationError, compile_presentation
from engine.render_inventory import default_view, render_views

IDENTITY = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def _camera(identifier, jobs, scenes=()):
    return {
        "id": identifier,
        "name": identifier.title(),
        "matrix": IDENTITY,
        "render_jobs": jobs,
        "scene_definitions": list(scenes),
    }


def _scene(identifier, camera_id, **fields):
    return {"id": identifier, "name": identifier.upper(), "camera_id": camera_id, **fields}


STYLE = {
    "levels": [{"id": "G"}, {"id": "U"}],
    "cameras": [
        _camera(
            "garden",
            [
                {
                    "stem": "garden",
                    "category": "exteriors",
                    "scene_id": "day",
                    "filename": "Gradina.png",
                },
                {
                    "stem": "evening",
                    "category": "exteriors",
                    "scene_id": "evening",
                    "filename": "Seara.png",
                },
            ],
            [
                _scene("day", "garden", cutaway="none"),
                _scene("evening", "garden", cutaway="none", evening=True),
            ],
        ),
        _camera(
            "ground",
            [
                {
                    "stem": "ground-cutaway",
                    "category": "plans",
                    "scene_id": "ground-section",
                    "filename": "Sectiune parter.png",
                },
                {
                    "stem": "ground-plan",
                    "category": "plans",
                    "scene_id": "ground-plan",
                    "filename": "Plan parter.png",
                },
            ],
            [
                _scene("ground-section", "ground", cutaway="section", level_id="G"),
                _scene("ground-plan", "ground", cutaway="plan", level_id="G"),
            ],
        ),
        _camera(
            "living",
            [
                {
                    "stem": "living",
                    "category": "interiors",
                    "scene_id": "day",
                    "filename": "Living.png",
                }
            ],
        ),
    ],
}


def test_views_follow_declaration_order_with_scene_flags():
    views = render_views(STYLE)
    assert [view["stem"] for view in views] == [
        "garden",
        "evening",
        "ground-cutaway",
        "ground-plan",
        "living",
    ]
    by_stem = {view["stem"]: view for view in views}
    assert by_stem["evening"]["evening"] and "floor" not in by_stem["evening"]
    assert by_stem["ground-cutaway"]["floor"] == "G" and by_stem["ground-cutaway"]["cutaway"]
    assert by_stem["ground-plan"]["floor"] == "G" and "cutaway" not in by_stem["ground-plan"]
    # A camera may render a scene another camera declares.
    living = by_stem["living"]
    assert (living["camera"], living["scene"], living["category"]) == ("Living", "DAY", "interiors")


def test_default_view_is_the_flagged_job_or_the_first():
    assert default_view(STYLE)["stem"] == "garden"
    style = deepcopy(STYLE)
    style["cameras"][2]["render_jobs"][0]["default"] = True
    assert default_view(style)["stem"] == "living"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: s["cameras"][2]["render_jobs"][0].update(scene_id="missing"), "unknown scene"),
        (lambda s: s["cameras"][2]["render_jobs"][0].update(filename="Seara.png"), "filename"),
        (lambda s: s["cameras"][2]["render_jobs"][0].update(category="drawings"), "category"),
        (lambda s: s["cameras"][1]["scene_definitions"][0].pop("level_id"), "needs a level_id"),
        (lambda s: s["cameras"][1]["scene_definitions"][1].update(level_id="B"), "level_id"),
        (lambda s: s["cameras"][1]["scene_definitions"][1].update(cutaway="ground"), "cutaway"),
        (
            lambda s: [job.update(default=True) for job in s["cameras"][0]["render_jobs"]],
            "default",
        ),
    ],
)
def test_presentation_rejects_inconsistent_render_jobs(change, message):
    assert len(compile_presentation(STYLE)["render_jobs"]) == 5
    style = deepcopy(STYLE)
    change(style)
    with pytest.raises(PresentationError, match=message):
        compile_presentation(style)
