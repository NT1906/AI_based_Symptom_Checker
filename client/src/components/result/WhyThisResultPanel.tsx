/**
 * @file Contributing-factor explanation panel explaining why conditions were suggested.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-3 · Requirements: FR-24
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 */

import { ChevronDown, ChevronUp, Search } from "lucide-react";
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
      className={`rounded-xl border border-border bg-card p-5 shadow-xs sm:p-6 ${className}`}
    >
      {/* Header and Toggle Button */}
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xl" aria-hidden="true">
              <Search className="size-5" aria-hidden="true" />
            </span>
            <h2
              id="why-result-heading"
              className="text-lg font-bold tracking-tight text-foreground sm:text-xl"
            >
              {title}
            </h2>
          </div>
          <p className="text-xs text-muted-foreground sm:text-sm">
            Contributing factors and symptom patterns that influenced these suggestions.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          aria-expanded={isExpanded}
          aria-controls="why-result-content"
          className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-card px-3 py-1.5 text-xs font-semibold text-muted-foreground transition hover:bg-muted/60 focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <span>{isExpanded ? "Collapse" : "Expand"}</span>
          {isExpanded ? (
                <ChevronUp className="size-3.5" aria-hidden="true" />
              ) : (
                <ChevronDown className="size-3.5" aria-hidden="true" />
              )}
        </button>
      </div>

      {/* Expandable Explanation Details */}
      {isExpanded && (
        <div id="why-result-content" className="mt-5 space-y-4 border-t border-border pt-4">
          {/* Summary of Reported Inputs */}
          {reportedSymptoms.length > 0 && (
            <div className="rounded-xl bg-muted/60 p-3.5 text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">
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
                className="rounded-xl border border-border bg-muted/60 p-4 transition"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-bold text-foreground">
                    {condition.name}
                  </h3>
                  <span className="rounded-full bg-muted/80 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                    {condition.confidence.replace("_", " ")}
                  </span>
                </div>

                {/* Plain-Language Why Rationale (FR-24) */}
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                  <strong className="font-semibold text-foreground">
                    Why suggested:{" "}
                  </strong>
                  {condition.why ||
                    `Based on pattern similarity with reported symptoms such as ${reportedSymptoms.slice(0, 3).join(", ") || "your reported concerns"}.`}
                </p>

                {condition.specialty && (
                  <p className="mt-1 text-[11px] text-primary">
                    Relevant specialty: {condition.specialty}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Safety Disclaimer */}
          <p className="text-[11px] text-muted-foreground">
            These explanations describe statistical pattern similarity and do not constitute a medical diagnosis.
          </p>
        </div>
      )}
    </section>
  );
}
