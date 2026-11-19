/**
 * @file Theme preference: light, dark or follow the system.
 * Owner: Nisarg · Task: S2-NIS-19 · Issue: #320 · Requirements: NFR-06
 *
 * The preference is a display setting, not health data, so it may live in
 * localStorage (AI_RULES §11 only forbids health data there). Storage access is
 * guarded because private windows and blocked storage can throw.
 */

/** A theme the user can pick. */
export type ThemePreference = "light" | "dark" | "system";

/** The theme actually applied to the page. */
export type ResolvedTheme = "light" | "dark";

/** localStorage key for the preference. */
export const THEME_STORAGE_KEY = "symptom-checker-theme";

/**
 * Read the saved preference.
 *
 * @returns The saved preference, or "system" when none or unreadable.
 */
export function readThemePreference(): ThemePreference {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" || value === "system" ? value : "system";
  } catch {
    return "system";
  }
}

/**
 * Save the preference; ignored when storage is unavailable.
 *
 * @param preference - The preference to keep.
 */
export function saveThemePreference(preference: ThemePreference): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    // Storage blocked: the choice still applies for this visit.
  }
}

/**
 * Whether the operating system asks for dark mode.
 *
 * @returns True when the system prefers dark.
 */
export function systemPrefersDark(): boolean {
  return typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)").matches
    : false;
}

/**
 * Turn a preference into the theme to apply.
 *
 * @param preference - User preference.
 * @param prefersDark - Whether the system prefers dark.
 * @returns "light" or "dark".
 */
export function resolveTheme(preference: ThemePreference, prefersDark: boolean): ResolvedTheme {
  if (preference === "system") return prefersDark ? "dark" : "light";
  return preference;
}

/**
 * Apply a theme to the document root (`.dark` class and colour-scheme).
 *
 * @param theme - Theme to apply.
 */
export function applyTheme(theme: ResolvedTheme): void {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
}
