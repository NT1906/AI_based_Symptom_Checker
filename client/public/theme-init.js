/**
 * @file Apply the saved theme before React loads, so dark mode never flashes white.
 * Owner: Nisarg · Task: S2-NIS-19 · Issue: #320 · Requirements: NFR-06
 *
 * Loaded as a same-origin script because the CSP forbids inline scripts.
 * Keep the storage key in sync with src/components/theme/theme.ts.
 */
(function () {
  var preference;
  try {
    preference = window.localStorage.getItem("symptom-checker-theme") || "system";
  } catch {
    preference = "system"; // storage blocked (private window, policy)
  }
  var dark =
    preference === "dark" ||
    (preference !== "light" &&
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  var root = document.documentElement;
  if (dark) root.classList.add("dark");
  root.style.colorScheme = dark ? "dark" : "light";
})();
