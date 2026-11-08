/**
 * @file Unit tests for visual symptom detection helper.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-1 · Requirements: idea §3
 */

import { describe, expect, it } from "vitest";
import {
  hasVisualSymptoms,
  VISUAL_SYMPTOM_KEYWORDS,
  VISUAL_BODY_SYSTEMS,
} from "./visualSymptoms";
import type { ConfirmedSymptom } from "./types";
import { CANONICAL_SYMPTOMS } from "./canonicalSymptoms";

describe("hasVisualSymptoms", () => {
  describe("Happy Path - Visual symptoms detected", () => {
    it("detects visual symptoms from plain text descriptions", () => {
      expect(hasVisualSymptoms("I noticed a red rash on my arm")).toBe(true);
      expect(hasVisualSymptoms("There is severe swelling near my ankle")).toBe(true);
      expect(hasVisualSymptoms("I have itchy skin and hives")).toBe(true);
      expect(hasVisualSymptoms("Small fluid-filled blisters on my back")).toBe(true);
      expect(hasVisualSymptoms("Dry scaly skin patches")).toBe(true);
      expect(hasVisualSymptoms("Acne and pimples on face")).toBe(true);
    });

    it("detects visual symptoms from array of string symptoms", () => {
      expect(hasVisualSymptoms(["fever", "skin rash", "chills"])).toBe(true);
      expect(hasVisualSymptoms(["headache", "swelling"])).toBe(true);
      expect(hasVisualSymptoms(["bumps", "nausea"])).toBe(true);
    });

    it("detects visual symptoms from ConfirmedSymptom objects", () => {
      const visualSymptom: ConfirmedSymptom = {
        id: "sym-1",
        name: "Skin rash or redness",
        severity: "MODERATE",
        bodyLocation: "arm",
      };
      expect(hasVisualSymptoms([visualSymptom])).toBe(true);
      expect(hasVisualSymptoms(visualSymptom)).toBe(true);
    });

    it("detects visual symptoms by bodySystem classification", () => {
      const skinSymptom = CANONICAL_SYMPTOMS.find((s) => s.id === "skin_rash");
      expect(skinSymptom).toBeDefined();
      if (skinSymptom) {
        expect(hasVisualSymptoms([skinSymptom])).toBe(true);
        expect(hasVisualSymptoms(skinSymptom)).toBe(true);
      }
    });

    it("detects visual symptoms by body location indicating skin or scalp", () => {
      const locatedSymptom: ConfirmedSymptom = {
        id: "sym-loc",
        name: "Irritation",
        severity: "MILD",
        bodyLocation: "skin of forearm",
      };
      expect(hasVisualSymptoms([locatedSymptom])).toBe(true);
    });
  });

  describe("Negative Path - Non-visual symptoms", () => {
    it("returns false for general systemic symptoms", () => {
      expect(hasVisualSymptoms("I have had a high fever and headache since yesterday")).toBe(false);
      expect(hasVisualSymptoms("Feeling tired with fatigue and body aches")).toBe(false);
      expect(hasVisualSymptoms("Tiredness or weakness")).toBe(false);
      expect(hasVisualSymptoms("Nausea and stomach ache")).toBe(false);
      expect(hasVisualSymptoms("Chest pain and shortness of breath")).toBe(false);
    });

    it("returns false for non-visual ConfirmedSymptom objects", () => {
      const nonVisualSymptoms: ConfirmedSymptom[] = [
        {
          id: "headache-1",
          name: "Headache",
          severity: "MILD",
        },
        {
          id: "fever-1",
          name: "Fever",
          severity: "SEVERE",
        },
      ];
      expect(hasVisualSymptoms(nonVisualSymptoms)).toBe(false);
    });

    it("returns false for non-visual canonical symptoms", () => {
      const systemicItems = CANONICAL_SYMPTOMS.filter(
        (s) => s.bodySystem === "general" || s.bodySystem === "neurological",
      );
      expect(hasVisualSymptoms(systemicItems)).toBe(false);
    });
  });

  describe("Edge cases and boundary handling", () => {
    it("returns false for null, undefined, and empty inputs", () => {
      expect(hasVisualSymptoms(null)).toBe(false);
      expect(hasVisualSymptoms(undefined)).toBe(false);
      expect(hasVisualSymptoms("")).toBe(false);
      expect(hasVisualSymptoms("   ")).toBe(false);
      expect(hasVisualSymptoms([])).toBe(false);
    });

    it("handles case insensitivity, underscores, and hyphens", () => {
      expect(hasVisualSymptoms("SKIN_RASH")).toBe(true);
      expect(hasVisualSymptoms("skin-swelling")).toBe(true);
      expect(hasVisualSymptoms("RING-SHAPED-RASH")).toBe(true);
      expect(hasVisualSymptoms("URTICARIA")).toBe(true);
    });

    it("exports frozen keyword and body system lists", () => {
      expect(VISUAL_SYMPTOM_KEYWORDS.length).toBeGreaterThan(20);
      expect(VISUAL_BODY_SYSTEMS).toContain("skin");
      expect(VISUAL_BODY_SYSTEMS).toContain("eye");
    });
  });
});
