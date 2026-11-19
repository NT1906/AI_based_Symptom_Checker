/**
 * @file Self-care guidance cards for low-risk clinical assessment outcomes.
 * Owner: Dimple · Task: S2-DIM-2, S2-DIM-5 · Requirements: idea §8, DR-01, DR-05, NFR-06
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 *
 * Medical-safety rules (AI_RULES.md §2):
 * - Renders ONLY when risk tier is explicitly SELF_CARE (returns null otherwise).
 * - Never diagnoses, prescribes, or recommends specific medication dosages.
 * - Clarifies that low risk does not mean zero risk; never discourages professional care.
 * - Displays mandatory medical disclaimer and emergency escalation cues (112).
 * - Gracefully provides clinically sound defaults if guidance data is incomplete.
 */

import { Check, Droplets, House, Stethoscope, TriangleAlert } from "lucide-react";
import React from "react";
import type { RiskLevel } from "./RiskBadge";

/** Props for the SelfCareGuidanceCard component. */
export interface SelfCareGuidanceCardProps {
  /** Deterministic risk level from clinical triage. Must be 'SELF_CARE' to render. */
  riskLevel: RiskLevel;
  /** Primary condition name or clinical topic for guidance context (optional). */
  conditionName?: string;
  /** Summary or rationale headline from triage guidance (optional). */
  summary?: string;
  /** Specific self-care recommendations from the guidance engine (optional). */
  advice?: string[];
  /** Non-prescriptive supportive advice alias matching knowledge service (optional). */
  generalAdvice?: string[];
  /** Red-flag warning signs that mandate clinical escalation (optional). */
  warningSigns?: string[];
  /** Warning signs alias matching knowledge service (optional). */
  whenToSeekCare?: string[];
  /** Safe monitoring tips from knowledge service (optional). */
  monitoringTips?: string[];
  /** Recommended timeframe for monitoring or follow-up (optional). */
  timeframe?: string;
  /** Error flag or message if guidance retrieval failed (optional). */
  error?: boolean | string | null;
  /** National emergency telephone number (defaults to '112'). */
  emergencyNumber?: string;
  /** Callback triggered if the user opts to find a healthcare provider anyway. */
  onConsultDoctorClick?: () => void;
  /** Optional additional CSS class name for outer wrapper. */
  className?: string;
}

/** Standard clinical fallback recommendations for low-risk home care. */
export const DEFAULT_SELF_CARE_ADVICE: readonly string[] = [
  "Prioritize restorative rest and avoid strenuous physical exertion.",
  "Maintain steady hydration with water, warm clear broths, or herbal fluids.",
  "Observe symptoms over the next 24 to 48 hours and note any changes.",
  "Avoid unverified remedies or self-medicating beyond standard over-the-counter care.",
];

/** Standard clinical fallback warning signs requiring medical evaluation. */
export const DEFAULT_WARNING_SIGNS: readonly string[] = [
  "Symptoms noticeably worsen or fail to improve after 3 to 5 days.",
  "New onset of high fever, persistent chills, or severe pain.",
  "Difficulty breathing, chest tightness, or unexplained dizziness.",
  "Inability to tolerate fluids or signs of severe dehydration.",
];

/** Mandatory medical disclaimer text per AI_RULES.md §2 rule 8. */
const DISCLAIMER_TEXT =
  "This is not a medical diagnosis. Always consult a qualified healthcare professional. Never ignore or delay seeking professional medical advice because of information provided by this triage aid.";

/**
 * Responsive card group presenting clear, accessible self-care guidance
 * for assessments classified as low-risk (SELF_CARE).
 *
 * Returns null if the assessment risk tier is CONSULT_DOCTOR or URGENT,
 * ensuring elevated risk cases never display low-risk home care advice.
 *
 * @param props - Component properties.
 * @returns Self-care guidance card layout or null.
 */
export function SelfCareGuidanceCard({
  riskLevel,
  conditionName,
  summary,
  advice,
  generalAdvice,
  warningSigns,
  whenToSeekCare,
  monitoringTips,
  timeframe = "24 to 48 hours",
  error,
  emergencyNumber = "112",
  onConsultDoctorClick,
  className = "",
}: SelfCareGuidanceCardProps): React.ReactElement | null {
  // Strict gate: Low-risk guidance is ONLY shown for SELF_CARE outcomes
  if (riskLevel !== "SELF_CARE") {
    return null;
  }

  // Handle guidance retrieval failure gracefully
  if (error) {
    const errorMsg =
      typeof error === "string"
        ? error
        : "Guidance information is temporarily unavailable.";

    return (
      <section
        role="region"
        aria-label="Self-care guidance status"
        className={`rounded-xl border border-warning/25 bg-warning/5 p-5 shadow-xs sm:p-6 ${className}`}
      >
        <div className="flex items-start gap-3">
          <span className="text-2xl" aria-hidden="true">
            <TriangleAlert className="size-5" aria-hidden="true" />
          </span>
          <div className="space-y-2">
            <h2 className="text-base font-bold text-warning-strong sm:text-lg">
              Self-Care Information Notice
            </h2>
            <p className="text-sm text-warning-strong leading-relaxed">
              {errorMsg} Although detailed guidance could not be loaded, your
              assessment remains in the low-risk tier.
            </p>
            <ul className="mt-2 list-disc pl-5 space-y-1 text-xs text-warning-strong sm:text-sm">
              <li>Rest and stay hydrated with water or oral fluids.</li>
              <li>Monitor your symptoms closely over the next 24 to 48 hours.</li>
              <li>
                If you feel uncertain or your symptoms worsen, consult a doctor
                promptly.
              </li>
            </ul>
            <p className="pt-2 text-xs text-muted-foreground italic">
              {DISCLAIMER_TEXT}
            </p>
          </div>
        </div>
      </section>
    );
  }

  // Resolve advice items: use provided list if non-empty, otherwise use safe clinical defaults
  const resolvedAdvice =
    advice && advice.length > 0
      ? advice
      : generalAdvice && generalAdvice.length > 0
        ? generalAdvice
        : DEFAULT_SELF_CARE_ADVICE;

  // Resolve warning signs: use provided list if non-empty, otherwise use safe clinical defaults
  const resolvedWarningSigns =
    warningSigns && warningSigns.length > 0
      ? warningSigns
      : whenToSeekCare && whenToSeekCare.length > 0
        ? whenToSeekCare
        : DEFAULT_WARNING_SIGNS;

  return (
    <section
      role="region"
      aria-labelledby="self-care-heading"
      className={`space-y-6 rounded-xl border border-success/25 bg-card p-5 shadow-sm sm:p-7 ${className}`}
    >
      {/* 1. Header Banner & Safety Notice */}
      <header className="space-y-2 border-b border-success/25 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center gap-1.5 rounded-full border border-success/40 bg-success/10 px-3 py-1 text-xs font-semibold text-success-strong"
              role="status"
            >
              <House className="size-4 shrink-0" aria-hidden="true" />
              <span>Low-Risk Outcome</span>
            </span>
            <span className="text-xs font-medium text-muted-foreground">
              Informational Home Management
            </span>
          </div>

          {conditionName && (
            <span className="text-xs font-semibold text-primary-strong bg-primary/10 rounded-lg px-2.5 py-1 border border-primary/25">
              Context: {conditionName}
            </span>
          )}
        </div>

        <h2
          id="self-care-heading"
          className="text-xl font-bold tracking-tight text-foreground sm:text-2xl"
        >
          Recommended Self-Care &amp; Monitoring
        </h2>

        <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
          {summary ||
            "Your reported symptoms match mild, low-risk conditions that typically resolve with supportive home care."}
        </p>

        {/* Safety reminder: Low risk != zero risk */}
        <div
          role="note"
          aria-label="Safety notice"
          className="rounded-xl border border-success/25 bg-success/5 p-3 text-xs leading-relaxed text-success-strong sm:text-sm"
        >
          <strong className="font-semibold text-success-strong">
            Important Medical Reminder:{" "}
          </strong>
          A low-risk assessment indicates supportive care is reasonable, but{" "}
          <strong>low risk does not mean zero risk</strong>. Listen to your body
          and seek medical attention if anything changes.
        </div>
      </header>

      {/* 2. Responsive Card Grid */}
      <div className="grid gap-5 md:grid-cols-2">
        {/* Card A: Supportive Rest & Hydration */}
        <article
          aria-labelledby="card-rest-heading"
          className="flex flex-col justify-between rounded-xl border border-border bg-muted/60 p-4 sm:p-5 transition hover:border-success/40 hover:shadow-xs"
        >
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-success-strong">
              <span className="text-xl" aria-hidden="true">
                <Droplets className="size-5" aria-hidden="true" />
              </span>
              <h3
                id="card-rest-heading"
                className="text-base font-bold text-foreground"
              >
                Supportive Care Steps
              </h3>
            </div>
            <ul className="space-y-2 text-xs leading-relaxed text-muted-foreground sm:text-sm">
              {resolvedAdvice.map((item, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-success"
                    aria-hidden="true"
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            {monitoringTips && monitoringTips.length > 0 && (
              <div className="mt-3 border-t border-border pt-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Monitoring Tips
                </h4>
                <ul className="mt-1.5 space-y-1 text-xs text-muted-foreground sm:text-sm">
                  {monitoringTips.map((tip, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-success-strong" aria-hidden="true">
                        <Check className="size-5" aria-hidden="true" />
                      </span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </article>

        {/* Card B: Observation & Red-Flag Escalation */}
        <article
          aria-labelledby="card-escalation-heading"
          className="flex flex-col justify-between rounded-xl border border-warning/25 bg-warning/5 p-4 sm:p-5 transition hover:border-warning/40 hover:shadow-xs"
        >
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-warning-strong">
              <span className="text-xl" aria-hidden="true">
                <TriangleAlert className="size-5" aria-hidden="true" />
              </span>
              <h3
                id="card-escalation-heading"
                className="text-base font-bold text-warning-strong"
              >
                When to Seek Medical Care
              </h3>
            </div>
            <p className="text-xs text-warning-strong leading-relaxed sm:text-sm">
              Consult a healthcare provider immediately or call{" "}
              <strong>{emergencyNumber}</strong> if you notice:
            </p>
            <ul className="space-y-2 text-xs leading-relaxed text-warning-strong sm:text-sm">
              {resolvedWarningSigns.map((item, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-warning"
                    aria-hidden="true"
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {timeframe && (
            <div className="mt-4 pt-3 border-t border-warning/25 text-xs text-warning-strong">
              <span className="font-semibold">Observation window: </span>
              <span>Re-evaluate if symptoms persist past {timeframe}.</span>
            </div>
          )}
        </article>
      </div>

      {/* 3. Action bar & Physician Consultation Link */}
      <footer className="space-y-4 pt-2">
        {onConsultDoctorClick && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-xl border border-border bg-muted/60 p-4">
            <div className="text-xs text-muted-foreground sm:text-sm text-center sm:text-left">
              Prefer speaking with a professional for reassurance?
            </div>
            <button
              type="button"
              onClick={onConsultDoctorClick}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-input bg-card px-4 py-2.5 text-xs font-semibold text-foreground shadow-xs transition hover:bg-muted focus:outline-none focus:ring-4 focus:ring-ring/20 sm:text-sm"
            >
              <Stethoscope className="size-4 shrink-0" aria-hidden="true" />
              <span>Find Nearby Clinic / Doctor</span>
            </button>
          </div>
        )}

        {/* Mandatory Medical Disclaimer (AI_RULES.md §2 rule 8) */}
        <p
          className="text-center text-xs leading-relaxed text-muted-foreground border-t border-border pt-3"
        >
          {DISCLAIMER_TEXT}
        </p>
      </footer>
    </section>
  );
}

export default SelfCareGuidanceCard;
