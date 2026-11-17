/**
 * @file RiskBadge — compact visual indicator of an assessment's risk level.
 * Owner: Dimple · Task: S1-DIM-3, S2-DIM-5 · Requirements: FR-06, FR-15, DR-02, NFR-06
 *
 * Renders SELF_CARE, CONSULT_DOCTOR, or URGENT as an accessible colour-coded pill.
 * Colour is never the ONLY signal — each badge includes an icon and text
 * label to satisfy WCAG 2.1 AA (NFR-06).
 */

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
  { label: string; icon: string; className: string }
> = {
  SELF_CARE: {
    label: "Self-Care",
    icon: "🏠",
    className: "bg-emerald-50 text-emerald-900 border-emerald-400 ring-emerald-500/10",
  },
  CONSULT_DOCTOR: {
    label: "Consult a Doctor",
    icon: "🩺",
    className: "bg-amber-50 text-amber-950 border-amber-400 ring-amber-500/10",
  },
  URGENT: {
    label: "Urgent Care Needed",
    icon: "🚨",
    className: "bg-rose-50 text-rose-950 border-rose-400 ring-rose-500/10",
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
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold tracking-tight shadow-2xs ring-1",
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
