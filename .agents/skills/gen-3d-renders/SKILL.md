---
name: gen-3d-renders
description: Create coherent photorealistic concept imagery from the current house brief for exterior, interior, garden, or whole-house views.
---

# Generative 3D renders

Create concept images from accepted brief records without treating them as a substitute for the saved model, design information, or professional validation.

## Before generating

1. Use `house-brief` and read the relevant records in `brief/`, especially style, rooms, site, and garden records.
2. Preserve `required` decisions, use `preferred` decisions as defaults, and leave `phased` and `deferred` matters visibly unresolved.
3. State any scene assumptions needed to make an image. Do not write those illustrative assumptions back into the brief.

## Generate and review

Use an image-generation capability only when the host provides one; `imagegen` may require an optional external installation. Build each prompt from the scene, camera, accepted visible requirements, materials, furnishing, and lighting. Keep a consistent architectural and interior language across a requested set. Inspect results for obvious conflicts and regenerate targeted views when needed.

Generated images are distinct from `model/house.blend`. Use `blender-house` when the task requires exact saved geometry, Blender rendering, or model validation. Concept imagery cannot establish dimensions, site conditions, performance, compliance, or construction readiness.

Save images and their prompts only when the user requests repository artifacts; otherwise return the generated views and their assumptions.
