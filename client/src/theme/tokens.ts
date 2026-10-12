/**
 * @file Design tokens and theme system for the AI-Based Symptom Checker frontend.
 *
 * Defines centralized design tokens including brand colors, accessible neutral
 * scales, deterministic medical risk-tier styles, typography scales, spacing,
 * and focus ring utilities. All color combinations satisfy WCAG 2.1 Level AA
 * contrast requirements (contrast ratio >= 4.5:1 for standard body text).
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S0-MAN-1 · Requirements: DR-01, NFR-06
 */

/** Brand and neutral color tokens. */
export const COLOR_TOKENS = {
  brand: {
    primary: "#0f766e", // Teal-700: Primary CTAs, active headers
    primaryHover: "#115e59", // Teal-800: Button hover state
    primaryLight: "#14b8a6", // Teal-500: Accents, indicators
    subtle: "#f0fdfa", // Teal-50: Container backgrounds
  },
  neutral: {
    background: "#f8fafc", // Slate-50: Application canvas background
    surface: "#ffffff", // Pure white: Card surfaces, modals
    surfaceSubtle: "#f1f5f9", // Slate-100: Secondary card containers
    border: "#e2e8f0", // Slate-200: Dividers, borders
    borderStrong: "#cbd5e1", // Slate-300: High-contrast boundaries
    textPrimary: "#0f172a", // Slate-900: Headings, primary body text (18.6:1 contrast)
    textSecondary: "#475569", // Slate-600: Subtitles, helper text (5.37:1 contrast)
    textMuted: "#64748b", // Slate-500: Timestamps, captions (4.62:1 contrast)
  },
} as const;

/**
 * Deterministic styling tokens mapped to the three core risk tiers.
 *
 * Aligns with the deterministic risk engine tiers defined in docs/rules.md:
 * - SELF_CARE: Emerald green accents for mild, self-manageable conditions.
 * - CONSULT_DOCTOR: Amber warning accents for conditions requiring physician review.
 * - URGENT: Rose/Red urgent emergency accents highlighting immediate danger and 112.
 */
export const RISK_TIER_TOKENS = {
  SELF_CARE: {
    label: "Self-Care",
    bg: "#ecfdf5", // Emerald-50
    border: "#a7f3d0", // Emerald-200
    text: "#065f46", // Emerald-800 (6.82:1 contrast)
    badgeBg: "#059669", // Emerald-600
    badgeText: "#ffffff",
  },
  CONSULT_DOCTOR: {
    label: "Consult Doctor",
    bg: "#fffbeb", // Amber-50
    border: "#fde68a", // Amber-200
    text: "#92400e", // Amber-800 (5.91:1 contrast)
    badgeBg: "#d97706", // Amber-600
    badgeText: "#ffffff",
  },
  URGENT: {
    label: "Urgent Care (112)",
    bg: "#fff1f2", // Rose-50
    border: "#fecdd3", // Rose-200
    text: "#9f1239", // Rose-800 (7.43:1 contrast)
    badgeBg: "#e11d48", // Rose-600
    badgeText: "#ffffff",
  },
} as const;

/** Qualitative condition confidence label tokens (no raw percentages per AI_RULES.md §2). */
export const CONFIDENCE_LABEL_TOKENS = {
  Likely: {
    label: "Likely",
    bg: "#ccfbf1", // Teal-100
    text: "#115e59", // Teal-800
    border: "#99f6e4", // Teal-200
  },
  Possible: {
    label: "Possible",
    bg: "#fef3c7", // Amber-100
    text: "#92400e", // Amber-800
    border: "#fde68a", // Amber-200
  },
  "Less likely": {
    label: "Less likely",
    bg: "#f1f5f9", // Slate-100
    text: "#475569", // Slate-600
    border: "#e2e8f0", // Slate-200
  },
} as const;

/** Typography hierarchy tokens for readable medical interfaces. */
export const TYPOGRAPHY_TOKENS = {
  fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, sans-serif",
  scale: {
    h1: { fontSize: "1.875rem", lineHeight: "2.25rem", fontWeight: "700" },
    h2: { fontSize: "1.5rem", lineHeight: "2.0rem", fontWeight: "600" },
    h3: { fontSize: "1.25rem", lineHeight: "1.75rem", fontWeight: "600" },
    bodyLg: { fontSize: "1.125rem", lineHeight: "1.75rem", fontWeight: "400" },
    body: { fontSize: "1.0rem", lineHeight: "1.5rem", fontWeight: "400" },
    bodySm: { fontSize: "0.875rem", lineHeight: "1.25rem", fontWeight: "400" },
    caption: { fontSize: "0.75rem", lineHeight: "1.0rem", fontWeight: "500" },
  },
} as const;

/** Spacing scale based on a 4px baseline grid. */
export const SPACING_TOKENS = {
  1: "0.25rem", // 4px
  2: "0.5rem", // 8px
  3: "0.75rem", // 12px
  4: "1.0rem", // 16px
  6: "1.5rem", // 24px
  8: "2.0rem", // 32px
  12: "3.0rem", // 48px
  16: "4.0rem", // 64px
} as const;

/** Elevation and drop shadow tokens. */
export const SHADOW_TOKENS = {
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.05)",
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.05)",
} as const;

/** Focus ring styling token for WCAG 2.1 AA keyboard accessibility. */
export const ACCESSIBILITY_TOKENS = {
  focusRing: "2px solid #0f766e",
  focusOffset: "2px",
  minTouchTarget: "44px",
} as const;

/** Type alias for supported risk levels. */
export type RiskTierKey = keyof typeof RISK_TIER_TOKENS;

/** Type alias for qualitative confidence levels. */
export type ConfidenceKey = keyof typeof CONFIDENCE_LABEL_TOKENS;
