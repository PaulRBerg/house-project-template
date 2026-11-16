"""Keep the current EEVEE set and one previous generation; overwrite the flat Cycles set."""

import runpy
import shutil

from project_paths import CYCLES_RENDERS, DRAWING_GEOMETRY, DRAWINGS_COMPLETE, MODEL_DIR, RENDERS

# Load fresh names from this checkout without resetting the live engine module namespace.
_inventory = runpy.run_path(str(MODEL_DIR / "engine/render_inventory.py"))
_persistence = runpy.run_path(str(MODEL_DIR / "engine/persistence.py"))
_read_json = _persistence["read_json"]
_write_json = _persistence["atomic_write_json"]
DRAWING_FILENAMES = _inventory["DRAWING_FILENAMES"]
DRAWING_OUTPUTS = (
    *(f"plans/{name}" for name in DRAWING_FILENAMES.values()),
    DRAWINGS_COMPLETE,
    DRAWING_GEOMETRY.name,
)


def _relocate_receipts(directory, old_root, new_root):
    """Keep image links usable after moving or copying a generation."""

    def relocate(value):
        if isinstance(value, str) and value.startswith(str(old_root) + "/"):
            return str(new_root) + value[len(str(old_root)) :]
        if isinstance(value, list):
            return [relocate(entry) for entry in value]
        if isinstance(value, dict):
            return {key: relocate(entry) for key, entry in value.items()}
        return value

    # Parse every receipt before writing, so invalid JSON leaves the set untouched.
    receipts = {receipt: relocate(_read_json(receipt)) for receipt in directory.rglob("*.json")}
    for receipt, data in receipts.items():
        _write_json(receipt, data)


def _archive(current):
    """Replace the single retained previous set with the current one."""
    previous = RENDERS / "previous"
    _relocate_receipts(current, current, previous)
    if previous.exists():
        shutil.rmtree(previous)
    current.rename(previous)
    return previous


def prepare_current(blend_sha256):
    """Archive the current outputs when they came from a different saved model."""
    for directory in (RENDERS, RENDERS / "current", RENDERS / "previous"):
        if directory.is_symlink():
            raise ValueError(f"Render directory must not be a symlink: {directory}")
    RENDERS.mkdir(parents=True, exist_ok=True)
    current = RENDERS / "current"
    marker = current / "source-blend.json"
    current_hash = _read_json(marker)["blend_sha256"] if marker.exists() else None
    if (
        current.exists()
        and current_hash != blend_sha256
        and any(entry.name != "source-blend.json" for entry in current.iterdir())
    ):
        _archive(current)
    current.mkdir(parents=True, exist_ok=True)
    _write_json(marker, {"blend_sha256": blend_sha256})
    return current


def _deliverable(current, kind):
    """Files of one deliverable in a set: drawings, or every other PNG and render receipt."""
    drawings = {path for pattern in DRAWING_OUTPUTS for path in current.glob(pattern)}
    if kind == "drawings":
        return drawings
    if kind == "renders":
        receipts = [*current.glob("preview-*.json"), *current.glob("final-*.json")]
        return (set(current.glob("**/*.png")) - drawings) | set(receipts)
    raise ValueError(f"Unknown render deliverable: {kind}")


def prepare_outputs(kind, blend_sha256):
    """Archive a replaced deliverable; carry complementary same-model outputs forward."""
    if kind not in {"renders", "drawings"}:
        raise ValueError(f"Unknown render deliverable: {kind}")
    current = prepare_current(blend_sha256)
    if _deliverable(current, kind):
        archived = _archive(current)
        shutil.copytree(archived, current)
        _relocate_receipts(current, archived, current)
        # Only these newly copied working files are removed; the archive is retained.
        for target in _deliverable(current, kind):
            target.unlink()
    return current


def prepare_cycles():
    """Return the flat Cycles set; each render simply overwrites its own file."""
    if CYCLES_RENDERS.is_symlink():
        raise ValueError(f"Render directory must not be a symlink: {CYCLES_RENDERS}")
    CYCLES_RENDERS.mkdir(parents=True, exist_ok=True)
    return CYCLES_RENDERS
