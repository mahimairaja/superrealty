import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/geist";
import "./index.css";
import App from "./App.tsx";
import { ThemeProvider } from "./lib/theme-provider";
import { ThemedClerkProvider } from "./components/app/themed-clerk-provider";

// Resolve the theme before first paint so there is no light/dark flash.
const stored = localStorage.getItem("rr-theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
document.documentElement.classList.toggle(
  "dark",
  stored ? stored === "dark" : prefersDark,
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <ThemedClerkProvider>
        <App />
      </ThemedClerkProvider>
    </ThemeProvider>
  </StrictMode>,
);
