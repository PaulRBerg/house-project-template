"""Read-only export of evaluated world-space geometry from the clean saved model."""

import bpy
from project_paths import ACTUAL_GEOMETRY, load_engine_modules

evidence = load_engine_modules("blender_runtime").export_evaluated_geometry(
    bpy, output_path=ACTUAL_GEOMETRY
)
print("Exported evaluated parcel geometry:", len(evidence["objects"]), "objects")
