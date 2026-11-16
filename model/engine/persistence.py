"""Stdlib-only persistence helpers shared across ``model/engine`` modules.

Every function here uses only the Python standard library (``hashlib``, ``json``,
``os``, ``re``, ``tempfile``, ``datetime``, ``pathlib``, ``typing``), so this module stays
importable inside Blender's bundled Python interpreter, which has no third-party
packages installed.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_COPY_SUFFIX = re.compile(r"\.\d{3}$")


def strip_copy_suffix(name: str) -> str:
    """Strip Blender's numeric collision suffix (for example ``.001``) from *name*."""

    return _COPY_SUFFIX.sub("", name)


def normalize_json(value: Any) -> Any:
    """Recursively canonicalize *value* for deterministic JSON fingerprinting."""

    if isinstance(value, Mapping):
        return {str(key): normalize_json(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [normalize_json(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("fingerprinted values must contain only finite numbers")
        return 0.0 if value == 0 else value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"cannot fingerprint value of type {type(value).__name__}")


def stable_hash(value: Any) -> str:
    """Return the SHA-256 of normalized, canonical UTF-8 JSON."""

    return transport_hash(normalize_json(value))


def evidence_fingerprint(vertices_world: Any, faces: Any) -> str:
    """Fingerprint one exported mesh so audits reject stale or edited evidence."""

    return stable_hash({"vertices_world": vertices_world, "faces": faces})


def transport_hash(value: Any) -> str:
    """Return the SHA-256 of canonical UTF-8 JSON without normalizing *value* first."""

    encoded = json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at *path*."""

    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path: Path) -> Any:
    """Parse the UTF-8 JSON document at *path*."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_write_json(path: Path, value: Any) -> None:
    """Write *value* as indented JSON to *path*, replacing it atomically."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(UTC).isoformat()
