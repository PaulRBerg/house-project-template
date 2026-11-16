"""Host-side compilation of the runtime bundle that Blender applies natively."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import paths
from .architecture import compile_architecture
from .assets import read_catalog
from .blender_runtime import FORMAT_VERSION, runtime_fingerprint
from .compiler import compile_design
from .design_package import load_design
from .furnishings import compile_furnishings
from .materials import compile_materials
from .persistence import read_json, stable_hash
from .persistence import sha256_file as _sha256
from .presentation import compile_presentation
from .requirements import load_requirements
from .site_components import compile_site_components

GENERATOR_ID = "engine.runtime_bundle"
GENERATOR_VERSION = "1.0.0"


def _file_hashes(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): _sha256(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
        and not path.is_symlink()
        and "__pycache__" not in path.relative_to(directory).parts
        and paths.GENERATED.name not in path.relative_to(directory).parts
        and path.suffix != ".pyc"
        and path.name not in paths.USER_OWNED_FILES
    }


def _descriptor_map(bundle: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for domain in ("architecture", "furnishings", "site_components"):
        generated = bundle.get(domain, {})
        for collection in ("meshes", "placements", "lights"):
            for descriptor in generated.get(collection, []):
                result[descriptor["id"]] = descriptor
    return result


def compare_runtime_bundles(
    previous: Mapping[str, Any] | None, current: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify a build without treating shader parameters as mesh geometry."""

    if previous is None:
        return {
            "mode": "fresh",
            "added": sorted(_descriptor_map(current)),
            "changed": [],
            "removed": [],
            "material_ids": sorted(item["id"] for item in current["materials"]["materials"]),
            "presentation_changed": True,
        }
    old = _descriptor_map(previous)
    new = _descriptor_map(current)
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(
        identifier
        for identifier in old.keys() & new.keys()
        if old[identifier]["geometry_fingerprint"] != new[identifier]["geometry_fingerprint"]
    )
    old_materials = {
        item["id"]: item["parameter_fingerprint"] for item in previous["materials"]["materials"]
    }
    new_materials = {
        item["id"]: item["parameter_fingerprint"] for item in current["materials"]["materials"]
    }
    material_ids = sorted(
        identifier
        for identifier in old_materials.keys() | new_materials.keys()
        if old_materials.get(identifier) != new_materials.get(identifier)
    )
    presentation_changed = (
        previous["presentation"]["fingerprint"] != current["presentation"]["fingerprint"]
    )
    binding_changed = stable_hash(
        {identifier: descriptor.get("material_binding") for identifier, descriptor in old.items()}
    ) != stable_hash(
        {identifier: descriptor.get("material_binding") for identifier, descriptor in new.items()}
    )
    if previous.get("runtime_fingerprint") == current.get("runtime_fingerprint"):
        mode = "noop"
    elif not (added or removed or changed or presentation_changed) and (
        material_ids or binding_changed
    ):
        mode = "material-only"
    else:
        mode = "incremental"
    return {
        "mode": mode,
        "added": added,
        "changed": changed,
        "removed": removed,
        "material_ids": material_ids,
        "material_bindings_changed": binding_changed,
        "presentation_changed": presentation_changed,
    }


def compile_runtime_bundle(
    *,
    previous: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile all generator domains from the model's versioned sources."""

    design = load_design(paths.DESIGN)
    assets = read_catalog(paths.ASSET_CATALOG)
    source_manifest = read_json(paths.SCENE_MANIFEST)
    requirements = load_requirements(paths.REQUIREMENTS)
    compiled = compile_design(design, asset_catalog=assets)
    architecture = compile_architecture(design, compiled)
    furnishings = compile_furnishings(design, assets, compiled)
    materials = compile_materials(design, compiled, source_manifest=source_manifest)
    site_components = compile_site_components(
        design, assets, compiled, setback_m=float(requirements["setback"]["minimum_m"])
    )
    presentation = compile_presentation(design, compiled)
    provenance = {
        "design_files": _file_hashes(paths.DESIGN),
        "engine_files": _file_hashes(paths.MODEL_DIR / "engine"),
        "asset_files": _file_hashes(paths.ASSETS),
        "script_files": _file_hashes(paths.SCRIPTS),
        "runtime_files": {
            name: _sha256(paths.MODEL_DIR / name)
            for name in ("pyproject.toml", "uv.lock")
            if (paths.MODEL_DIR / name).is_file()
        },
    }
    bundle = {
        "format_version": FORMAT_VERSION,
        "generator": {"id": GENERATOR_ID, "version": GENERATOR_VERSION},
        "design_id": design["id"],
        "source_fingerprint": compiled["source_fingerprint"],
        "compiled": compiled,
        "architecture": architecture,
        "furnishings": furnishings,
        "materials": materials,
        "site_components": site_components,
        "presentation": presentation,
        "libraries": {
            "assets": paths.ASSET_LIBRARY.relative_to(paths.MODEL_DIR).as_posix(),
        },
        "provenance": provenance,
    }
    bundle["runtime_fingerprint"] = runtime_fingerprint(bundle)
    bundle["change_set"] = compare_runtime_bundles(previous, bundle)
    return bundle


__all__ = ["compare_runtime_bundles", "compile_runtime_bundle"]


if __name__ == "__main__":
    from .persistence import atomic_write_json

    output = paths.RUNTIME_BUNDLE
    previous = read_json(output) if output.is_file() else None
    bundle = compile_runtime_bundle(previous=previous)
    atomic_write_json(output, bundle)
    print(output, bundle["change_set"]["mode"])
