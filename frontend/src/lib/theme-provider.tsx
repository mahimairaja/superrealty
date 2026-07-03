import { useCallback, useEffect, useState, type ReactNode } from "react";
import { ThemeContext, type Theme } from "@/lib/use-theme";

const KEY = "rr-theme";

function read(): Theme {
  const stored = localStorage.getItem(KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * Shared light/dark theme state, persisted and reflected onto <html class="dark">. Kept in one
 * context (not a per-component hook) so every consumer stays in sync: the sidebar toggle and the
 * root Clerk provider (which re-themes its widgets) react to the same state.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(read);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const setTheme = useCallback((t: Theme) => setThemeState(t), []);
  const toggle = useCallback(
    () => setThemeState((t) => (t === "dark" ? "light" : "dark")),
    [],
  );

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}
