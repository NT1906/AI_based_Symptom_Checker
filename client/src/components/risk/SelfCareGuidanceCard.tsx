/**
 * @file Self-care guidance cards for low-risk clinical assessment outcomes.
 * Owner: Dimple · Task: S2-DIM-2 · Requirements: idea §8, DR-01, DR-05
 *
 * Medical-safety rules (AI_RULES.md §2):
 * - Renders ONLY when risk tier is explicitly SELF_CARE (returns null otherwise).
 * - Never diagnoses, prescribes, or recommends specific medication dosages.
 * - Clarifies that low risk does not mean zero risk; never discourages professional care.
 * - Displays mandatory medical disclaimer and emergency escalation cues (112).
 * - Gracefully provides clinically sound defaults if guidance data is incomplete.
 */

import React from "react";
import type { RiskLevel } from "./RiskBadge";
import {
  COLOR_TOKENS,
  SHADOW_TOKENS,
  ACCESSIBILITY_TOKENS,
} from "../../theme/tokens";

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
        className={`rounded-2xl border border-amber-200 bg-amber-50/80 p-5 shadow-xs sm:p-6 ${className}`}
        style={{
          boxShadow: SHADOW_TOKENS.sm,
        }}
      >
        <div className="flex items-start gap-3">
          <span className="text-2xl" aria-hidden="true">
            ⚠️
          </span>
          <div className="space-y-2">
            <h2 className="text-base font-bold text-amber-950 sm:text-lg">
              Self-Care Information Notice
            </h2>
            <p className="text-sm text-amber-900 leading-relaxed">
              {errorMsg} Although detailed guidance could not be loaded, your
              assessment remains in the low-risk tier.
            </p>
            <ul className="mt-2 list-disc pl-5 space-y-1 text-xs text-amber-900 sm:text-sm">
              <li>Rest and stay hydrated with water or oral fluids.</li>
              <li>Monitor your symptoms closely over the next 24 to 48 hours.</li>
              <li>
                If you feel uncertain or your symptoms worsen, consult a doctor
                promptly.
              </li>
            </ul>
            <p className="pt-2 text-xs text-slate-500 italic">
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
      className={`space-y-6 rounded-3xl border border-emerald-200 bg-white p-5 shadow-sm sm:p-7 ${className}`}
      style={{
        boxShadow: SHADOW_TOKENS.md,
      }}
    >
      {/* 1. Header Banner & Safety Notice */}
      <header className="space-y-2 border-b border-emerald-100 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800"
              role="status"
            >
              <span aria-hidden="true">🏠</span>
              <span>Low-Risk Outcome</span>
            </span>
            <span className="text-xs font-medium text-slate-500">
              Informational Home Management
            </span>
          </div>

          {conditionName && (
            <span className="text-xs font-semibold text-teal-800 bg-teal-50 rounded-lg px-2.5 py-1 border border-teal-200">
              Context: {conditionName}
            </span>
          )}
        </div>

        <h2
          id="self-care-heading"
          className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl"
        >
          Recommended Self-Care &amp; Monitoring
        </h2>

        <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
          {summary ||
            "Your reported symptoms match mild, low-risk conditions that typically resolve with supportive home care."}
        </p>

        {/* Safety reminder: Low risk != zero risk */}
        <div
          role="note"
          aria-label="Safety notice"
          className="rounded-xl border border-emerald-200/80 bg-emerald-50/60 p-3 text-xs leading-relaxed text-emerald-950 sm:text-sm"
        >
          <strong className="font-semibold text-emerald-900">
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
          className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-slate-50/50 p-4 sm:p-5 transition hover:border-emerald-300 hover:shadow-xs"
        >
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-emerald-800">
              <span className="text-xl" aria-hidden="true">
                💧
              </span>
              <h3
                id="card-rest-heading"
                className="text-base font-bold text-slate-900"
              >
                Supportive Care Steps
              </h3>
            </div>
            <ul className="space-y-2 text-xs leading-relaxed text-slate-700 sm:text-sm">
              {resolvedAdvice.map((item, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600"
                    aria-hidden="true"
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            {monitoringTips && monitoringTips.length > 0 && (
              <div className="mt-3 border-t border-slate-200/60 pt-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Monitoring Tips
                </h4>
                <ul className="mt-1.5 space-y-1 text-xs text-slate-600 sm:text-sm">
                  {monitoringTips.map((tip, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-emerald-700" aria-hidden="true">
                        ✓
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
          className="flex flex-col justify-between rounded-2xl border border-amber-200 bg-amber-50/40 p-4 sm:p-5 transition hover:border-amber-300 hover:shadow-xs"
        >
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-amber-900">
              <span className="text-xl" aria-hidden="true">
                ⚠️
              </span>
              <h3
                id="card-escalation-heading"
                className="text-base font-bold text-amber-950"
              >
                When to Seek Medical Care
              </h3>
            </div>
            <p className="text-xs text-amber-900/90 leading-relaxed sm:text-sm">
              Consult a healthcare provider immediately or call{" "}
              <strong>{emergencyNumber}</strong> if you notice:
            </p>
            <ul className="space-y-2 text-xs leading-relaxed text-amber-950 sm:text-sm">
              {resolvedWarningSigns.map((item, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600"
                    aria-hidden="true"
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {timeframe && (
            <div className="mt-4 pt-3 border-t border-amber-200/60 text-xs text-amber-900">
              <span className="font-semibold">Observation window: </span>
              <span>Re-evaluate if symptoms persist past {timeframe}.</span>
            </div>
          )}
        </article>
      </div>

      {/* 3. Action bar & Physician Consultation Link */}
      <footer className="space-y-4 pt-2">
        {onConsultDoctorClick && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs text-slate-600 sm:text-sm text-center sm:text-left">
              Prefer speaking with a professional for reassurance?
            </div>
            <button
              type="button"
              onClick={onConsultDoctorClick}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-800 shadow-xs transition hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-teal-500/20 sm:text-sm"
              style={{
                minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
              }}
            >
              <span>🩺</span>
              <span>Find Nearby Clinic / Doctor</span>
            </button>
          </div>
        )}

        {/* Mandatory Medical Disclaimer (AI_RULES.md §2 rule 8) */}
        <p
          className="text-center text-xs leading-relaxed text-slate-500 border-t border-slate-100 pt-3"
          style={{
            color: COLOR_TOKENS.neutral.textMuted,
          }}
        >
          {DISCLAIMER_TEXT}
        </p>
      </footer>
    </section>
  );
}

export default SelfCareGuidanceCard;
