import { resolve } from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { createBudgetApiPlugin } from "./src/server/api-vite-plugin.js";

const projectRoot = resolve(import.meta.dirname);
/** Dev and preview both serve only on the fixed loopback port. */
const loopbackServer = { host: "127.0.0.1", port: 8437, strictPort: true };

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
              test: /node_modules[\\/](?:@base-ui|@floating-ui|lucide-react|simple-icons|tailwind-merge|tailwind-variants)[\\/]/,
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
  server: loopbackServer,
  preview: loopbackServer,
});
