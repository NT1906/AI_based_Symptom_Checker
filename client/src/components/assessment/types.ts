/**
 * @file TypeScript domain types and interfaces for symptom review and confirmation.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-1 · Requirements: FR-16, FR-21, FR-03
 */

import type { VisualSymptomInput } from "./visualSymptoms";

/** Clinical severity classifications matching the backend severity schema. */
export type SeverityLevel = "MILD" | "MODERATE" | "SEVERE" | "UNKNOWN";

/** Units for expressing symptom duration lengths. */
export type DurationUnitType = "HOUR" | "DAY" | "WEEK" | "MONTH" | "YEAR";

/** Structured duration of a symptom. */
export interface SymptomDuration {
  /** Numerical quantity of duration units elapsed. */
  value: number;
  /** Duration unit of measure. */
  unit: DurationUnitType;
}

/** Confirmed or extracted symptom presented for user review and editing. */
export interface ConfirmedSymptom {
  /** Unique identifier for the symptom item. */
  id: string;
  /** Normalized or canonical symptom name. */
  name: string;
  /** Clinical severity level. */
  severity: SeverityLevel;
  /** Structured duration or null if unknown. */
  duration?: SymptomDuration | null;
  /** Anatomical body location or null if systemic. */
  bodyLocation?: string | null;
  /** Provenance of the symptom record. */
  source?: "USER" | "AI_EXTRACTED" | "USER_CONFIRMED" | "USER_CORRECTED";
}

/** Props for the SymptomConfirmationCard component. */
export interface SymptomConfirmationCardProps {
  /** List of extracted symptoms requiring user confirmation. */
  initialSymptoms: ConfirmedSymptom[];
  /** Callback invoked when user confirms verified symptoms to trigger analysis. */
  onConfirm: (symptoms: ConfirmedSymptom[]) => void;
  /** Optional callback invoked if user cancels or navigates back to chat. */
  onCancel?: () => void;
  /** Whether analysis submission is currently in progress. */
  isSubmitting?: boolean;
}

/** Props for the ImageAttach component (idea §3, S2-MAN-1). */
export interface ImageAttachProps {
  /** Symptoms or message text evaluated to determine if visual symptoms are present. */
  symptoms?: VisualSymptomInput;
  /** Force showing the component even if visual symptoms were not detected. */
  forceShow?: boolean;
  /** Currently selected file, if managed externally. */
  selectedFile?: File | null;
  /** Callback when a valid photo is selected or removed. */
  onImageSelect: (file: File | null) => void;
  /** Callback when validation or file read error occurs. */
  onError?: (error: string | null) => void;
  /** Whether the attachment controls are disabled. */
  disabled?: boolean;
  /** Optional container CSS class name. */
  className?: string;
}


