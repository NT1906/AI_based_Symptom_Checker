/**
 * @file RiskBadge — compact visual indicator of an assessment's risk level.
 * Owner: Dimple · Task: S1-DIM-3, S2-DIM-5 · Requirements: FR-06, FR-15, DR-02, NFR-06
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 *
 * Renders SELF_CARE, CONSULT_DOCTOR, or URGENT as an accessible colour-coded pill.
 * Colour is never the ONLY signal — each badge includes an icon and text
 * label to satisfy WCAG 2.1 AA (NFR-06).
 */

import { House, Siren, Stethoscope, type LucideIcon } from "lucide-react";

/** The three risk tiers produced by the deterministic risk engine. */
export type RiskLevel = "SELF_CARE" | "CONSULT_DOCTOR" | "URGENT";

/** Props for the RiskBadge component. */
export type RiskBadgeProps = {
  /** Risk level returned by the assessment result. */
  level: RiskLevel;
  /** Optional additional CSS class names. */
  className?: string;
};

/** Display configuration for each risk level with high-contrast text (>7:1). */
const RISK_CONFIG: Record<
  RiskLevel,
  { label: string; icon: LucideIcon; className: string }
> = {
  SELF_CARE: {
    label: "Self-Care",
    icon: House,
    className: "bg-success/10 text-success-strong border-success/40 ring-success/40",
  },
  CONSULT_DOCTOR: {
    label: "Consult a Doctor",
    icon: Stethoscope,
    className: "bg-warning/10 text-warning-strong border-warning/40 ring-warning/40",
  },
  URGENT: {
    label: "Urgent Care Needed",
    icon: Siren,
    className: "bg-danger/10 text-danger-strong border-danger/40 ring-danger/40",
  },
};

/**
 * Compact pill badge that displays the clinical triage risk level.
 * Uses color, icon, and accessible text (WCAG 2.1 AA).
 *
 * @param props - Component props.
 * @returns A styled status badge element.
 *
 * @example
 * ```tsx
 * <RiskBadge level="URGENT" />
 * ```
 */
export function RiskBadge({ level, className = "" }: RiskBadgeProps) {
  const config = RISK_CONFIG[level];

  return (
    <span
      role="status"
      aria-label={`Risk level: ${config.label}`}
      className={[
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold tracking-tight shadow-2xs ring-1",
        config.className,
        className,
      ].join(" ")}
    >
      <config.icon className="size-3.5" aria-hidden="true" />
      <span>{config.label}</span>
    </span>
  );
}

export default RiskBadge;
