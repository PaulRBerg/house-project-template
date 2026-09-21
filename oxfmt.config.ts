import { defineConfig } from "oxfmt";
import ultracite from "ultracite/oxfmt";

export default defineConfig({
  ...ultracite,
  ignorePatterns: [
    ...(ultracite.ignorePatterns ?? []),
    "**/.ai/**",
    "**/.cache/**",
    "**/coverage/**",
    "**/dist/**",
    "**/node_modules/**",
    "**/*.lock",
    "**/*.md",
    "**/*.yaml",
    "**/*.yml",
    "budget/data/project.json",
  ],
  printWidth: 100,
  sortPackageJson: false,
  sortTailwindcss: {
    functions: ["cn"],
    stylesheet: "budget/src/styles/global.css",
  },
  trailingComma: "all",
});
