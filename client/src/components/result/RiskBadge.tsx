/**
 * @file RiskBadge — accessible visual indicator of deterministic clinical triage risk tier.
 *
 * Implements FR-06 (deterministic risk tiering), FR-15 (clinical triage categorization),
 * DR-02 (red-flag emergency classification), and NFR-06 (WCAG 2.1 AA accessible indicators).
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-3 · Requirements: FR-06, FR-15, DR-02, NFR-06
 */

import React from "react";
import type { RiskLevel } from "./types";

/** Props for the RiskBadge component. */
export interface RiskBadgeProps {
  /** Deterministic risk level from clinical assessment. */
  level: RiskLevel;
  /** Optional additional CSS class names for custom layout spacing. */
  className?: string;
}

/** Visual and semantic configuration for each triage risk tier. */
export interface RiskConfig {
  /** User-friendly label for the risk tier. */
  label: string;
  /** Accessible visual emoji or icon representing the tier. */
  icon: string;
  /** Tailwind styling classes ensuring WCAG 2.1 AA contrast. */
  className: string;
  /** Detailed description for the tier. */
  description: string;
}

/** Display configuration dictionary for each clinical risk tier. */
export const RISK_CONFIG: Record<RiskLevel, RiskConfig> = {
  SELF_CARE: {
    label: "Self-Care",
    icon: "🏠",
    className: "bg-emerald-50 text-emerald-800 border-emerald-300 ring-emerald-500/10 dark:bg-emerald-950 dark:text-emerald-200 dark:border-emerald-800",
    description: "Recommended for self-management at home. Follow general self-care guidance and monitor your condition.",
  },
  CONSULT_DOCTOR: {
    label: "Consult a Doctor",
    icon: "🩺",
    className: "bg-amber-50 text-amber-800 border-amber-300 ring-amber-500/10 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800",
    description: "Medical consultation recommended within 24–48 hours. This is not an emergency, but requires clinical evaluation.",
  },
  URGENT: {
    label: "Urgent Care Needed",
    icon: "🚨",
    className: "bg-rose-50 text-rose-800 border-rose-300 ring-rose-500/10 dark:bg-rose-950 dark:text-rose-200 dark:border-rose-800",
    description: "Immediate emergency medical care required. Call emergency services (112) or go to the nearest emergency room.",
  },
};

/**
 * Returns configuration for a given triage risk level.
 *
 * @param level - Deterministic clinical risk level.
 * @returns RiskConfig object with label, icon, and styling.
 */
export function getRiskConfig(level: RiskLevel): RiskConfig {
  return RISK_CONFIG[level] ?? RISK_CONFIG.CONSULT_DOCTOR;
}

/**
 * Compact pill badge displaying clinical triage risk level with icon and text label.
 * Colour is never the only signal to satisfy WCAG 2.1 AA.
 *
 * @param props - Component properties.
 * @returns Rendered status badge element.
 */
export function RiskBadge({ level, className = "" }: RiskBadgeProps): React.ReactElement {
  const config = getRiskConfig(level);

  return (
    <span
      role="status"
      aria-label={`Risk level: ${config.label}`}
      className={[
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold tracking-tight shadow-xs ring-1",
        config.className,
        className,
      ].join(" ")}
    >
      <span aria-hidden="true">{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}

export default RiskBadge;
