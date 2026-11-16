"""Render the maintained parcel queue from a clean saved model."""

import bpy
from parcel_render_output import prepare_cycles, prepare_outputs
from project_paths import BLEND, DESIGN, RENDER_CANCEL, completion_name, load_engine_modules

task_context = globals().get("BLENDER_TASK_CONTEXT")
if not isinstance(task_context, dict) or not task_context.get("run_id"):
    raise RuntimeError("Start renders through start_render() for run-specific completion")


persistence, inventory, rendering = load_engine_modules(
    "persistence", "render_inventory", "rendering"
)
style = persistence.read_json(DESIGN / "style.json")
jobs = inventory.render_views(style)
sun = inventory.sun_rotations(style)
preview = globals().get("PARCEL_PREVIEW", False)
engine = globals().get("PARCEL_ENGINE", "eevee")
selected = globals().get("PARCEL_VIEWS")
if selected is not None:
    unknown = set(selected) - {job["stem"] for job in jobs}
    if unknown or not selected:
        raise ValueError(f"Choose existing, nonempty render stems; unknown: {unknown}")
    jobs = [job for job in jobs if job["stem"] in selected]
elif preview:
    jobs = jobs[:4]
# Resolve every requested scene/camera before archiving the previous output set.
for job in jobs:
    bpy.data.scenes[job["scene"]].objects[job["camera"]]
# The runner's preflight hashed the clean saved blend this queue renders.
blend_sha256 = task_context["blend_sha256"]
run_dir = prepare_cycles() if engine == "cycles" else prepare_outputs("renders", blend_sha256)
mode = "preview" if preview else "final"
log = run_dir / f"{mode}-log.json"
completion = run_dir / completion_name(mode)
completion.unlink(missing_ok=True)
receipt = {
    "run_id": task_context["run_id"],
    "started_at": persistence.utc_now(),
    "blend": str(BLEND),
    "blend_sha256": blend_sha256,
    "engine": engine,
    "mode": mode,
    "blender_version": bpy.app.version_string,
    "expected_views": [job["stem"] for job in jobs],
    "images": [],
    "status": "running",
}
persistence.atomic_write_json(log, receipt)
quality = inventory.QUALITY_PROFILES[engine][mode]
try:
    for job in jobs:
        # Blender cannot abort a blocking render from Python, so cancellation lands between views.
        if RENDER_CANCEL.exists():
            RENDER_CANCEL.unlink()
            receipt.update(status="cancelled", cancelled_at=persistence.utc_now())
            break
        target = run_dir / job["category"] / job["filename"]
        rendered = rendering.render_view_image(
            bpy, view=job, quality=quality, output_path=target, sun=sun
        )
        receipt["images"].append(
            {
                "path": str(target),
                "sha256": persistence.sha256_file(target),
                "scene": job["scene"],
                "camera": job["camera"],
                "category": job["category"],
                "seconds": rendered["seconds"],
                **rendered["settings"],
            }
        )
        persistence.atomic_write_json(log, receipt)
except Exception as exc:
    receipt.update(status="failed", error=str(exc))
    persistence.atomic_write_json(log, receipt)
    raise
if receipt["status"] == "cancelled":
    persistence.atomic_write_json(log, receipt)
    task_context["cancelled_outputs"] = [image["path"] for image in receipt["images"]]
    print("PARCEL RENDERS CANCELLED", len(receipt["images"]), str(run_dir))
else:
    receipt.update(status="complete", completed_at=persistence.utc_now())
    persistence.atomic_write_json(log, receipt)
    persistence.atomic_write_json(completion, receipt)
    print("PARCEL RENDERS COMPLETE", len(receipt["images"]), str(run_dir))
