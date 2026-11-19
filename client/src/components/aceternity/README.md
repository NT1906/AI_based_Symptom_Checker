# Aceternity UI effects

**Owner:** Nisarg · **Task:** S2-NIS-20 (#321)

Decorative components adapted from [Aceternity UI](https://ui.aceternity.com) (free to use):
`Spotlight`, `TextGenerateEffect`, `BentoGrid` / `BentoGridItem` and `GridBackground`.

They were changed to use the design tokens (light and dark mode), to stay out of the
accessibility tree when purely decorative, and to respect reduced motion through
`MotionConfig reducedMotion="user"` in `app/providers.tsx`.

Use them sparingly (landing page only) to keep the calm, clinical look.
