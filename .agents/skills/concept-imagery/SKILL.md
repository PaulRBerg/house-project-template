---
name: concept-imagery
skill-dependencies: [household-brief, openai/codex#imagegen]
description:
  Generate photorealistic house concept images directly from the household brief with an image model, not the
  Blender model. Use for exterior, interior, garden, or whole-house visualizations.
---

# Concept Imagery

Create an inviting, coherent vision of the household's house from the current written brief.

## Read the brief

- Use [household-brief](../household-brief/SKILL.md) to interpret the household decisions, then read every current
  Markdown file in the repository's [brief directory](../../../brief/).
- Take the visual direction from [Interiors](../../../brief/interiors.md), including palette, materials, detailing,
  lighting, and atmosphere. Read the room-specific requirements in
  [Rooms and Furnishings](../../../brief/rooms-and-furnishings.md) alongside it.
- Carry the recorded architecture, room relationships, garden intent, and existing assets into the scenes. Preserve
  accepted decisions outside the user's requested exploration. Label proposed departures explicitly. If the user requests
  a stage view, include only results complete by that stage in the order `La roșu`, `La gri`, `La cheie`, `La mutat`,
  `Extra`. Otherwise, render the complete direction, including requested alternatives. Keep explicit flexibility and
  unresolved specifications visible as assumptions rather than settled facts.
- Choose plausible illustrative details where a render needs them, and identify material assumptions briefly. Keep
  these choices in the rendering task. Do not write them back into the brief.

## Compose and generate

1. Follow the user's requested views and image count. For an unspecified whole-house request, choose a compact set
   covering arrival and garden exteriors, shared living spaces, private rooms, and work. Announce the chosen
   views and visual direction, then proceed.
2. Establish one consistent house concept across the set: architectural form, facade treatment, window language,
   interior palette, joinery, and recurring furniture. Let each room express its recorded use and occupant.
3. Write a focused prompt for each view. Include the subject, camera composition, relevant visible brief requirements,
   materials, furnishings, and lighting. Translate records into concrete scene descriptions. The image generator
   cannot read repository paths or record IDs. Choose broad, room or detail framing to answer the task's question.
   A detail study is optional. Bound everyday objects to the recorded room use and what the camera shows.
4. Aim for editorial architectural photography: elegant proportions, believable scale, tactile surfaces, purposeful
   light and shadow, and composed everyday life. Express quality through comfort, craftsmanship, and material detail
   consistent with the brief. Use natural perspective, sharp architectural focus and straight verticals to make the
   space easy to understand.
5. Use the `imagegen` skill and its built-in image-generation tool to produce the actual images directly from these
   prompts. This is separate from the canonical Blender model: use `blender-model` when the request needs exact
   modeled geometry, saved-model validation, or Cycles/drawing output. No Blender controls are needed for a
   brief-led concept image. Reference images are optional. When you use them, keep the current brief authoritative.
6. Inspect the results for visual quality and obvious conflicts with the brief. Make focused corrections when needed,
   keeping the requested scope. Check visible texture scale, timber grain direction and plausible highlights and
   shadows without changing the accepted palette to compensate for lighting. Give concise progress updates as views finish.

## Output

- Save the selected images with descriptive filenames in a fresh directory under the repository-root
  `.ai/renders/`, unless the user names another destination. Preserve existing renders.
- Save the final prompts alongside the images in `prompts.md`, with any material illustrative assumptions.
- Deliver the images and their paths, noting any obvious remaining discrepancy or missing view. Finish when the
  requested views have been generated and saved. Report an unavailable generation tool as a blocker.
- Describe the set as concept imagery. Generated views can differ in geometry and do not establish dimensions,
  site conditions, technical performance, compliance, or construction readiness.
