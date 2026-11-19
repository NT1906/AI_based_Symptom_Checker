/**
 * @file Tests for the theme preference, provider and toggle.
 * Owner: Nisarg · Task: S2-NIS-19 · Issue: #320 · Requirements: NFR-06
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  THEME_STORAGE_KEY,
  applyTheme,
  readThemePreference,
  resolveTheme,
  saveThemePreference,
} from "./theme";
import { ThemeProvider } from "./ThemeProvider";
import { ThemeToggle } from "./ThemeToggle";

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.classList.remove("dark");
  document.documentElement.style.colorScheme = "";
});

describe("theme preference", () => {
  it("defaults to system and ignores unknown values", () => {
    expect(readThemePreference()).toBe("system");
    window.localStorage.setItem(THEME_STORAGE_KEY, "purple");
    expect(readThemePreference()).toBe("system");
  });

  it("round-trips a saved preference", () => {
    saveThemePreference("dark");
    expect(readThemePreference()).toBe("dark");
  });

  it("falls back safely when storage throws", () => {
    const get = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const set = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(readThemePreference()).toBe("system");
    expect(() => saveThemePreference("dark")).not.toThrow();
    get.mockRestore();
    set.mockRestore();
  });

  it("resolves system against the OS setting", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("light", true)).toBe("light");
  });

  it("applies the dark class and colour scheme", () => {
    applyTheme("dark");
    expect(document.documentElement).toHaveClass("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
    applyTheme("light");
    expect(document.documentElement).not.toHaveClass("dark");
  });
});

describe("ThemeToggle", () => {
  it("switches to dark, remembers it, and marks the choice", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Change theme" }));
    await user.click(screen.getByRole("menuitem", { name: /dark/i }));

    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");

    await user.click(screen.getByRole("button", { name: "Change theme" }));
    expect(screen.getByRole("menuitem", { name: /dark/i })).toHaveTextContent("Dark");
    expect(screen.getByLabelText("selected")).toBeInTheDocument();

    await user.click(screen.getByRole("menuitem", { name: /light/i }));
    expect(document.documentElement).not.toHaveClass("dark");
  });
});
