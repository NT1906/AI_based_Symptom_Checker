/**
 * @file Maps assessment API data to and from the UI components' shapes.
 * Owner: Nisarg (integration) · Task: S2-NIS-13 · Issue: #280 · Requirements: FR-03, FR-06, FR-22, FR-24
 *
 * Pure functions only, so the safety-relevant mapping is easy to test:
 * - Symptoms go back to the API by canonical ID whenever the user picked a
 * known symptom, so the risk engine always recognises it.
 * - The result page only ever gets the server's result, never sample data.
 */

import type { ConfirmedSymptom } from "../components/assessment/types";
import { CANONICAL_SYMPTOMS } from "../components/assessment/canonicalSymptoms";
import type { AssessmentResultData } from "../components/result/types";
import type {
  AssessmentResult,
  SymptomRead,
  SymptomUpdate,
} from "../types";

/** Emergency number used when the result does not carry one (AI_RULES.md §2.5). */
export const DEFAULT_EMERGENCY_NUMBER = "112";

const NAME_BY_ID = new Map(CANONICAL_SYMPTOMS.map((s) => [s.id, s.name]));
const ID_BY_NAME = new Map(
  CANONICAL_SYMPTOMS.map((s) => [s.name.toLowerCase(), s.id]),
);

/**
 * Human-readable label for a symptom name from the API.
 *
 * @param name - Canonical ID (e.g. `sore_throat`) or free text.
 * @returns The vocabulary display name, or the text with underscores spaced out.
 */
export function symptomLabel(name: string): string {
  const known = NAME_BY_ID.get(name);
  if (known) return known;
  const spaced = name.replace(/_/g, " ").trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * The name to send to the API: the canonical ID for a known symptom, else the text.
 *
 * @param label - What the confirmation card shows (display name, ID or free text).
 * @returns Canonical ID when the label is a vocabulary name or ID, else the trimmed text.
 */
export function symptomApiName(label: string): string {
  const trimmed = label.trim();
  if (NAME_BY_ID.has(trimmed)) return trimmed;
  return ID_BY_NAME.get(trimmed.toLowerCase()) ?? trimmed;
}

/**
 * Convert an API symptom into the confirmation card's shape.
 *
 * @param symptom - Symptom from `GET /symptoms`.
 * @param index - Position, used for a stable ID when the API gave none.
 * @returns Card symptom with a readable name.
 */
export function toConfirmedSymptom(
  symptom: SymptomRead,
  index: number,
): ConfirmedSymptom {
  return {
    id: symptom.id ?? `api-symptom-${index}`,
    name: symptomLabel(symptom.name),
    severity: symptom.severity ?? "UNKNOWN",
    duration: symptom.duration
      ? { value: symptom.duration.value, unit: symptom.duration.unit ?? "DAY" }
      : null,
    bodyLocation: symptom.bodyLocation ?? null,
    source:
      symptom.source === "USER_CORRECTED" || symptom.source === "USER"
        ? symptom.source
        : "AI_EXTRACTED",
  };
}

/**
 * Convert the user's confirmed list into the `PATCH /symptoms` payload.
 *
 * @param symptoms - Symptoms as confirmed in the card.
 * @param serverIds - IDs the API issued; other IDs were made up by the card.
 * @returns Update items with canonical names where known.
 */
export function toSymptomUpdates(
  symptoms: ConfirmedSymptom[],
  serverIds: ReadonlySet<string>,
): SymptomUpdate[] {
  return symptoms.map((symptom) => ({
    ...(serverIds.has(symptom.id) ? { id: symptom.id } : {}),
    name: symptomApiName(symptom.name),
    severity: symptom.severity,
    duration: symptom.duration ?? null,
    bodyLocation: symptom.bodyLocation ?? null,
    source:
      symptom.source === "USER_CORRECTED" ? "USER_CORRECTED" : "USER_CONFIRMED",
  }));
}

/** Result page data plus the parts the page shows outside `AssessmentResultData`. */
export interface MappedResult {
  /** Data for `ResultPage`. */
  data: AssessmentResultData;
  /** Emergency number to show first on an urgent result. */
  emergencyNumber: string;
}

/**
 * Convert the API result into the result page's shape.
 *
 * @param result - Result from `GET /result`.
 * @returns Page data built only from the server's result.
 */
export function toResultData(result: AssessmentResult): MappedResult {
  const referral = result.referral;
  return {
    emergencyNumber: referral?.emergencyNumber || DEFAULT_EMERGENCY_NUMBER,
    data: {
      assessmentId: result.assessmentId,
      riskLevel: result.riskLevel,
      conditions: (result.conditions ?? []).map((condition, index) => ({
        id: `condition-${condition.rank ?? index + 1}`,
        name: condition.name,
        confidence: condition.confidence,
        rank: condition.rank ?? index + 1,
        why: condition.why ?? null,
        specialty: condition.specialty ?? null,
        icd10Code: condition.icd10Code ?? null,
        description: condition.description ?? null,
      })),
      guidance: {
        summary: referral?.reason ?? undefined,
        stepsHeading: "What to do next",
        selfCareAdvice: result.guidance ?? [],
      },
      referral:
        referral?.specialty && result.riskLevel !== "URGENT"
          ? { specialty: referral.specialty }
          : undefined,
      limitations: result.limitations ?? [],
      completedAt: result.createdAt,
    },
  };
}
