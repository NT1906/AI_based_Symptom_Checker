/**
 * @file Public exports for assessment components.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-1, S2-MAN-1 · Requirements: FR-16, FR-21, FR-03, idea §3
 */

export {
  SymptomConfirmationCard,
  CONFIRMATION_DISCLAIMER_TEXT,
} from "./SymptomConfirmationCard";
export {
  ImageAttach,
  MAX_IMAGE_SIZE_BYTES,
  ALLOWED_IMAGE_TYPES,
  IMAGE_PRIVACY_DISCLAIMER,
  formatFileSize,
} from "./ImageAttach";
export {
  hasVisualSymptoms,
  VISUAL_SYMPTOM_KEYWORDS,
  VISUAL_BODY_SYSTEMS,
} from "./visualSymptoms";
export type {
  VisualSymptomCandidate,
  VisualSymptomInput,
} from "./visualSymptoms";
export { CANONICAL_SYMPTOMS } from "./canonicalSymptoms";
export type {
  ConfirmedSymptom,
  SeverityLevel,
  DurationUnitType,
  SymptomDuration,
  SymptomConfirmationCardProps,
  ImageAttachProps,
} from "./types";
export type { CanonicalSymptomItem } from "./canonicalSymptoms";


