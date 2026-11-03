/**
 * @file Public exports for result triage components.
 * Owner: Mann (Frontend + Deployment · Testing) · Tasks: S1-MAN-2, S1-MAN-3 · Requirements: FR-06, FR-15, FR-22, FR-23, DR-01, DR-02
 */

export {
  ConditionList,
  getConfidenceLabel,
  getConfidenceBadgeClass,
} from "./ConditionList";

export {
  RiskBadge,
  getRiskConfig,
  RISK_CONFIG,
} from "./RiskBadge";

export type {
  RiskBadgeProps,
  RiskConfig,
} from "./RiskBadge";

export type {
  ConditionItem,
  ConfidenceTier,
  ConditionListProps,
  RiskLevel,
  TriageGuidance,
  ReferralInfo,
  AssessmentResultData,
} from "./types";
