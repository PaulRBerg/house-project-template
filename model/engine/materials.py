"""Material and world descriptors with in-place Blender parameter updates."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import paths
from .persistence import transport_hash
from .surface_materials import apply_surface

# Editable scalar Principled BSDF inputs keyed by their style.json parameter names.
PRINCIPLED_SCALAR_SOCKETS = {
    "roughness": "Roughness",
    "metallic": "Metallic",
    "ior": "IOR",
    "transmission_weight": "Transmission Weight",
    "coat_roughness": "Coat Roughness",
    "alpha": "Alpha",
}
# Every editable non-colour input keyed by parameter name; ``color`` maps to a
# role-dependent socket and is resolved per material.
SCALAR_SOCKETS = {
    **PRINCIPLED_SCALAR_SOCKETS,
    "strength": "Strength",
    "emission_color": "Emission Color",
    "emission_strength": "Emission Strength",
}
EDITABLE_PARAMETERS = ("color", *SCALAR_SOCKETS)
# EEVEE world sun extraction for an HDRI ``environment`` without its own ``sun``: Blender
# 5.2 defaults (``World.sun_threshold``, ``sun_shadow_maximum_resolution``) and the real
# sun's 0.526 degree angular diameter for ``World.sun_angle``.
ENVIRONMENT_SUN_DEFAULTS = {"threshold": 10.0, "angle_deg": 0.526, "shadow_resolution_m": 0.001}
# HDR radiance maps carry scene-linear Rec.709 values.
ENVIRONMENT_COLORSPACE = "Linear Rec.709"


class MaterialError(ValueError):
    pass


def compile_materials(
    design: Mapping[str, Any],
    compiled: Mapping[str, Any] | None = None,
    *,
    source_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile material intent without flattening captured native shaders.

    Catalog color and roughness values are useful viewport metadata, but they do
    not describe every linked node in the captured Blender datablocks.  Runtime
    overrides therefore include only fields changed from the immutable native
    library defaults captured in the asset manifest.
    """

    components = {item["id"]: item for item in (compiled or {}).get("components", [])}
    source_materials = {item["name"]: item for item in (source_manifest or {}).get("materials", [])}
    source_worlds = {item["name"]: item for item in (source_manifest or {}).get("worlds", [])}
    descriptors = []
    for source in sorted(design.get("materials", []), key=lambda item: item["id"]):
        item = dict(source)
        color = item.get("color")
        if not isinstance(color, Sequence) or len(color) not in (3, 4):
            raise MaterialError(f"{item['id']}.color must have three or four values")
        color = [float(value) for value in color]
        if len(color) == 3:
            color.append(1.0)
        if any(not math.isfinite(value) or value < 0 for value in color):
            raise MaterialError(f"{item['id']}.color values must be finite and nonnegative")
        role = item.get("role", "material")
        if role not in {"material", "world"}:
            raise MaterialError(f"{item['id']}: unsupported role {role!r}")
        environment = item.get("environment")
        if environment is not None and (
            role != "world" or not isinstance(environment.get("map"), str)
        ):
            raise MaterialError(f"{item['id']}.environment needs a world role and a map path")
        descriptor = {
            **item,
            "color": color,
            "component_id": item["id"],
            "dependency_fingerprint": components.get(item["id"], {}).get(
                "fingerprint", transport_hash(item)
            ),
        }
        source_record = (source_worlds if role == "world" else source_materials).get(
            item.get("source_name", ""), {}
        )
        shader = (
            source_record.get("background" if role == "world" else "principled")
            or source_record.get("emission")
            or {}
        )
        socket_names = {
            "color": "Color" if role == "world" or source_record.get("emission") else "Base Color",
            **SCALAR_SOCKETS,
        }
        source_parameters = {
            key: shader[socket]["value"] for key, socket in socket_names.items() if socket in shader
        }
        descriptor["source_parameters"] = source_parameters
        descriptor["parameter_overrides"] = (
            {
                key: descriptor[key]
                for key in EDITABLE_PARAMETERS
                if key in descriptor and descriptor[key] != source_parameters.get(key)
            }
            if source_record
            else {}
        )
        descriptor["parameter_fingerprint"] = transport_hash(
            {
                "source_name": item.get("source_name"),
                "role": role,
                "source_parameters": source_parameters,
                "parameters": {
                    key: descriptor[key] for key in EDITABLE_PARAMETERS if key in descriptor
                },
                "overrides": descriptor["parameter_overrides"],
                "surface_render_method": descriptor.get("surface_render_method"),
                "surface": descriptor.get("surface"),
                "environment": environment,
            }
        )
        descriptors.append(descriptor)
    return {
        "generator": {"id": "engine.materials", "version": "1.2.0"},
        "materials": descriptors,
        "fingerprint": transport_hash(descriptors),
    }


def _append_datablock(bpy: Any, library: Path, kind: str, source_name: str) -> Any | None:
    with bpy.data.libraries.load(str(library), link=False) as (available, loaded):
        available_names = getattr(available, kind)
        if source_name not in available_names:
            return None
        setattr(loaded, kind, [source_name])
    values = getattr(loaded, kind)
    return values[0] if values else None


def _apply_environment(bpy: Any, world: Any, item: Mapping[str, Any]) -> None:
    """Rebuild an HDRI world tree and configure EEVEE's extraction of its sun."""
    environment = item["environment"]
    tree = world.node_tree
    tree.nodes.clear()
    coordinates = tree.nodes.new("ShaderNodeTexCoord")
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (
        0.0,
        0.0,
        math.radians(float(environment.get("rotation_deg", 0.0))),
    )
    texture = tree.nodes.new("ShaderNodeTexEnvironment")
    path = str(paths.ASSETS / environment["map"])
    texture.image = bpy.data.images.load(path, check_existing=True)
    texture.image.filepath = bpy.path.relpath(path)
    texture.image.colorspace_settings.name = ENVIRONMENT_COLORSPACE
    background = tree.nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = float(item.get("strength", 1.0))
    output = tree.nodes.new("ShaderNodeOutputWorld")
    tree.links.new(coordinates.outputs["Generated"], mapping.inputs["Vector"])
    tree.links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
    tree.links.new(texture.outputs["Color"], background.inputs["Color"])
    tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    sun = {**ENVIRONMENT_SUN_DEFAULTS, **environment.get("sun", {})}
    world.use_sun_shadow = True
    world.sun_threshold = float(sun["threshold"])
    world.sun_angle = math.radians(float(sun["angle_deg"]))
    world.sun_shadow_maximum_resolution = float(sun["shadow_resolution_m"])


def apply_materials(
    bpy: Any,
    descriptors: Sequence[Mapping[str, Any]],
    *,
    library_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create/append datablocks once, then update parameters without touching meshes."""
    library = Path(library_path).resolve() if library_path else None
    result: dict[str, Any] = {}
    derived: dict[str, list[Any]] = {}
    for candidate in bpy.data.materials:
        source_id = candidate.get("procedural_source_material_id")
        if source_id:
            derived.setdefault(source_id, []).append(candidate)
    for item in descriptors:
        role = item.get("role", "material")
        owner = bpy.data.worlds if role == "world" else bpy.data.materials
        datablock = owner.get(item["id"])
        appended = False
        if datablock is None and library and item.get("source_name"):
            datablock = _append_datablock(
                bpy,
                library,
                "worlds" if role == "world" else "materials",
                item["source_name"],
            )
            appended = datablock is not None
        if datablock is None:
            datablock = owner.new(item["id"])
        datablock.name = item["id"]
        datablock["source_name"] = item.get("source_name", "")
        targets = [datablock]
        if role == "material":
            targets.extend(
                candidate for candidate in derived.get(item["id"], ()) if candidate != datablock
            )
        overrides = dict(item.get("parameter_overrides", {}))
        if not appended and not datablock.get("procedural_native_source"):
            overrides = {key: item[key] for key in EDITABLE_PARAMETERS if key in item}
        for target in targets:
            target.use_nodes = True
            if "surface" in item:
                apply_surface(bpy, target, item)
            if role == "material" and "surface_render_method" in item:
                target.surface_render_method = item["surface_render_method"]
            color = tuple(item["color"])
            if role == "material" and "color" in overrides:
                target.diffuse_color = color
            nodes = target.node_tree.nodes
            if "environment" in item:
                _apply_environment(bpy, target, item)
                shader = None
            elif role == "world":
                shader = nodes.get("Background")
            else:
                shader = next(
                    (node for node in nodes if node.type in {"BSDF_PRINCIPLED", "EMISSION"}),
                    None,
                )
            if shader is not None:
                if role == "world":
                    if "color" in overrides and not shader.inputs["Color"].is_linked:
                        shader.inputs["Color"].default_value = color
                    if "strength" in overrides:
                        shader.inputs["Strength"].default_value = float(overrides["strength"])
                elif shader.type == "BSDF_PRINCIPLED":
                    if "color" in overrides and not shader.inputs["Base Color"].is_linked:
                        shader.inputs["Base Color"].default_value = color
                    for key, socket in PRINCIPLED_SCALAR_SOCKETS.items():
                        if key in overrides and socket in shader.inputs:
                            shader.inputs[socket].default_value = float(overrides[key])
                    if "emission_color" in overrides:
                        shader.inputs["Emission Color"].default_value = tuple(
                            overrides["emission_color"]
                        )
                    if "emission_strength" in overrides:
                        shader.inputs["Emission Strength"].default_value = float(
                            overrides["emission_strength"]
                        )
                elif shader.type == "EMISSION":
                    if "color" in overrides and not shader.inputs["Color"].is_linked:
                        shader.inputs["Color"].default_value = color
                    if "strength" in overrides:
                        shader.inputs["Strength"].default_value = float(overrides["strength"])
            target["procedural_source_material_id"] = item["id"]
            target["parameter_fingerprint"] = item["parameter_fingerprint"]
        datablock["procedural_id"] = item["id"]
        if appended:
            datablock["procedural_native_source"] = True
        result[item["id"]] = datablock
    return result
