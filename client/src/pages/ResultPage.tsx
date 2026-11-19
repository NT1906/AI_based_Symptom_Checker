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
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-3, S2-NIS-13, S2-NIS-16, S2-NIS-17 · Requirements: DR-01, DR-02, FR-06, FR-15, FR-22, FR-23, FR-24, FR-08, NFR-06
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 */

import React from "react";
import { Lightbulb, Phone, Printer, RotateCcw, TriangleAlert } from "lucide-react";
import { UrgentCareAlert } from "../components/risk/UrgentCareAlert";
import { AppLayout } from "../components/layout/AppLayout";
import { ConditionList } from "../components/result/ConditionList";
import { DoctorReferral } from "../components/result/DoctorReferral";
import { WhyThisResultPanel } from "../components/result/WhyThisResultPanel";
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
  /** Optional subtitle override, e.g. when a past result is shown from history. */
  subtitle?: string;
  /** Optional extra header controls, e.g. a link back to history. */
  headerActions?: React.ReactNode;
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
 * Format a timestamp for the printed result.
 *
 * @param value - ISO timestamp.
 * @returns A local date and time, or the raw value if it cannot be parsed.
 */
function formatPrintDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

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
  subtitle = "Clinical Triage & Candidate Conditions Summary",
  headerActions,
}: ResultPageProps): React.ReactElement {
  const riskLevel: RiskLevel = result.riskLevel || "CONSULT_DOCTOR";
  const riskConfig = getRiskConfig(riskLevel);
  const isUrgent = riskLevel === "URGENT";
  const [urgentAlertDismissed, setUrgentAlertDismissed] = React.useState(false);

  const conditions = result.conditions || [];
  const guidance = result.guidance;
  const referral = result.referral;

  const handleStartOver = () => {
    if (onStartNewAssessment) {
      onStartNewAssessment();
    }
  };

  return (
    <AppLayout
      title={title}
      subtitle={subtitle}
      emergencyNumber={emergencyNumber}
      headerActions={headerActions}
      showStartOver={Boolean(onStartNewAssessment)}
      onStartOver={handleStartOver}
    >
      {isUrgent && !urgentAlertDismissed && (
        <UrgentCareAlert onDismiss={() => setUrgentAlertDismissed(true)} />
      )}
      <div className="space-y-8 pb-12">
        {/* Print-only heading so a saved PDF says what it is (S2-NIS-17, #314). */}
        <div className="hidden border-b border-input pb-3 print:block">
          <p className="text-lg font-bold text-foreground">
            AI-Based Symptom Checker · Assessment result
          </p>
          <p className="text-xs text-muted-foreground">
            {result.completedAt
              ? `Completed ${formatPrintDate(result.completedAt)} · `
              : ""}
            Informational triage aid, not a medical diagnosis.
          </p>
        </div>

        {/* Save or print this result (S2-NIS-17, #314). */}
        <div className="flex justify-end print:hidden">
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex min-h-[44px] items-center gap-2 rounded-xl border border-primary/60 bg-card px-4 py-2 text-sm font-semibold text-primary-strong shadow-xs transition hover:bg-primary/10 focus:outline-none focus:ring-4 focus:ring-ring"
          >
            <Printer className="size-4 shrink-0" aria-hidden="true" />
            <span>Save as PDF / Print</span>
          </button>
        </div>

        {/* 1. Triage Risk Level Banner */}
        <section
          aria-labelledby="triage-status-heading"
          className={[
            "rounded-xl border p-5 shadow-sm transition sm:p-6",
            isUrgent
              ? "border-danger/40 bg-danger/5 text-danger-strong"
              : riskLevel === "CONSULT_DOCTOR"
                ? "border-warning/40 bg-warning/5 text-warning-strong"
                : "border-success/40 bg-success/5 text-success-strong",
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
              className="mt-5 rounded-xl border border-danger/40 bg-card p-4 text-danger-strong shadow-sm sm:p-5"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-bold uppercase tracking-wide text-danger-strong">
                    <TriangleAlert className="inline size-4 align-[-3px]" aria-hidden="true" /> Immediate Action Required
                  </p>
                  <p className="text-xs leading-relaxed text-muted-foreground sm:text-sm">
                    Your reported symptoms indicate a potential high-risk condition.
                    Do not attempt to drive yourself. Alert someone nearby and call
                    emergency services immediately.
                  </p>
                </div>
                <a
                  href={`tel:${emergencyNumber}`}
                  className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-2 rounded-xl bg-danger px-5 py-3 text-sm font-bold text-danger-foreground shadow-md transition hover:bg-danger/90 focus:outline-none focus:ring-4 focus:ring-danger/40"
                  aria-label={`Call emergency number ${emergencyNumber} now`}
                >
                  <span aria-hidden="true" className="text-lg">
                    <Phone className="size-4" aria-hidden="true" />
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
              className="text-lg font-bold tracking-tight text-foreground sm:text-xl"
            >
              Candidate Conditions
            </h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
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

          {/* Explanation panel for contributing factors (FR-24) */}
          {conditions.length > 0 && (
            <WhyThisResultPanel conditions={conditions} />
          )}
        </section>

        {/* 3. Clinical Guidance Slot (Self-Care & Warning Signs) */}
        {guidance && (
          <section
            aria-labelledby="guidance-section-heading"
            className="space-y-4 rounded-xl border border-border bg-card p-5 shadow-xs sm:p-6"
          >
            <div className="space-y-1 border-b border-border pb-3">
              <h2
                id="guidance-section-heading"
                className="text-lg font-bold tracking-tight text-foreground sm:text-xl"
              >
                Self-Care &amp; Guidance
              </h2>
              {guidance.summary && (
                <p className="text-xs text-muted-foreground sm:text-sm">
                  {guidance.summary}
                </p>
              )}
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              {/* Actionable Self-Care Advice */}
              {guidance.selfCareAdvice && guidance.selfCareAdvice.length > 0 && (
                <div className="space-y-2.5">
                  <h3 className="flex items-center gap-1.5 text-sm font-bold text-foreground">
                    <Lightbulb className="size-4 shrink-0" aria-hidden="true" />
                    <span>{guidance.stepsHeading ?? "General Self-Care Steps"}</span>
                  </h3>
                  <ul className="space-y-2 text-xs leading-relaxed text-muted-foreground sm:text-sm">
                    {guidance.selfCareAdvice.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span
                          className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
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
                <div className="space-y-2.5 rounded-xl border border-warning/25 bg-warning/5 p-3.5 sm:p-4">
                  <h3 className="flex items-center gap-1.5 text-sm font-bold text-warning-strong">
                    <TriangleAlert className="size-4 shrink-0" aria-hidden="true" />
                    <span>When to Seek Emergency Care</span>
                  </h3>
                  <ul className="space-y-1.5 text-xs leading-relaxed text-warning-strong sm:text-sm">
                    {guidance.warningSigns.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span
                          className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-warning"
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
              <div className="rounded-lg bg-muted/60 px-3.5 py-2.5 text-xs text-muted-foreground sm:text-sm">
                <span className="font-semibold text-foreground">
                  Recommended Timeframe:{" "}
                </span>
                <span>{guidance.timeframe}</span>
              </div>
            )}
          </section>
        )}

        {/* 4. Specialist Referral Slot (FR-08: External Map Search) */}
        {referral && (
          <DoctorReferral
            referral={referral}
            title="Recommended Specialist Evaluation"
          />
        )}

        {/* 4b. Limits of this result, as stated by the server (S2-NIS-13) */}
        {result.limitations && result.limitations.length > 0 && (
          <section
            aria-labelledby="limitations-heading"
            className="rounded-xl border border-border bg-card p-5 text-sm text-muted-foreground sm:p-6"
          >
            <h2
              id="limitations-heading"
              className="text-base font-bold text-foreground"
            >
              About this result
            </h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {result.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        {/* 5. Persistent Medical Disclaimer Card (DR-01) */}
        <aside
          role="note"
          aria-label="Medical disclaimer"
          className="rounded-xl border border-primary/25 bg-primary/5 p-4 text-xs text-muted-foreground sm:p-5 sm:text-sm"
        >
          <div className="flex items-start gap-3">
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground"
              aria-hidden="true"
            >
              i
            </span>
            <div className="space-y-1">
              <p className="font-bold text-foreground">
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
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-input bg-card px-6 py-3 text-sm font-semibold text-foreground shadow-xs transition hover:bg-muted/60 focus:outline-none focus:ring-4 focus:ring-ring"
            >
              <RotateCcw className="size-4 shrink-0" aria-hidden="true" />
              <span>Start New Assessment</span>
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

export default ResultPage;
