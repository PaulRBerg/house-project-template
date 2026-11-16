if (import.meta.env.DEV) {
  import("react-grab").then(({ getGlobalApi }) => {
    getGlobalApi()?.setOptions({ activationKey: "Meta+G", keyHoldDuration: 0 });
  });
}

import { NuqsAdapter } from "nuqs/adapters/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App.js";

import "./styles/global.css";

const root = document.querySelector<HTMLDivElement>("#root");

if (!root) {
  throw new Error("Elementul #root lipsește din index.html.");
}

createRoot(root).render(
  <StrictMode>
    <NuqsAdapter>
      <App />
    </NuqsAdapter>
  </StrictMode>,
);
