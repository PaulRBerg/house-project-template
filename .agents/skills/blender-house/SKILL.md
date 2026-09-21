---
name: blender-house
description: Inspect, edit, render, or maintain a repository's canonical Blender house model with guarded save, reopen, and verification evidence.
---

# Blender house

Use this skill for work on `model/house.blend`, its maintained builder, or its renders.

Use `$house-brief` first whenever geometry may express, interpret, or change a household requirement. The brief is
the semantic authority; the model is a coordinated design artifact. Do not infer accepted requirements from demo
geometry.

Read the repository instructions and `model/AGENTS.md`. Establish the live Blender instance, resolved open file,
dirty state, and known on-disk hash before mutation. Coordinate one live owner. Refuse an unexpected path, dirty file,
or hash mismatch.

Use Blender Lab's official MCP tools for scene facts and maintained-script execution. Use native UI interaction for
add-on setup, visual inspection, and recovery when available; otherwise use official MCP screenshots. Do not use the
Python Console or clipboard injection for routine work. Do not invoke Blender directly from a shell.

Keep model changes in maintained repository sources. Save explicitly, reopen the canonical blend, and validate the
reopened snapshot: path, clean state, metric units, expected geometry and area, object inventory, source hash, linked
libraries, and external assets. Inspect a current render for visual work.

After any timeout, inspect state and outputs before another mutation. Never replay an uncertain operation. Put
replaceable images under `model/renders/` and machine-readable evidence under `model/.generated/`.
