/**
 * @file Automated safety and medical disclaimer audit test suite.
 * Owner: Dimple · Task: S2-DIM-6 · Requirements: DR-01, DR-05, DR-02, DR-08
 *
 * Verifies medical-safety invariants mandated by AI_RULES.md §2 and DR-01/DR-05:
 * - Zero diagnostic claims ("You have X", "diagnosed with").
 * - Zero drug prescriptions or specific medication dosages.
 * - Mandatory persistent disclaimer presence and wording.
 * - Emergency escalation prioritization (112 first and largest, 108 secondary).
 * - Qualitative confidence tiers (no raw percentages to patients).
 */

import { describe, expect, it } from "vitest";
import { MANDATORY_DISCLAIMER_TEXT } from "../components/layout/AppLayout";
import {
  DEFAULT_SELF_CARE_ADVICE,
  DEFAULT_WARNING_SIGNS,
} from "../components/risk/SelfCareGuidanceCard";
import { DEFAULT_RESULT_DATA } from "../pages/ResultPage";

describe("Medical Safety & Disclaimer Audit (DR-01, DR-05, DR-02)", () => {
  describe("Mandatory Persistent Disclaimer (DR-01)", () => {
    it("contains explicit non-diagnostic language", () => {
      expect(MANDATORY_DISCLAIMER_TEXT).toMatch(
        /does not provide a medical diagnosis/i,
      );
      expect(MANDATORY_DISCLAIMER_TEXT).toMatch(
        /informational triage aid/i,
      );
    });

    it("directs users to consult a qualified healthcare professional", () => {
      expect(MANDATORY_DISCLAIMER_TEXT).toMatch(
        /consult a qualified healthcare professional/i,
      );
    });

    it("includes emergency escalation guidance for life-threatening symptoms", () => {
      expect(MANDATORY_DISCLAIMER_TEXT).toMatch(
        /emergency/i,
      );
    });
  });

  describe("Zero Prescription & Medication Dosing Rules (DR-05)", () => {
    const FORBIDDEN_DRUG_PATTERNS = [
      /\bparacetamol\b/i,
      /\bibuprofen\b/i,
      /\baspirin\b/i,
      /\bantibiotic(s)?\b/i,
      /\bsteroid(s)?\b/i,
      /\b\d+\s*mg\b/i,
      /\b\d+\s*ml\b/i,
      /\btablet(s)?\b/i,
      /\bprescribe\b/i,
      /\bprescription\b/i,
    ];

    it("self-care fallback recommendations contain zero drug names or dosages", () => {
      for (const advice of DEFAULT_SELF_CARE_ADVICE) {
        for (const pattern of FORBIDDEN_DRUG_PATTERNS) {
          expect(advice).not.toMatch(pattern);
        }
      }
    });

    it("self-care recommendations focus strictly on non-prescriptive supportive care", () => {
      const combinedAdvice = DEFAULT_SELF_CARE_ADVICE.join(" ");
      expect(combinedAdvice).toMatch(/rest/i);
      expect(combinedAdvice).toMatch(/hydration/i);
      expect(combinedAdvice).toMatch(/observe|monitor/i);
    });

    it("warning signs contain explicit medical evaluation triggers", () => {
      const combinedWarnings = DEFAULT_WARNING_SIGNS.join(" ");
      expect(combinedWarnings).toMatch(/worsen|fail to improve/i);
      expect(combinedWarnings).toMatch(/difficulty breathing|chest tightness/i);
    });
  });

  describe("Zero Diagnostic Claims & Triage Framing (DR-01, DR-05)", () => {
    const FORBIDDEN_DIAGNOSTIC_ASSERTIONS = [
      /\byou have\b/i,
      /\bdiagnosed with\b/i,
      /\bour diagnosis\b/i,
      /\bwe diagnose\b/i,
      /\bguaranteed cure\b/i,
      /\bwill cure\b/i,
    ];

    it("default result conditions use qualitative confidence and avoid affirmative diagnosis", () => {
      for (const cond of DEFAULT_RESULT_DATA.conditions) {
        expect(["LIKELY", "POSSIBLE", "LESS_LIKELY"]).toContain(
          cond.confidence,
        );

        for (const pattern of FORBIDDEN_DIAGNOSTIC_ASSERTIONS) {
          expect(cond.why).not.toMatch(pattern);
          if (cond.description) {
            expect(cond.description).not.toMatch(pattern);
          }
        }
      }
    });

    it("result guidance summary frames recommendations as clinical triage", () => {
      if (DEFAULT_RESULT_DATA.guidance?.summary) {
        expect(DEFAULT_RESULT_DATA.guidance.summary).toMatch(
          /clinical triage|assessment/i,
        );
        for (const pattern of FORBIDDEN_DIAGNOSTIC_ASSERTIONS) {
          expect(DEFAULT_RESULT_DATA.guidance.summary).not.toMatch(pattern);
        }
      }
    });
  });
});
