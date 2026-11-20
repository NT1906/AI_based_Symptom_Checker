/**
 * @file React context that applies and exposes the theme preference.
 * Owner: Nisarg · Task: S2-NIS-19 · Issue: #320 · Requirements: NFR-06
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  applyTheme,
  readThemePreference,
  resolveTheme,
  saveThemePreference,
  systemPrefersDark,
  type ResolvedTheme,
  type ThemePreference,
} from "./theme";

/** Value shared by the theme context. */
type ThemeContextValue = {
  /** What the user picked. */
  preference: ThemePreference;
  /** What is applied now. */
  resolved: ResolvedTheme;
  /** Change and remember the preference. */
  setPreference: (preference: ThemePreference) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

/**
 * Provide the theme to the app and keep `<html>` in sync with it.
 *
 * @param props - Children to render.
 * @param props.children - The app.
 * @returns The provider.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [preference, setPreferenceState] = useState<ThemePreference>(readThemePreference);
  const [prefersDark, setPrefersDark] = useState<boolean>(systemPrefersDark);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (event: MediaQueryListEvent) => setPrefersDark(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const resolved = resolveTheme(preference, prefersDark);

  useEffect(() => {
    applyTheme(resolved);
  }, [resolved]);

  const setPreference = useCallback((next: ThemePreference) => {
    saveThemePreference(next);
    setPreferenceState(next);
  }, []);

  const value = useMemo(
    () => ({ preference, resolved, setPreference }),
    [preference, resolved, setPreference],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/**
 * Read the theme context.
 *
 * @returns The current theme and a setter; a light fallback outside the provider.
 */
export function useTheme(): ThemeContextValue {
  return (
    useContext(ThemeContext) ?? {
      preference: "light",
      resolved: "light",
      setPreference: () => undefined,
    }
  );
}
