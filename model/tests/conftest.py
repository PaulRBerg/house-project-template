"""Shared fixtures for the model test suite."""

from __future__ import annotations

import importlib.util
import sys
import types
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

import pytest

from engine import paths
from engine.assets import read_catalog
from engine.design_package import load_design
from engine.requirements import check_design, load_requirements


class FakeTimers:
    """Records timer registrations made through ``bpy.app.timers``."""

    def __init__(self) -> None:
        self.callbacks: list[tuple[Callable[[], object], float]] = []

    def register(self, callback: Callable[[], object], first_interval: float) -> None:
        self.callbacks.append((callback, first_interval))


class FakeBpy:
    """A minimal double for the ``bpy`` module used by the Blender task runner."""

    def __init__(self, filepath) -> None:
        self.data = types.SimpleNamespace(filepath=str(filepath), is_dirty=False)
        self.app = types.SimpleNamespace(background=False, driver_namespace={}, timers=FakeTimers())
        self.ops = types.SimpleNamespace(ed=types.SimpleNamespace(undo_push=self._undo_push))

    @staticmethod
    def _undo_push(*, message):
        return {"FINISHED"}


@pytest.fixture
def scripts_dir() -> Path:
    """The ``model/scripts`` directory, source of the maintained Blender scripts."""

    return Path(__file__).resolve().parent.parent / "scripts"


@pytest.fixture
def load_script_module(scripts_dir, monkeypatch):
    """Factory fixture loading a ``model/scripts`` file as a standalone module.

    Scripts are not importable as a package, so each is loaded from its
    absolute path via ``importlib.util``. ``scripts_dir`` is prepended to
    ``sys.path`` so a script's own bare sibling imports (e.g.
    ``from project_paths import RENDERS``) resolve.
    """

    def _load(name: str):
        monkeypatch.syspath_prepend(str(scripts_dir))
        spec = importlib.util.spec_from_file_location(name, scripts_dir / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        # Scripts reload the engine package; keep the suite's own engine classes afterwards.
        engine_modules = {
            key: value
            for key, value in sys.modules.items()
            if key == "engine" or key.startswith("engine.")
        }
        saved_path = list(sys.path)
        try:
            spec.loader.exec_module(module)
        finally:
            for key in [key for key in sys.modules if key == "engine" or key.startswith("engine.")]:
                del sys.modules[key]
            sys.modules.update(engine_modules)
            sys.path[:] = saved_path
        return module

    return _load


@pytest.fixture
def fake_bpy():
    """Factory fixture returning a :class:`FakeBpy` double for a given blend path."""

    return FakeBpy


def _signed_volume(mesh):
    vertices = mesh["vertices"]
    volume = 0.0
    for face in mesh["faces"]:
        a = vertices[face[0]]
        for i in range(1, len(face) - 1):
            b, c = vertices[face[i]], vertices[face[i + 1]]
            volume += (
                a[0] * (b[1] * c[2] - b[2] * c[1])
                + a[1] * (b[2] * c[0] - b[0] * c[2])
                + a[2] * (b[0] * c[1] - b[1] * c[0])
            ) / 6
    return volume


@pytest.fixture
def signed_volume():
    """Signed volume of an indexed mesh; positive when every face winds outward."""

    return _signed_volume


# Session-scoped design inputs: tests that change them must deepcopy first.
@pytest.fixture(scope="session")
def design():
    return load_design(paths.DESIGN)


# A habitable void over part of the ground-floor living room. The demo house has none, but the
# engine still supports authored voids, so tests exercise them on this synthetic one.
SYNTHETIC_VOID = {
    "id": "void-test",
    "name": "Synthetic void",
    "level_id": "U",
    "room_below_id": "G-LIV",
    "polygon": {"outer": [[0.5, 0.5], [2.5, 0.5], [2.5, 2.0], [0.5, 2.0]], "holes": []},
    "cut_slab_ids": ["slab-upper", "ceiling-g"],
}


@pytest.fixture(scope="session")
def voided_design(design):
    """The design with :data:`SYNTHETIC_VOID` added; deepcopy before changing it."""
    changed = deepcopy(design)
    changed["voids"] = [deepcopy(SYNTHETIC_VOID)]
    return changed


@pytest.fixture(scope="session")
def asset_catalog():
    return read_catalog(paths.ASSET_CATALOG)


@pytest.fixture(scope="session")
def requirements():
    return load_requirements(paths.REQUIREMENTS)


@pytest.fixture(scope="session")
def prebuild_report(design, requirements):
    """The pre-build requirement report for the unchanged design."""
    return check_design(design, requirements, paths.BRIEF)


@pytest.fixture
def check_by_id():
    """Find one check in a requirement report by its ID."""

    def find(report, check_id):
        return next(check for check in report["checks"] if check["id"] == check_id)

    return find
