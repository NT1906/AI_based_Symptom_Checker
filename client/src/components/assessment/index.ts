/**
 * @file Public exports for assessment components.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-1 · Requirements: FR-16, FR-21, FR-03
 */

export {
  SymptomConfirmationCard,
  CONFIRMATION_DISCLAIMER_TEXT,
} from "./SymptomConfirmationCard";
export { CANONICAL_SYMPTOMS } from "./canonicalSymptoms";
export type {
  ConfirmedSymptom,
  SeverityLevel,
  DurationUnitType,
  SymptomDuration,
  SymptomConfirmationCardProps,
} from "./types";
export type { CanonicalSymptomItem } from "./canonicalSymptoms";

