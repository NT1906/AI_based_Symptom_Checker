/**
 * @file Public exports for result triage components.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-2 · Requirements: FR-22, FR-23, DR-01
 */

export {
  ConditionList,
  getConfidenceLabel,
  getConfidenceBadgeClass,
} from "./ConditionList";
export type {
  ConditionItem,
  ConfidenceTier,
  ConditionListProps,
} from "./types";
