"""Reconcile presentation links, then save the canonical blend."""

import bpy
from parcel_render_output import prepare_current
from project_paths import ASSET_CATALOG, BLEND, DESIGN, load_engine_modules

assets, furnishings, persistence, presentation, render_inventory = load_engine_modules(
    "assets", "furnishings", "persistence", "presentation", "render_inventory"
)
# Presentation-only reconciliation: preserve every mesh, transform and budget/brief decision.
style = persistence.read_json(DESIGN / "style.json")
placements = persistence.read_json(DESIGN / "furnishings.json")["furnishings"]
furnishings.relink_furnishings(
    bpy, placements, assets.asset_index(assets.read_catalog(ASSET_CATALOG))
)
presentation.configure_annotations(bpy)
presentation.configure_mirror_probes(bpy)
for camera in style["cameras"]:
    for definition in camera["scene_definitions"]:
        presentation.configure_scene(bpy.data.scenes[definition["name"]], definition)

view = render_inventory.default_view(style)
scene = bpy.data.scenes[view["scene"]]
for saved_scene in bpy.data.scenes:
    saved_scene.use_fake_user = True
bpy.context.window.scene = scene
scene.camera = bpy.data.objects[view["camera"]]
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            presentation.configure_camera_viewport(area.spaces.active)

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
output_hash = persistence.sha256_file(BLEND)
prepare_current(output_hash)
globals()["BLENDER_TASK_CONTEXT"]["output_blend_sha256"] = output_hash
print("PARCEL SAVED", output_hash)
