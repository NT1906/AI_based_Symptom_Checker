/**
 * @file Faint grid behind the hero that fades out at the edges.
 * Owner: Nisarg · Task: S2-NIS-20 · Issue: #321 · Requirements: NFR-06
 *
 * Adapted from Aceternity UI "Grid and Dot Backgrounds" (ui.aceternity.com).
 * Uses the border token so it follows light and dark mode.
 */

/**
 * Decorative grid layer.
 *
 * @returns The background element.
 */
export function GridBackground(): React.JSX.Element {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 [background-image:linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] [background-size:44px_44px] [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)] opacity-70"
    />
  );
}
