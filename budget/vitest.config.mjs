import { defineDevkitConfig } from "@prb/devkit/vitest";
import react from "@vitejs/plugin-react";

const baseConfig = defineDevkitConfig();

export default {
  ...baseConfig,
  plugins: [react()],
  test: {
    ...baseConfig.test,
    globals: false,
    reporters: ["default"],
    restoreMocks: true,
    projects: [
      {
        extends: true,
        test: {
          name: "node",
          include: ["src/**/*.test.ts", "scripts/**/*.test.ts"],
        },
      },
      {
        extends: true,
        test: {
          name: "ui",
          environment: "jsdom",
          include: ["src/**/*.test.tsx"],
          setupFiles: ["src/test/setup.ts"],
        },
      },
    ],
  },
};
