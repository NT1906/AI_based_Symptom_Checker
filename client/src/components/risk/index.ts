/**
 * @file Public component exports for risk-tier presentation and safety alerts.
 * Owner: Dimple · Tasks: S1-DIM-3, S2-DIM-2, S2-DIM-5 · Requirements: FR-06, FR-15, DR-01, DR-02, NFR-06, idea §8
 */

export { RiskBadge, default as RiskBadgeComponent } from "./RiskBadge";
export type { RiskBadgeProps, RiskLevel } from "./RiskBadge";

export { UrgentCareAlert, default as UrgentCareAlertComponent } from "./UrgentCareAlert";
export type { UrgentCareAlertProps } from "./UrgentCareAlert";

export {
  SelfCareGuidanceCard,
  default as SelfCareGuidanceCardComponent,
  DEFAULT_SELF_CARE_ADVICE,
  DEFAULT_WARNING_SIGNS,
} from "./SelfCareGuidanceCard";
export type { SelfCareGuidanceCardProps } from "./SelfCareGuidanceCard";
