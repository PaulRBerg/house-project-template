"""Check the retained render layout: one current set, at most one flat previous set, PNG images only.

Run through `just render-check`. It exits non-zero and lists every violation.
"""

from __future__ import annotations

import sys
from pathlib import Path

from engine.paths import CYCLES_RENDERS, RENDERS
from engine.render_inventory import RENDER_CATEGORIES

RENDER_SETS = ("current", "previous")
CATEGORIES = frozenset(RENDER_CATEGORIES)
IGNORED_NAMES = frozenset({".DS_Store"})


def _entries(directory: Path) -> list[Path]:
    return sorted(entry for entry in directory.iterdir() if entry.name not in IGNORED_NAMES)


def _check_set(root: Path) -> list[str]:
    """A set holds only category folders of PNG files plus its JSON receipts."""
    problems = []
    for entry in _entries(root):
        if entry.is_dir() and entry.name in CATEGORIES:
            for image in _entries(entry):
                if image.is_dir() or image.suffix.lower() != ".png":
                    problems.append(f"{image}: only PNG files belong in a category folder")
        elif entry.is_dir():
            problems.append(
                f"{entry}: unexpected folder; use only {', '.join(sorted(CATEGORIES))} "
                "(no timestamped, 2d or 3d subfolders)"
            )
        elif entry.suffix != ".json":
            problems.append(f"{entry}: only category folders and JSON receipts belong in a set")
    return problems


def check_render_layout(renders: Path = RENDERS, cycles: Path = CYCLES_RENDERS) -> list[str]:
    """Return every violation of the render retention layout."""
    problems = []
    if renders.exists():
        for entry in _entries(renders):
            if entry.name not in RENDER_SETS or not entry.is_dir() or entry.is_symlink():
                problems.append(
                    f"{entry}: `renders/` holds only the `current/` and `previous/` folders "
                    "(keep one previous set, directly in `previous/`)"
                )
        for name in RENDER_SETS:
            if (renders / name).is_dir() and not (renders / name).is_symlink():
                problems.extend(_check_set(renders / name))
    if cycles.exists():
        problems.extend(_check_set(cycles))
    return problems


def main() -> int:
    problems = check_render_layout()
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print("Render layout OK: current/, one flat previous/ set and the flat Cycles set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
