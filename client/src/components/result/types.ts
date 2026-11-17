/**
 * @file TypeScript domain types and interfaces for candidate condition presentation and triage results.
 * Owner: Mann (Frontend + Deployment · Testing) · Tasks: S1-MAN-2, S1-MAN-3 · Requirements: FR-06, FR-15, FR-22, FR-23, DR-01, DR-02
 */

/** Qualitative confidence tier matching backend ConfidenceLabel enum (FR-23, AI_RULES §2.3). */
export type ConfidenceTier = "LIKELY" | "POSSIBLE" | "LESS_LIKELY";

/** Deterministic clinical triage risk levels (FR-06, FR-15, DR-02). */
export type RiskLevel = "SELF_CARE" | "CONSULT_DOCTOR" | "URGENT";

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

/** Clinical guidance information covering self-care recommendations and warning signs. */
export interface TriageGuidance {
  /** Summary or headline for the guidance section. */
  summary?: string;
  /** Actionable self-care recommendations (rest, fluids, symptom monitoring). */
  selfCareAdvice?: string[];
  /** Red-flag warnings or symptoms indicating need for emergency evaluation. */
  warningSigns?: string[];
  /** Recommended timeframe for seeking medical evaluation (e.g. within 24-48 hours). */
  timeframe?: string;
}

/** Supported external map search providers (FR-08, idea §9). */
export type MapProvider = "google" | "osm" | "apple";

/** External doctor or clinic referral recommendation based on medical specialty. */
export interface ReferralInfo {
  /** Primary recommended medical specialty. */
  specialty: string;
  /** Additional suggested specialties if applicable. */
  secondarySpecialties?: string[];
  /** Suggested external map query string (e.g. "General Physician near me"). */
  mapQuery?: string;
}

/** Props for the DoctorReferral component (FR-08, idea §9, S2-MAN-2). */
export interface DoctorReferralProps {
  /** Referral configuration bundle or primary specialty name. */
  referral?: ReferralInfo | null;
  /** Direct primary medical specialty override (e.g. "General Physician", "Dermatologist"). */
  specialty?: string | null;
  /** Secondary or complementary specialties. */
  secondarySpecialties?: string[];
  /** Custom map search query override (defaults to "<specialty> near me"). */
  mapQuery?: string | null;
  /** Preferred external map provider (defaults to "google"). */
  provider?: MapProvider;
  /** Optional location hint (e.g. city or postal code). */
  location?: string | null;
  /** Custom section title. */
  title?: string;
  /** Optional callback invoked when the user clicks an external map search link. */
  onReferralClick?: (specialty: string, targetUrl: string) => void;
  /** Optional container CSS class name. */
  className?: string;
}

/** Complete assessment result data bundle composed by ResultPage. */
export interface AssessmentResultData {
  /** Assessment unique identifier, if persisted. */
  assessmentId?: string;
  /** Deterministic risk tier. */
  riskLevel: RiskLevel;
  /** Ranked list of candidate conditions. */
  conditions: ConditionItem[];
  /** Clinical triage guidance and self-care directions. */
  guidance?: TriageGuidance;
  /** Specialty referral recommendations. */
  referral?: ReferralInfo;
  /** ISO timestamp of when the assessment result was generated. */
  completedAt?: string;
}
