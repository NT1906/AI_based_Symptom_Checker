# Theme (light / dark / system)

**Owner:** Nisarg · **Task:** S2-NIS-19 (#320) · **Requirements:** NFR-06

- `theme.ts` reads, saves (localStorage key `symptom-checker-theme`) and applies the
  preference. A display setting is not health data, so localStorage is allowed (AI_RULES §11).
- `ThemeProvider` (in `app/providers.tsx`) keeps the `.dark` class on `<html>` in sync and
  follows the OS setting when the preference is "system". `useTheme()` exposes it.
- `ThemeToggle` is the header menu (Light / Dark / System).
- `public/theme-init.js` applies the saved theme before React loads, so dark mode does not
  flash white. It is a separate file because the CSP forbids inline scripts; keep its
  storage key in sync with `theme.ts`.

Test: `npx vitest run src/components/theme`.
