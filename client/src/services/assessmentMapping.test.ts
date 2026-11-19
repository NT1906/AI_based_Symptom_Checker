/**
 * @file Unit tests for the assessment API <-> UI mapping.
 * Owner: Nisarg (integration) · Task: S2-NIS-13 · Issue: #280
 */

import { describe, expect, it } from "vitest";
import type { AssessmentResult, SymptomRead } from "../types";
import {
  DEFAULT_EMERGENCY_NUMBER,
  symptomApiName,
  symptomLabel,
  toConfirmedSymptom,
  toResultData,
  toSymptomUpdates,
} from "./assessmentMapping";

const SERVER_ID = "c1f67f08-3e4b-4b2e-a579-2425dc595cf2";

describe("symptom names", () => {
  it("shows the vocabulary name for a canonical ID", () => {
    expect(symptomLabel("sore_throat")).toBe("Sore throat");
    expect(symptomLabel("chest_pain")).toBe("Chest pain");
  });

  it("spaces out an unknown ID instead of failing", () => {
    expect(symptomLabel("strange_tingling")).toBe("Strange tingling");
  });

  it("sends a picked symptom back by canonical ID, in any letter case", () => {
    expect(symptomApiName("Chest pain")).toBe("chest_pain");
    expect(symptomApiName("chest PAIN")).toBe("chest_pain");
    expect(symptomApiName("shortness_of_breath")).toBe("shortness_of_breath");
  });

  it("sends free text unchanged for the server to resolve", () => {
    expect(symptomApiName("  seene me dard ")).toBe("seene me dard");
  });
});

describe("toConfirmedSymptom", () => {
  it("maps an API symptom with a readable name", () => {
    const symptom: SymptomRead = {
      id: SERVER_ID,
      name: "sore_throat",
      severity: "MODERATE",
      duration: { value: 2, unit: "DAY" },
      bodyLocation: "throat",
      source: "AI_EXTRACTED",
    };

    expect(toConfirmedSymptom(symptom, 0)).toEqual({
      id: SERVER_ID,
      name: "Sore throat",
      severity: "MODERATE",
      duration: { value: 2, unit: "DAY" },
      bodyLocation: "throat",
      source: "AI_EXTRACTED",
    });
  });

  it("fills safe defaults when optional fields are missing", () => {
    const mapped = toConfirmedSymptom({ name: "fever" }, 3);

    expect(mapped).toMatchObject({
      id: "api-symptom-3",
      name: "Fever",
      severity: "UNKNOWN",
      duration: null,
    });
  });
});

describe("toSymptomUpdates", () => {
  it("keeps server IDs, drops card-made IDs and sends canonical names", () => {
    const updates = toSymptomUpdates(
      [
        { id: SERVER_ID, name: "Sore throat", severity: "MILD", source: "AI_EXTRACTED" },
        { id: "symptom-123", name: "Chest pain", severity: "SEVERE", source: "USER_CONFIRMED" },
        { id: "symptom-456", name: "tummy ache", severity: "MILD", source: "USER_CORRECTED" },
      ],
      new Set([SERVER_ID]),
    );

    expect(updates).toEqual([
      expect.objectContaining({ id: SERVER_ID, name: "sore_throat", source: "USER_CONFIRMED" }),
      expect.objectContaining({ name: "chest_pain", severity: "SEVERE" }),
      expect.objectContaining({ name: "tummy ache", source: "USER_CORRECTED" }),
    ]);
    expect(updates[1]).not.toHaveProperty("id");
  });
});

describe("toResultData", () => {
  const base: AssessmentResult = {
    assessmentId: "a-1",
    riskLevel: "CONSULT_DOCTOR",
    conditions: [
      { name: "Iron deficiency anaemia", confidence: "POSSIBLE", rank: 1, why: "Because you reported tiredness." },
    ],
    guidance: ["Book a visit with a general physician soon."],
    referral: { required: true, specialty: "General physician", reason: "A doctor can check this." },
    limitations: ["No physical examination was done."],
  };

  it("maps conditions, next steps, referral and limitations from the server", () => {
    const { data, emergencyNumber } = toResultData(base);

    expect(emergencyNumber).toBe(DEFAULT_EMERGENCY_NUMBER);
    expect(data.riskLevel).toBe("CONSULT_DOCTOR");
    expect(data.conditions[0]).toMatchObject({
      name: "Iron deficiency anaemia",
      confidence: "POSSIBLE",
      why: "Because you reported tiredness.",
    });
    expect(data.guidance).toEqual({
      summary: "A doctor can check this.",
      stepsHeading: "What to do next",
      selfCareAdvice: ["Book a visit with a general physician soon."],
    });
    expect(data.referral).toEqual({ specialty: "General physician" });
    expect(data.limitations).toEqual(["No physical examination was done."]);
  });

  it("uses the server's emergency number and no map referral when urgent", () => {
    const { data, emergencyNumber } = toResultData({
      ...base,
      riskLevel: "URGENT",
      referral: { required: true, specialty: "Cardiologist", emergencyNumber: "108" },
    });

    expect(emergencyNumber).toBe("108");
    expect(data.referral).toBeUndefined();
  });

  it("gives empty lists, never sample data, when the server sends none", () => {
    const { data } = toResultData({ assessmentId: "a-2", riskLevel: "SELF_CARE" });

    expect(data.conditions).toEqual([]);
    expect(data.guidance?.selfCareAdvice).toEqual([]);
    expect(data.limitations).toEqual([]);
  });
});
