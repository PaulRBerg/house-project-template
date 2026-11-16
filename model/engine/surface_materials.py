"""Reproducible, metre-scaled CC0 surface materials for the native asset browser.

Maps live under ``model/assets/`` (``exterior/`` facade and ``interior/`` finish sets)
and are box-projected from world or object coordinates, so generated meshes need
no UVs.
"""

from . import paths


def apply_surface(bpy, material, descriptor):
    surface = descriptor["surface"]
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = descriptor["color"]
    shader.inputs["Roughness"].default_value = descriptor.get("roughness", 0.65)
    tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    coords = tree.nodes.new("ShaderNodeNewGeometry")
    scale = tree.nodes.new("ShaderNodeMapping")
    scale.inputs["Scale"].default_value = surface.get("scale", [1, 1, 1])
    scale.inputs["Rotation"].default_value = surface.get("rotation", [0, 0, 0])
    scale.inputs["Location"].default_value = surface.get("location", [0, 0, 0])
    if surface.get("coordinates") == "object":
        texture_space = tree.nodes.new("ShaderNodeTexCoord")
        tree.links.new(texture_space.outputs["Object"], scale.inputs["Vector"])
    else:
        tree.links.new(coords.outputs["Position"], scale.inputs["Vector"])
    root = paths.ASSETS
    images = {}
    for channel, filename in surface.get("maps", {}).items():
        texture = tree.nodes.new("ShaderNodeTexImage")
        texture.image = bpy.data.images.load(str(root / filename), check_existing=True)
        texture.image.filepath = bpy.path.relpath(str(root / filename))
        texture.image.colorspace_settings.name = "sRGB" if channel == "color" else "Non-Color"
        texture.projection = "BOX"
        texture.projection_blend = 0.15
        tree.links.new(scale.outputs["Vector"], texture.inputs["Vector"])
        images[channel] = texture
    if "color" in images and "monochrome" in surface:
        # Keep only the map's luminance pattern (normalized by its mean ``gain``)
        # around the palette colour, so off-palette CC0 fabrics still read as texture.
        mono = surface["monochrome"]
        gray = tree.nodes.new("ShaderNodeRGBToBW")
        tree.links.new(images["color"].outputs["Color"], gray.inputs["Color"])
        spread = tree.nodes.new("ShaderNodeMapRange")
        spread.clamp = False
        spread.inputs["From Min"].default_value = 0.0
        spread.inputs["From Max"].default_value = 2.0 / mono["gain"]
        spread.inputs["To Min"].default_value = 1.0 - mono.get("contrast", 1.0)
        spread.inputs["To Max"].default_value = 1.0 + mono.get("contrast", 1.0)
        tree.links.new(gray.outputs["Val"], spread.inputs["Value"])
        tint = tree.nodes.new("ShaderNodeMixRGB")
        tint.blend_type = "MULTIPLY"
        tint.inputs[0].default_value = 1
        tint.inputs[1].default_value = descriptor["color"]
        tree.links.new(spread.outputs["Result"], tint.inputs[2])
        tree.links.new(tint.outputs[0], shader.inputs["Base Color"])
    elif "color" in images:
        tint = tree.nodes.new("ShaderNodeMixRGB")
        tint.blend_type = "MULTIPLY"
        tint.inputs[0].default_value = 1
        tint.inputs[2].default_value = surface.get("tint", [1, 1, 1, 1])
        tree.links.new(images["color"].outputs["Color"], tint.inputs[1])
        tree.links.new(tint.outputs[0], shader.inputs["Base Color"])
    if "roughness" in images:
        tree.links.new(images["roughness"].outputs["Color"], shader.inputs["Roughness"])
    if "sheen" in surface:
        shader.inputs["Sheen Weight"].default_value = surface["sheen"]
        shader.inputs["Sheen Roughness"].default_value = 0.6
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = surface.get("bump_strength", 0.3)
    bump.inputs["Distance"].default_value = surface.get("relief_m", 0.002)
    if "height" in images:
        tree.links.new(images["height"].outputs["Color"], bump.inputs["Height"])
    elif "seams" in surface:
        bump.inputs["Strength"].default_value = 1
        _standing_seams(tree, coords, shader, bump, descriptor)
    else:
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 120
        tree.links.new(scale.outputs["Vector"], noise.inputs["Vector"])
        tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    material.asset_mark()
    material.asset_data.description = surface.get("description", "Concept surface")
    material["Asset source"] = surface.get("source", "Project-authored plaster")
    material["Asset license"] = "CC0-1.0" if images else "Project material"


def _math(tree, operation, *inputs):
    node = tree.nodes.new("ShaderNodeMath")
    node.operation = operation
    for index, value in enumerate(inputs):
        if isinstance(value, (int, float)):
            node.inputs[index].default_value = value
        else:
            tree.links.new(value, node.inputs[index])
    return node.outputs[0]


def _standing_seams(tree, coords, shader, bump, descriptor):
    """World-aligned double-lock seams on up-facing faces, with slight per-pan tone drift."""
    seams = descriptor["surface"]["seams"]
    pitch = seams["pitch_m"]
    axes = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(coords.outputs["Position"], axes.inputs[0])
    across = axes.outputs["Y" if seams["runs_along"] == "x" else "X"]
    pans = _math(tree, "DIVIDE", across, pitch)
    offset = _math(tree, "ABSOLUTE", _math(tree, "SUBTRACT", _math(tree, "FRACT", pans), 0.5))
    rib = tree.nodes.new("ShaderNodeMapRange")
    rib.interpolation_type = "SMOOTHSTEP"
    rib.inputs["From Min"].default_value = 0.5 - seams["rib_width_m"] / pitch
    rib.inputs["From Max"].default_value = 0.5
    tree.links.new(offset, rib.inputs["Value"])
    normals = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(coords.outputs["Normal"], normals.inputs[0])
    upward = _math(tree, "GREATER_THAN", normals.outputs["Z"], 0.5)
    height = _math(tree, "MULTIPLY", rib.outputs["Result"], upward)
    tree.links.new(height, bump.inputs["Height"])
    bump.inputs["Distance"].default_value = seams["rib_height_m"]
    variation = tree.nodes.new("ShaderNodeTexWhiteNoise")
    variation.noise_dimensions = "1D"
    tree.links.new(_math(tree, "FLOOR", pans), variation.inputs["W"])
    tone = tree.nodes.new("ShaderNodeMapRange")
    tone.inputs["To Min"].default_value = 1 - seams["tone_variation"]
    tone.inputs["To Max"].default_value = 1 + seams["tone_variation"]
    tree.links.new(variation.outputs["Value"], tone.inputs["Value"])
    tint = tree.nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[1].default_value = descriptor["color"]
    tree.links.new(tone.outputs["Result"], tint.inputs[2])
    tree.links.new(tint.outputs[0], shader.inputs["Base Color"])
    shader.inputs["Metallic"].default_value = descriptor.get("metallic", 0.0)
