/**
 * @file Ranked candidate conditions list with qualitative confidence badges and 'why' lines.
 *
 * Implements FR-22 (candidate condition ranking), FR-23 (qualitative confidence badges:
 * Likely, Possible, Less likely; never raw scores or percentages), and DR-01 (informational framing).
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-2 · Requirements: FR-22, FR-23, DR-01
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 */

import { ArrowRight, ChevronDown, ChevronRight, Stethoscope } from "lucide-react";
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
      return "bg-primary/15 text-primary-strong border-primary/40";
    case "POSSIBLE":
      return "bg-warning/15 text-warning-strong border-warning/40";
    case "LESS_LIKELY":
      return "bg-muted text-muted-foreground border-input";
    default:
      return "bg-muted text-muted-foreground border-input";
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
      className="w-full max-w-2xl mx-auto bg-card border border-border rounded-xl shadow-sm overflow-hidden"
    >
      {/* Header Container */}
      <div className="p-6 bg-muted/60 border-b border-border">
        <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
          <Stethoscope className="size-4 shrink-0" aria-hidden="true" /> {title}
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          These are informational considerations based on your reported symptoms. Always consult a
          qualified healthcare professional for evaluation.
        </p>
      </div>

      {/* Conditions Content */}
      <div className="p-6">
        {conditions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm font-medium">{emptyMessage}</p>
            <p className="text-xs mt-1 text-muted-foreground">
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
                  className="p-4 rounded-xl border border-border bg-muted/60 hover:border-primary/25 transition-colors"
                >
                  {/* Top Bar: Rank, Name, Confidence Badge */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-muted-foreground">
                        #{displayRank}
                      </span>
                      <h3 className="font-semibold text-foreground text-base">
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
                    <div className="mt-2.5 flex items-start gap-1.5 text-xs text-muted-foreground leading-relaxed bg-card/70 p-2.5 rounded-lg border border-border">
                      <span className="font-semibold text-primary-strong shrink-0">
                        Why:
                      </span>
                      <span>{item.why}</span>
                    </div>
                  )}

                  {/* Recommended Specialty */}
                  {item.specialty && (
                    <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1.5">
                      <span className="font-medium text-muted-foreground">
                        Recommended Specialty:
                      </span>
                      <span>{item.specialty}</span>
                    </div>
                  )}

                  {/* Optional Metadata Toggle (ICD-10, Description) */}
                  {(item.icd10Code || item.description) && (
                    <div className="mt-3 pt-2.5 border-t border-border">
                      <button
                        type="button"
                        onClick={() => toggleDetails(key)}
                        className="text-xs font-medium text-primary hover:text-primary-strong hover:underline flex items-center gap-1 focus:outline-none focus:ring-1 focus:ring-ring rounded"
                        aria-expanded={isExpanded}
                      >
                        {isExpanded ? (
                        <ChevronDown className="size-3.5" aria-hidden="true" />
                      ) : (
                        <ChevronRight className="size-3.5" aria-hidden="true" />
                      )}
                      <span>{isExpanded ? "Hide details" : "Show details"}</span>
                      </button>

                      {isExpanded && (
                        <div className="mt-2 space-y-1.5 text-xs text-muted-foreground bg-muted/60 p-2.5 rounded-lg">
                          {item.icd10Code && (
                            <div>
                              <span className="font-medium text-muted-foreground">
                                ICD-10 Code:
                              </span>{" "}
                              <code className="text-[11px] bg-muted/60 px-1 py-0.5 rounded text-foreground">
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
                        className="text-xs font-semibold text-primary hover:text-primary-strong hover:underline"
                      >
                        Select for follow-up <ArrowRight className="inline size-3.5 align-[-2px]" aria-hidden="true" />
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
      <footer className="px-6 py-3 bg-muted/80 border-t border-border text-[11px] text-muted-foreground text-center leading-relaxed">
        Conditions are ranked suggestions for informational discussion with a licensed healthcare
        provider, not clinical diagnoses.
      </footer>
    </section>
  );
}

