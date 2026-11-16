from pathlib import Path

import pytest

from engine.render_layout import check_render_layout


def _set(root: Path) -> None:
    for category in ("plans", "exteriors", "interiors"):
        (root / category).mkdir(parents=True)
        (root / category / "Vedere.png").write_bytes(b"")
    (root / "final-log.json").write_text("{}")


@pytest.fixture
def layout(tmp_path: Path) -> tuple[Path, Path]:
    renders, cycles = tmp_path / "renders", tmp_path / "renders-cycles"
    _set(renders / "current")
    _set(renders / "previous")
    _set(cycles)
    return renders, cycles


def test_accepts_current_one_flat_previous_and_flat_cycles(layout):
    assert check_render_layout(*layout) == []


@pytest.mark.parametrize(
    "extra",
    [
        "previous/2026-10-07T12-00-00/plans",
        "previous/previous",
        "current/plans/2d",
        "older",
    ],
)
def test_rejects_extra_generations_and_nested_folders(layout, extra):
    renders, cycles = layout
    (renders / extra).mkdir(parents=True)
    assert check_render_layout(renders, cycles)


def test_rejects_svg_plans_and_rotated_cycles(layout):
    renders, cycles = layout
    (renders / "previous/plans/Plan arhitectural parter.svg").write_text("")
    (cycles / "previous").mkdir()
    problems = check_render_layout(renders, cycles)
    assert len(problems) == 2
