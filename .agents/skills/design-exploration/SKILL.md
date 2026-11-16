---
name: design-exploration
skill-dependencies: [blender-model, concept-imagery]
description:
  Explore house redesigns through rendered alternatives and user feedback. Use for iterative exterior, interior,
  garden, massing, material, or color studies before selecting a design.
---

# Design Exploration

Generate a small visual round, learn from the user's reaction, and refine until they select a direction.

## Frame the round

- Read the conversation and previous exploration notes. Separate explicit likes, dislikes, and uncertain reactions.
  Treat “interesting” as a lead, not acceptance. A rejected proposal does not establish dislike of every ingredient.
- Use [concept-imagery](../concept-imagery/SKILL.md) for brief interpretation, image generation, and visual inspection.
  Keep accepted requirements outside the requested exploration fixed. State proposed departures and material assumptions.
- Choose a concrete next direction and proceed without a preliminary approval round. Ask only for missing input that
  materially changes the task. When inspiration would help, reuse the household's recorded
  references in `brief/references.md` and earlier exploration notes instead of repeating research for each variation.
- Preserve elements the user likes, including texture scale and material coverage. Interpret “something different”
  within the scope of their latest feedback. For color studies, vary colors while keeping geometry, textures, and
  material coverage fixed. Explore new massing or materials when the user requests those changes.
- For layout studies, review the changed room connections and circulation in a plan or cutaway before developing
  furnishing detail. Use [blender-model](../blender-model/SKILL.md) when that review needs modeled geometry.

## Render and review

1. State the direction and what this round tests. Default to two or three images unless the user specifies otherwise.
   Distinguish alternative designs from multiple views of one design.
2. For alternatives, keep the camera position, orientation, field of view, setting, and lighting comparable, with sharp
   focus and straight architectural verticals. For multiple views, establish one reference
   image and carry its architecture and materials across the set. Inspect local reference images before editing them.
3. Preserve geometry outside the intended changes. Describe visible constraints directly in each prompt.
   Inspect the generated images for unintended changes and inconsistent materials. Correct material conflicts before delivery.
4. Show the images with short labels and one sentence explaining each option. Link the saved files and ask one focused
   feedback question. Complete the requested round before waiting for the user's response.
5. On the next response, record the feedback and use it to guide the next round. Do not generate further rounds without
   user feedback or an explicit request for more alternatives.

## Output and verification

- Save every round under repository-root `.ai/explorations/YYYY-MM-DD/<EXPLORATION_NAME>/`.
  Use the local date and a descriptive kebab-case name that distinguishes the round, such as `facade-04-brick-timber`.
  This destination overrides the concept-imagery skill's default. Preserve previous rounds.
- Save images with descriptive filenames. Keep final prompts, reference paths, proposed departures, assumptions,
  and user feedback together in `prompts.md`. Identify the preceding round when refining an earlier design.
- Verify that each delivered image exists at its linked path and that the saved prompts match the delivered set.
- Finish the round when the requested images and notes are saved, inspected, and shown for user feedback.

## Selection

Keep exploration notes in the exploration directory. Preference feedback alone does not update the accepted brief,
budget, or canonical Blender model. When the user selects a design, follow the repository's acceptance and
reconciliation workflow. Generated concepts remain visual proposals, not evidence of dimensions or construction readiness.
