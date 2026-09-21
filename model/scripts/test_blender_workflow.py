"""Pure-Python checks for the guarded Blender workflow."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


builder = load("demo_builder_under_test", "build_demo_house.py")
workflow = load("blender_workflow_under_test", "blender_workflow.py")


class FacadeGeometryTests(unittest.TestCase):
    def test_door_and_window_voids_are_not_filled(self) -> None:
        openings = (
            builder.Opening(-2.5, -1.5, 0.0, 2.2),
            builder.Opening(0.5, 2.0, 0.8, 2.0),
        )
        sections = builder.facade_sections(8.0, 2.8, openings)

        for center, width, center_z, height in sections:
            x_range = (center - width / 2, center + width / 2)
            z_range = (center_z - height / 2, center_z + height / 2)
            for opening in openings:
                overlap_x = min(x_range[1], opening.end) - max(x_range[0], opening.start)
                overlap_z = min(z_range[1], opening.top) - max(z_range[0], opening.bottom)
                self.assertFalse(overlap_x > 1e-9 and overlap_z > 1e-9)

    def test_rejects_overlapping_openings(self) -> None:
        with self.assertRaises(ValueError):
            builder.facade_sections(
                8.0,
                2.8,
                (
                    builder.Opening(-2.0, 0.5, 0.0, 2.0),
                    builder.Opening(0.0, 1.0, 0.8, 2.0),
                ),
            )


class WorkflowGuardTests(unittest.TestCase):
    def test_noncanonical_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(RuntimeError):
            workflow.canonical_target(Path(directory) / "house.blend")

    def test_known_hash_guard_accepts_only_exact_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.blend"
            path.write_bytes(b"known snapshot")
            known = workflow.sha256_file(path)
            workflow.assert_expected_file(path, known)
            path.write_bytes(b"changed snapshot")
            with self.assertRaises(RuntimeError):
                workflow.assert_expected_file(path, known)

    def test_expected_inventory_is_minimal_and_stable(self) -> None:
        self.assertEqual(len(workflow.EXPECTED_OBJECTS), 15)
        self.assertEqual(
            {name for name in workflow.EXPECTED_OBJECTS if name.startswith("Wall.")},
            {"Wall.Front", "Wall.Back", "Wall.East", "Wall.West"},
        )


if __name__ == "__main__":
    unittest.main()
