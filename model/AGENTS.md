# Blender model guidance

`house.blend` is a small, generic demonstration: one 8 m × 6 m single-storey rectangular volume, four exterior
walls, a gabled roof, one door and four windows. Its 48 m² external footprint matches the repository's demo data,
but the model is illustrative and unaccepted. It is not a buildable design, a site layout, or an authority for
requirements. Use the brief for accepted decisions and reconcile any accepted geometry change with the brief and
budget.

The scene is self-contained. It has no parcel, surveyed coordinates, setback claim, linked library, downloaded
texture, furnishing, or household-specific room topology. Generated evidence belongs in `.generated/`; replaceable
images belong in `renders/`.

## Maintained sources

- `scripts/build_demo_house.py` deterministically builds the complete scene from an empty Blender file.
- `scripts/blender_workflow.py` guards creation, rebuilding, saving, reopening, and verification.
- `scripts/test_blender_workflow.py` checks the path/hash guards and facade opening geometry without starting Blender.

Do not make lasting geometry changes only in the Blender UI. Update the builder and call `rebuild_demo` against a
known clean saved hash; this entry point rebuilds and saves the canonical file. Then call `reopen_and_verify`.
Keep the builder source hash stored in the scene current. For exploration, use Numpad 0 to view the saved camera and
F12 to render it.

## Blender connection

Use Blender Lab's official MCP server for scene facts and maintained-script execution. Use native UI interaction for
add-on installation, visual inspection, and recovery when available. Use MCP screenshots when native computer use is
not available. Do not use routine Python Console or clipboard injection.

The repository pins Blender Lab `blender_mcp` at commit
`2cea8d566dde07fbac28a61d698909d69724e853` in `.mcp.json` and `.codex/config.toml`. Install the add-on from that
same source in Blender 5.1 or later through Blender's native UI. The sample was saved and validated in Blender 5.2;
5.1 has not been separately tested. The add-on and server communicate only through
`127.0.0.1:9876`. Configure the Blender executable on the host when the background tools require it; never commit an
absolute `BLENDER_PATH`.

Before any mutation, establish exclusive ownership of the live Blender instance and verify the resolved open-file
path, clean state, and the expected on-disk SHA-256. For a first build, also prove any currently open source file is
clean and unchanged before opening a factory-startup empty scene with
`read_homefile(use_empty=True, use_factory_startup=True)`. For a rebuild, require the canonical blend itself to be
open, clean, and equal to the supplied hash. A timeout makes the outcome uncertain: inspect the live file, dirty
state, object inventory, output and any receipt before deciding whether a retry is safe. Never replay an uncertain
mutation.

Open this checkout's `model/house.blend` and verify its resolved path first. Run maintained functions through official
MCP in a fresh namespace. Derive the scripts from that verified file, because Blender's working directory need not
be the repository. A typical verification call is:

```python
from pathlib import Path
import runpy
import bpy

scripts = Path(bpy.data.filepath).resolve().parent / "scripts"
workflow = runpy.run_path(str(scripts / "blender_workflow.py"))
result = workflow["verify_current"](
    str(scripts.parent / "house.blend"),
    "<known 64-character SHA-256>",
)
```

After `rebuild_demo` saves a geometry change, call `reopen_and_verify`, then independently inspect the saved snapshot.
Verification must cover the resolved path, saved and clean state, metric units, 48 m² footprint metadata, exact
object inventory, builder source hash, linked libraries, and external file assets. Inspect a current render rather
than treating a successful render command as visual proof.

Run the workflow checks from the repository root with:

```sh
just --justfile budget/justfile blender-workflow-tests
```
