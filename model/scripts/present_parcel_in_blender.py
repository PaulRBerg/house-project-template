"""Set up the interactive Layout presentation without saving the blend."""

import bpy
from project_paths import DESIGN, load_engine_modules

persistence, presentation, render_inventory = load_engine_modules(
    "persistence", "presentation", "render_inventory"
)
window = bpy.context.window
if window is None:
    raise RuntimeError("Presentation requires an interactive Blender window")
view = render_inventory.default_view(persistence.read_json(DESIGN / "style.json"))
window.scene = bpy.data.scenes[view["scene"]]
window.scene.camera = bpy.data.objects[view["camera"]]
window.scene.camera.data.show_passepartout = True
window.scene.camera.data.passepartout_alpha = 1
window.workspace = bpy.data.workspaces["Layout"]

with bpy.context.temp_override(window=window):
    # Bonsai can activate BIM on file load. Keep both workspaces presentable.
    screens = {window.screen}
    if "BIM" in bpy.data.workspaces:
        screens.update(bpy.data.workspaces["BIM"].screens)
    areas = [area for screen in screens for area in screen.areas]
    for area in areas:
        if area.type == "CONSOLE":
            area.type = "VIEW_3D"
        elif area.type == "VIEW_3D" and area.height < 180:
            area.type = "DOPESHEET_EDITOR"
            area.ui_type = "TIMELINE"
    for area in areas:
        if area.type == "VIEW_3D":
            space = next(space for space in area.spaces if space.type == "VIEW_3D")
            presentation.configure_camera_viewport(space)
            space.region_3d.view_camera_zoom = 20
            space.shading.type = "MATERIAL"
        elif area.type == "PROPERTIES":
            area.spaces.active.context = "RENDER"
print("PARCEL PRESENTATION READY (not saved)")
