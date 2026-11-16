import { defineConfig } from "oxlint";
import core from "ultracite/oxlint/core";

export default defineConfig({
  extends: [core],
  ignorePatterns: [
    "**/.ai/**",
    "**/.cache/**",
    "**/dist/**",
    "**/node_modules/**",
    "**/coverage/**",
    "**/*.lock",
    "budget/data/project.json",
  ],
  rules: {
    // These Ultracite defaults create churn without catching bugs in this small app.
    "default-case": "off",
    "eslint/curly": "off",
    "eslint/no-nested-ternary": "off",
    "eslint/no-void": "off",
    "eslint/prefer-named-capture-group": "off",
    // Adding `u` is a semantic regexp change. Keep existing, tested parsing behavior.
    "eslint/require-unicode-regexp": "off",
    "func-names": "off",
    "func-style": "off",
    "max-classes-per-file": "off",
    "no-await-in-loop": "off",
    "no-use-before-define": "off",
    "prefer-destructuring": "off",

    // Preserve the existing module boundaries and TypeScript conventions.
    "import/consistent-type-specifier-style": "off",
    "oxc/no-barrel-file": "off",
    "typescript/array-type": "off",
    "typescript/consistent-type-definitions": "off",
    "typescript/consistent-type-imports": "off",
    "unicorn/no-useless-undefined": "off",

    // Tooling conflicts or style-only suggestions with no correctness benefit here.
    "import/first": "off",
    "promise/avoid-new": "off",
    "promise/prefer-await-to-callbacks": "off",
    "promise/prefer-await-to-then": "off",
    // Existing component filenames are public import boundaries.
    "unicorn/filename-case": "off",
    "unicorn/import-style": "off",
    "unicorn/no-array-for-each": "off",
    "unicorn/no-array-reduce": "off",
    // In-place sorting is deliberate where collections are copied or locally owned.
    "unicorn/no-array-sort": "off",
    "unicorn/no-await-expression-member": "off",
    "unicorn/no-immediate-mutation": "off",
    "unicorn/numeric-separators-style": "off",
    "unicorn/prefer-export-from": "off",
    "unicorn/prefer-single-call": "off",
    "unicorn/prefer-string-replace-all": "off",
    "sort-keys": "off",
    "unicorn/text-encoding-identifier-case": "off",
  },
});
