import { resolve } from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { createBudgetApiPlugin } from "./src/server/api-vite-plugin.js";

const projectRoot = resolve(import.meta.dirname);

export default defineConfig({
  plugins: [tailwindcss(), react(), createBudgetApiPlugin({ projectRoot })],
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: "framework",
              test: /node_modules[\\/](?:nuqs|react|react-dom|scheduler|use-sync-external-store)[\\/]/,
              priority: 30,
            },
            {
              name: "interface",
              test: /node_modules[\\/](?:@base-ui|@floating-ui|lucide-react|tailwind-merge|tailwind-variants)[\\/]/,
              priority: 20,
            },
            {
              name: "data-content",
              test: /node_modules[\\/](?:react-markdown|zod)[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  preview: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
});
