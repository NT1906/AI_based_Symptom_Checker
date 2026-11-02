/**
 * @file TypeScript domain types and interfaces for candidate condition presentation.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-2 · Requirements: FR-22, FR-23, DR-01
 */

/** Qualitative confidence tier matching backend ConfidenceLabel enum (FR-23, AI_RULES §2.3). */
export type ConfidenceTier = "LIKELY" | "POSSIBLE" | "LESS_LIKELY";

/** Candidate condition item presented to users with non-diagnostic qualitative confidence. */
export interface ConditionItem {
  /** Optional identifier for the condition record. */
  id?: string;
  /** Clinical or plain-language condition title. */
  name: string;
  /** Qualitative confidence tier (Likely, Possible, Less likely; never a raw score). */
  confidence: ConfidenceTier;
  /** Relative rank position (1 = top match). */
  rank?: number;
  /** Plain-language 'why' rationale or contributing factor explanation. */
  why?: string | null;
  /** Recommended healthcare specialty for evaluation. */
  specialty?: string | null;
  /** Standard ICD-10 diagnostic code classification, if available. */
  icd10Code?: string | null;
  /** Brief informational overview of the condition. */
  description?: string | null;
}

/** Props for the ConditionList component. */
export interface ConditionListProps {
  /** Ranked list of candidate conditions. */
  conditions: ConditionItem[];
  /** Optional callback invoked when a condition card is clicked or selected. */
  onSelectCondition?: (condition: ConditionItem) => void;
  /** Custom fallback message displayed when no conditions are present. */
  emptyMessage?: string;
  /** Optional container title overriding the default header. */
  title?: string;
}

