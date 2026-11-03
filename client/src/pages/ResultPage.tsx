/**
 * @file Comprehensive assessment result and triage guidance screen.
 *
 * Composes ConditionList, RiskBadge, guidance slot, specialist referral, and
 * persistent medical disclaimer.
 *
 * Implements:
 * - DR-01: Non-diagnostic informational framing and persistent medical disclaimer.
 * - DR-02 / FR-06 / FR-15: Deterministic triage risk tiering with 112 emergency prioritization.
 * - FR-22 / FR-23: Qualitative confidence rankings for candidate conditions.
 * - FR-24: Plain-language 'why' rationale explanations.
 * - FR-08: External map search link for recommended medical specialty (no doctor data stored).
 * - NFR-06: WCAG 2.1 AA accessible landmarks, contrast, and focus states.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-3 · Requirements: DR-01, DR-02, FR-06, FR-15, FR-22, FR-23, FR-24, FR-08, NFR-06
 */

import React from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { ConditionList } from "../components/result/ConditionList";
import { RiskBadge, getRiskConfig } from "../components/result/RiskBadge";
import type {
  AssessmentResultData,
  ConditionItem,
  RiskLevel,
} from "../components/result/types";

/** Props for the ResultPage component. */
export interface ResultPageProps {
  /** Assessment result data bundle containing risk tier, conditions, and guidance. */
  result?: AssessmentResultData;
  /** Callback triggered when user requests to start a new assessment session. */
  onStartNewAssessment?: () => void;
  /** National emergency hotline number (defaults to "112"). */
  emergencyNumber?: string;
  /** Custom header title override for the application shell. */
  title?: string;
  /** Optional callback invoked when a candidate condition item is selected. */
  onSelectCondition?: (condition: ConditionItem) => void;
}

/** Standard default result dataset used when no external result is injected. */
export const DEFAULT_RESULT_DATA: AssessmentResultData = {
  riskLevel: "CONSULT_DOCTOR",
  conditions: [
    {
      id: "cond-1",
      name: "Migraine with Photophobia",
      confidence: "LIKELY",
      rank: 1,
      why: "Matches reported unilateral throbbing pain, nausea, and light sensitivity lasting > 24 hours.",
      specialty: "Neurologist / General Physician",
      icd10Code: "G43.909",
      description: "A recurring primary headache disorder characterized by moderate to severe throbbing pain.",
    },
    {
      id: "cond-2",
      name: "Tension-type Headache",
      confidence: "POSSIBLE",
      rank: 2,
      why: "Common cause of diffuse head discomfort; partially overlaps with stress and fatigue indicators.",
      specialty: "General Physician",
      icd10Code: "G44.209",
      description: "A mild to moderate band-like head pressure often triggered by muscle contraction or strain.",
    },
    {
      id: "cond-3",
      name: "Sinusitis",
      confidence: "LESS_LIKELY",
      rank: 3,
      why: "Potential overlap with frontal pressure, although primary nasal symptoms were not reported.",
      specialty: "ENT Specialist / General Physician",
      icd10Code: "J01.90",
      description: "Inflammation or swelling of the tissue lining the sinuses.",
    },
  ],
  guidance: {
    summary: "Clinical triage assessment based on confirmed symptom pattern.",
    selfCareAdvice: [
      "Rest in a quiet, dark environment to reduce sensory stimulation.",
      "Stay well-hydrated and avoid skipping meals or sudden caffeine shifts.",
      "Apply a cool cloth or gentle cold pack across the forehead or neck.",
      "Keep a symptom log recording onset, severity, triggers, and duration.",
    ],
    warningSigns: [
      "Sudden, explosive 'thunderclap' headache reaching peak intensity in seconds.",
      "Fever accompanied by a stiff neck, confusion, or sensitivity to light.",
      "Neurological symptoms such as slurred speech, limb weakness, or vision changes.",
      "Headache following recent head trauma or progressive worsening over days.",
    ],
    timeframe: "Schedule an evaluation with a general physician within 24 to 48 hours.",
  },
  referral: {
    specialty: "General Physician",
    secondarySpecialties: ["Neurologist"],
    mapQuery: "General Physician near me",
  },
};

/**
 * Result page composing ConditionList, RiskBadge, guidance slot, and persistent disclaimer.
 *
 * @param props - Component properties.
 * @returns Rendered comprehensive result page.
 */
export function ResultPage({
  result = DEFAULT_RESULT_DATA,
  onStartNewAssessment,
  emergencyNumber = "112",
  title = "Assessment Result",
  onSelectCondition,
}: ResultPageProps): React.ReactElement {
  const riskLevel: RiskLevel = result.riskLevel || "CONSULT_DOCTOR";
  const riskConfig = getRiskConfig(riskLevel);
  const isUrgent = riskLevel === "URGENT";

  const conditions = result.conditions || [];
  const guidance = result.guidance;
  const referral = result.referral;

  // External map query link ensuring zero doctor data is stored locally (Mann's module boundary)
  const mapSearchQuery =
    referral?.mapQuery || `${referral?.specialty || "Doctor"} near me`;
  const mapSearchUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    mapSearchQuery,
  )}`;

  const handleStartOver = () => {
    if (onStartNewAssessment) {
      onStartNewAssessment();
    }
  };

  return (
    <AppLayout
      title={title}
      subtitle="Clinical Triage & Candidate Conditions Summary"
      emergencyNumber={emergencyNumber}
      showStartOver={Boolean(onStartNewAssessment)}
      onStartOver={handleStartOver}
    >
      <div className="space-y-8 pb-12">
        {/* 1. Triage Risk Level Banner */}
        <section
          aria-labelledby="triage-status-heading"
          className={[
            "rounded-2xl border p-5 shadow-sm transition sm:p-6",
            isUrgent
              ? "border-rose-300 bg-rose-50/90 text-rose-950 dark:border-rose-900 dark:bg-rose-950/60 dark:text-rose-100"
              : riskLevel === "CONSULT_DOCTOR"
                ? "border-amber-300 bg-amber-50/80 text-amber-950 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-100"
                : "border-emerald-300 bg-emerald-50/80 text-emerald-950 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100",
          ].join(" ")}
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2.5">
                <RiskBadge level={riskLevel} />
                <span className="text-xs font-semibold uppercase tracking-wider opacity-75">
                  Deterministic Triage
                </span>
              </div>
              <h2
                id="triage-status-heading"
                className="text-xl font-bold tracking-tight sm:text-2xl"
              >
                {isUrgent
                  ? "Urgent Medical Care Required"
                  : riskLevel === "CONSULT_DOCTOR"
                    ? "Medical Consultation Recommended"
                    : "Self-Care Management Recommended"}
              </h2>
              <p className="max-w-3xl text-sm leading-relaxed opacity-90 sm:text-base">
                {riskConfig.description}
              </p>
            </div>
          </div>

          {/* High Priority Emergency Callout on URGENT tier (DR-02, FR-06) */}
          {isUrgent && (
            <div
              role="alert"
              className="mt-5 rounded-xl border border-rose-300 bg-white p-4 text-rose-900 shadow-sm sm:p-5 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-100"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-bold uppercase tracking-wide text-rose-700 dark:text-rose-300">
                    ⚠️ Immediate Action Required
                  </p>
                  <p className="text-xs leading-relaxed text-slate-700 sm:text-sm dark:text-slate-200">
                    Your reported symptoms indicate a potential high-risk condition.
                    Do not attempt to drive yourself. Alert someone nearby and call
                    emergency services immediately.
                  </p>
                </div>
                <a
                  href={`tel:${emergencyNumber}`}
                  className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-2 rounded-xl bg-rose-600 px-5 py-3 text-sm font-bold text-white shadow-md transition hover:bg-rose-700 focus:outline-none focus:ring-4 focus:ring-rose-500/50"
                  aria-label={`Call emergency number ${emergencyNumber} now`}
                >
                  <span aria-hidden="true" className="text-lg">
                    📞
                  </span>
                  <span>Call {emergencyNumber} Now</span>
                </a>
              </div>
            </div>
          )}
        </section>

        {/* 2. Candidate Conditions List (Composes ConditionList) */}
        <section aria-labelledby="conditions-section-heading" className="space-y-3">
          <div className="space-y-1">
            <h2
              id="conditions-section-heading"
              className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl dark:text-slate-100"
            >
              Candidate Conditions
            </h2>
            <p className="text-xs text-slate-600 sm:text-sm dark:text-slate-400">
              Ranked in order of symptom pattern similarity. Confidence is expressed
              qualitatively (Likely, Possible, Less likely); raw scores are never
              provided. This is not a diagnosis.
            </p>
          </div>

          <ConditionList
            conditions={conditions}
            onSelectCondition={onSelectCondition}
            emptyMessage="No matching conditions identified for the provided symptoms. Please consult a qualified physician for a clinical evaluation."
          />
        </section>

        {/* 3. Clinical Guidance Slot (Self-Care & Warning Signs) */}
        {guidance && (
          <section
            aria-labelledby="guidance-section-heading"
            className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-xs sm:p-6 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="space-y-1 border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2
                id="guidance-section-heading"
                className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl dark:text-slate-100"
              >
                Self-Care &amp; Guidance
              </h2>
              {guidance.summary && (
                <p className="text-xs text-slate-600 sm:text-sm dark:text-slate-400">
                  {guidance.summary}
                </p>
              )}
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              {/* Actionable Self-Care Advice */}
              {guidance.selfCareAdvice && guidance.selfCareAdvice.length > 0 && (
                <div className="space-y-2.5">
                  <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-900 dark:text-slate-100">
                    <span aria-hidden="true">💡</span>
                    <span>General Self-Care Steps</span>
                  </h3>
                  <ul className="space-y-2 text-xs leading-relaxed text-slate-700 sm:text-sm dark:text-slate-300">
                    {guidance.selfCareAdvice.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span
                          className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600 dark:bg-teal-400"
                          aria-hidden="true"
                        />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Warning Signs / Red Flags */}
              {guidance.warningSigns && guidance.warningSigns.length > 0 && (
                <div className="space-y-2.5 rounded-xl border border-amber-200 bg-amber-50/50 p-3.5 sm:p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
                  <h3 className="flex items-center gap-1.5 text-sm font-bold text-amber-900 dark:text-amber-200">
                    <span aria-hidden="true">⚠️</span>
                    <span>When to Seek Emergency Care</span>
                  </h3>
                  <ul className="space-y-1.5 text-xs leading-relaxed text-amber-950 sm:text-sm dark:text-amber-200/90">
                    {guidance.warningSigns.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span
                          className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600 dark:bg-amber-400"
                          aria-hidden="true"
                        />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Timeframe Direction */}
            {guidance.timeframe && (
              <div className="rounded-lg bg-slate-50 px-3.5 py-2.5 text-xs text-slate-700 sm:text-sm dark:bg-slate-800/60 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-slate-100">
                  Recommended Timeframe:{" "}
                </span>
                <span>{guidance.timeframe}</span>
              </div>
            )}
          </section>
        )}

        {/* 4. Specialist Referral Slot (FR-08: External Map Search) */}
        {referral && (
          <section
            aria-labelledby="referral-section-heading"
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs sm:p-6 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <h2
                  id="referral-section-heading"
                  className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl dark:text-slate-100"
                >
                  Recommended Specialist Evaluation
                </h2>
                <p className="text-xs text-slate-600 sm:text-sm dark:text-slate-400">
                  Based on candidate conditions, clinical assessment suggests consulting a{" "}
                  <strong className="text-teal-700 dark:text-teal-400">
                    {referral.specialty}
                  </strong>
                  .
                </p>
                {referral.secondarySpecialties && referral.secondarySpecialties.length > 0 && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Other relevant specialties: {referral.secondarySpecialties.join(", ")}
                  </p>
                )}
              </div>

              <div className="flex flex-col gap-1 sm:items-end">
                <a
                  href={mapSearchUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-xs transition hover:bg-teal-700 focus:outline-none focus:ring-4 focus:ring-teal-500/40"
                  aria-label={`Find a ${referral.specialty} near you on external map`}
                >
                  <span aria-hidden="true">🗺️</span>
                  <span>Find a {referral.specialty} Near Me</span>
                </a>
                <span className="text-[11px] text-slate-400">
                  Opens external map search. No doctor or personal data is stored.
                </span>
              </div>
            </div>
          </section>
        )}

        {/* 5. Persistent Medical Disclaimer Card (DR-01) */}
        <aside
          role="note"
          aria-label="Medical disclaimer"
          className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-slate-700 sm:p-5 sm:text-sm dark:border-teal-900 dark:bg-teal-950/40 dark:text-slate-300"
        >
          <div className="flex items-start gap-3">
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-teal-700 text-xs font-bold text-white"
              aria-hidden="true"
            >
              i
            </span>
            <div className="space-y-1">
              <p className="font-bold text-slate-900 dark:text-slate-100">
                Non-Diagnostic Medical Notice (DR-01)
              </p>
              <p className="leading-relaxed">
                This is not a medical diagnosis. Always consult a qualified
                healthcare professional for medical concerns. This application is
                an informational triage aid and does not replace clinical judgment
                or provide a treatment plan. If you think you may be experiencing a
                life-threatening medical emergency, call emergency services ({emergencyNumber})
                immediately.
              </p>
            </div>
          </div>
        </aside>

        {/* 6. Primary Action Slot: Start New Assessment */}
        {onStartNewAssessment && (
          <div className="flex justify-center pt-2">
            <button
              type="button"
              onClick={handleStartOver}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-800 shadow-xs transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <span aria-hidden="true">🔄</span>
              <span>Start New Assessment</span>
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

export default ResultPage;
