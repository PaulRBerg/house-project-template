import path from "node:path";

const budget = (recipe, ...args) =>
  ["just", "--justfile", "budget/justfile", "--working-directory", "budget", recipe, ...args].join(
    " ",
  );

const budgetRelative = (files) => {
  const budgetRoot = path.resolve("budget");
  return files.map((file) => path.relative(budgetRoot, file).replaceAll(path.sep, "/")).toSorted();
};

/**
 * @type {import("lint-staged").Configuration}
 */
export default {
  "*.{ts,tsx,mts,cts,js,mjs,cjs,json,jsonc,css,html}": "just ox-write",
  "*.{md,yml,yaml}": "na prettier --write",
  "*.py": "just py-write",
  "budget/src/**/*.{ts,tsx}": (files) => budget("lint-eslint", ...budgetRelative(files)),
  "budget/{eslint.config.js,src/styles/global.css}": () => budget("lint-eslint"),
  "budget/**/*.{ts,tsx}": () => budget("typecheck"),
  "{budget/data/project.json,brief/*.md}": () => budget("test-node", "src/data/catalogue.test.ts"),
  ".agents/skills/**/{SKILL.md,agents/openai.yaml}": "bash -c 'just skill-check' --",
  // One key, so a commit touching both code and design data runs the suite once.
  "model/{engine,scripts,tests,design,assets}/**/*.{py,json,jsonl}": () => "just model-tests",
};
