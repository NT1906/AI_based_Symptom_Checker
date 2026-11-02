/**
 * @file Ranked candidate conditions list with qualitative confidence badges and 'why' lines.
 *
 * Implements FR-22 (candidate condition ranking), FR-23 (qualitative confidence badges:
 * Likely, Possible, Less likely; never raw scores or percentages), and DR-01 (informational framing).
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-2 · Requirements: FR-22, FR-23, DR-01
 */

import React, { useState } from "react";
import type { ConditionListProps, ConfidenceTier } from "./types";

/**
 * Maps a technical ConfidenceTier to a human-readable display label.
 *
 * @param confidence - Qualitative confidence tier.
 * @returns User-facing plain-language label string.
 */
export function getConfidenceLabel(confidence: ConfidenceTier): string {
  switch (confidence) {
    case "LIKELY":
      return "Likely";
    case "POSSIBLE":
      return "Possible";
    case "LESS_LIKELY":
      return "Less likely";
    default:
      return "Possible";
  }
}

/**
 * Returns accessible styling classes for qualitative confidence badges.
 *
 * @param confidence - Qualitative confidence tier.
 * @returns Tailwind CSS class string.
 */
export function getConfidenceBadgeClass(confidence: ConfidenceTier): string {
  switch (confidence) {
    case "LIKELY":
      return "bg-teal-100 text-teal-800 border-teal-300 dark:bg-teal-950 dark:text-teal-200 dark:border-teal-800";
    case "POSSIBLE":
      return "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800";
    case "LESS_LIKELY":
      return "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
    default:
      return "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
  }
}

/**
 * ConditionList component rendering ranked candidate conditions and 'why' rationale.
 *
 * @param props - Configuration and list items props.
 * @returns Rendered condition cards list.
 */
export function ConditionList({
  conditions,
  onSelectCondition,
  emptyMessage = "No specific conditions identified for the reported symptoms.",
  title = "Possible Conditions",
}: ConditionListProps): React.ReactElement {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  /**
   * Toggles detail accordion for a specific condition.
   *
   * @param key - Condition item unique key.
   */
  const toggleDetails = (key: string) => {
    setExpandedId((prev) => (prev === key ? null : key));
  };

  return (
    <section
      aria-label="Possible Conditions"
      className="w-full max-w-2xl mx-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden"
    >
      {/* Header Container */}
      <div className="p-6 bg-slate-50/80 dark:bg-slate-950/40 border-b border-slate-200 dark:border-slate-800">
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <span aria-hidden="true">🩺</span> {title}
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
          These are informational considerations based on your reported symptoms. Always consult a
          qualified healthcare professional for evaluation.
        </p>
      </div>

      {/* Conditions Content */}
      <div className="p-6">
        {conditions.length === 0 ? (
          <div className="text-center py-8 text-slate-500 dark:text-slate-400">
            <p className="text-sm font-medium">{emptyMessage}</p>
            <p className="text-xs mt-1 text-slate-400 dark:text-slate-500">
              A general physician can help evaluate non-specific or evolving symptoms.
            </p>
          </div>
        ) : (
          <ol className="space-y-4" aria-label="Ranked candidate conditions">
            {conditions.map((item, index) => {
              const displayRank = item.rank ?? index + 1;
              const key = item.id || `cond-${item.name}-${index}`;
              const label = getConfidenceLabel(item.confidence);
              const badgeClass = getConfidenceBadgeClass(item.confidence);
              const isExpanded = expandedId === key;

              return (
                <li
                  key={key}
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 hover:border-teal-200 dark:hover:border-teal-900/60 transition-colors"
                >
                  {/* Top Bar: Rank, Name, Confidence Badge */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-slate-400 dark:text-slate-500">
                        #{displayRank}
                      </span>
                      <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-base">
                        {item.name}
                      </h3>
                    </div>

                    <span
                      aria-label={`Likelihood: ${label}`}
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border shrink-0 ${badgeClass}`}
                    >
                      {label}
                    </span>
                  </div>

                  {/* "Why" Explanation Line (FR-22, FR-24) */}
                  {item.why && (
                    <div className="mt-2.5 flex items-start gap-1.5 text-xs text-slate-700 dark:text-slate-300 leading-relaxed bg-white/70 dark:bg-slate-900/50 p-2.5 rounded-lg border border-slate-200/60 dark:border-slate-700/60">
                      <span className="font-semibold text-teal-800 dark:text-teal-300 shrink-0">
                        Why:
                      </span>
                      <span>{item.why}</span>
                    </div>
                  )}

                  {/* Recommended Specialty */}
                  {item.specialty && (
                    <div className="mt-2 text-xs text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        Recommended Specialty:
                      </span>
                      <span>{item.specialty}</span>
                    </div>
                  )}

                  {/* Optional Metadata Toggle (ICD-10, Description) */}
                  {(item.icd10Code || item.description) && (
                    <div className="mt-3 pt-2.5 border-t border-slate-200/70 dark:border-slate-700/70">
                      <button
                        type="button"
                        onClick={() => toggleDetails(key)}
                        className="text-xs font-medium text-teal-700 dark:text-teal-400 hover:text-teal-800 dark:hover:text-teal-300 hover:underline flex items-center gap-1 focus:outline-none focus:ring-1 focus:ring-teal-600 rounded"
                        aria-expanded={isExpanded}
                      >
                        <span>{isExpanded ? "▾ Hide details" : "▸ Show details"}</span>
                      </button>

                      {isExpanded && (
                        <div className="mt-2 space-y-1.5 text-xs text-slate-600 dark:text-slate-400 bg-slate-100/60 dark:bg-slate-900/40 p-2.5 rounded-lg">
                          {item.icd10Code && (
                            <div>
                              <span className="font-medium text-slate-700 dark:text-slate-300">
                                ICD-10 Code:
                              </span>{" "}
                              <code className="text-[11px] bg-slate-200/60 dark:bg-slate-800 px-1 py-0.5 rounded text-slate-800 dark:text-slate-200">
                                {item.icd10Code}
                              </code>
                            </div>
                          )}
                          {item.description && (
                            <p className="leading-relaxed mt-1">{item.description}</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Interactive Selection Trigger (if provided) */}
                  {onSelectCondition && (
                    <div className="mt-3 flex justify-end">
                      <button
                        type="button"
                        onClick={() => onSelectCondition(item)}
                        className="text-xs font-semibold text-teal-700 dark:text-teal-400 hover:text-teal-800 hover:underline"
                      >
                        Select for follow-up →
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </div>

      {/* Persistent Informational Footer Note (DR-01) */}
      <footer className="px-6 py-3 bg-slate-100/80 dark:bg-slate-950/60 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 text-center leading-relaxed">
        Conditions are ranked suggestions for informational discussion with a licensed healthcare
        provider, not clinical diagnoses.
      </footer>
    </section>
  );
}

