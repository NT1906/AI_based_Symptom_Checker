/**
 * @file Contributing-factor explanation panel explaining why conditions were suggested.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-3 · Requirements: FR-24
 */

import { useState } from "react";
import type { ConditionItem } from "./types";

/** Props for the WhyThisResultPanel component (FR-24). */
export interface WhyThisResultPanelProps {
  /** Candidate conditions presented to the user. */
  conditions: ConditionItem[];
  /** Confirmed symptoms reported by user. */
  reportedSymptoms?: string[];
  /** Whether the panel starts expanded. */
  defaultExpanded?: boolean;
  /** Section heading title override. */
  title?: string;
  /** Custom container styling classes. */
  className?: string;
}

/**
 * Accessible contributing-factor explanation panel.
 *
 * Explains to users *why* specific conditions were suggested and how their
 * reported symptoms influenced the qualitative confidence ranking (FR-24).
 * Uses accessible disclosure regions and non-diagnostic framing (DR-01).
 *
 * @param props Conditions list, reported symptoms, and expansion controls.
 * @returns Expandable explanation panel.
 */
export function WhyThisResultPanel({
  conditions,
  reportedSymptoms = [],
  defaultExpanded = true,
  title = "Why Was This Result Suggested?",
  className = "",
}: WhyThisResultPanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!conditions || conditions.length === 0) {
    return null;
  }

  return (
    <section
      aria-labelledby="why-result-heading"
      className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-xs sm:p-6 dark:border-slate-800 dark:bg-slate-900 ${className}`}
    >
      {/* Header and Toggle Button */}
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xl" aria-hidden="true">
              🔍
            </span>
            <h2
              id="why-result-heading"
              className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl dark:text-slate-100"
            >
              {title}
            </h2>
          </div>
          <p className="text-xs text-slate-600 sm:text-sm dark:text-slate-400">
            Contributing factors and symptom patterns that influenced these suggestions.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          aria-expanded={isExpanded}
          aria-controls="why-result-content"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
        >
          <span>{isExpanded ? "Collapse" : "Expand"}</span>
          <span aria-hidden="true">{isExpanded ? "▲" : "▼"}</span>
        </button>
      </div>

      {/* Expandable Explanation Details */}
      {isExpanded && (
        <div id="why-result-content" className="mt-5 space-y-4 border-t border-slate-100 pt-4 dark:border-slate-800">
          {/* Summary of Reported Inputs */}
          {reportedSymptoms.length > 0 && (
            <div className="rounded-xl bg-slate-50 p-3.5 text-xs text-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                Symptoms evaluated from your input:{" "}
              </span>
              <span>{reportedSymptoms.join(", ")}</span>
            </div>
          )}

          {/* Per-Condition Explanation Cards */}
          <div className="space-y-3">
            {conditions.map((condition) => (
              <div
                key={condition.id || condition.name}
                className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 transition dark:border-slate-800 dark:bg-slate-800/30"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {condition.name}
                  </h3>
                  <span className="rounded-full bg-slate-200/80 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                    {condition.confidence.replace("_", " ")}
                  </span>
                </div>

                {/* Plain-Language Why Rationale (FR-24) */}
                <p className="mt-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                  <strong className="font-semibold text-slate-900 dark:text-slate-100">
                    Why suggested:{" "}
                  </strong>
                  {condition.why ||
                    `Based on pattern similarity with reported symptoms such as ${reportedSymptoms.slice(0, 3).join(", ") || "your reported concerns"}.`}
                </p>

                {condition.specialty && (
                  <p className="mt-1 text-[11px] text-teal-700 dark:text-teal-400">
                    Relevant specialty: {condition.specialty}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Safety Disclaimer */}
          <p className="text-[11px] text-slate-400 dark:text-slate-500">
            These explanations describe statistical pattern similarity and do not constitute a medical diagnosis.
          </p>
        </div>
      )}
    </section>
  );
}
