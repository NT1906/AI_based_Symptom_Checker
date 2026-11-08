/**
 * @file Visual symptom detection utilities for situational image attachment.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-1 · Requirements: idea §3
 */

import type { ConfirmedSymptom } from "./types";
import type { CanonicalSymptomItem } from "./canonicalSymptoms";

/** Acceptable input forms for visual symptom evaluation. */
export type VisualSymptomCandidate =
  | string
  | ConfirmedSymptom
  | CanonicalSymptomItem
  | Record<string, unknown>;

/** Permitted aggregate or individual inputs for hasVisualSymptoms. */
export type VisualSymptomInput =
  | VisualSymptomCandidate
  | VisualSymptomCandidate[]
  | null
  | undefined;

/**
 * Curated list of keywords, symptom names, and dermatological terms that
 * indicate an identifiable visual or skin component (idea §3).
 */
export const VISUAL_SYMPTOM_KEYWORDS: readonly string[] = Object.freeze([
  "rash",
  "skin_rash",
  "skin rash",
  "hives",
  "urticaria",
  "swelling",
  "skin_swelling",
  "edema",
  "discoloration",
  "spots",
  "bump",
  "bumps",
  "small_itchy_bumps",
  "blister",
  "blisters",
  "fluid_filled_blisters",
  "bruise",
  "burn",
  "redness",
  "spreading_redness",
  "lesion",
  "lesions",
  "itching",
  "itchy",
  "itchy skin",
  "scaly_skin",
  "scaly skin",
  "dry_skin",
  "dry skin",
  "ring_shaped_rash",
  "pimple",
  "pimples",
  "acne",
  "blackhead",
  "blackheads",
  "whitehead",
  "whiteheads",
  "eczema",
  "dermatitis",
  "scabies",
  "psoriasis",
  "shingles",
  "chickenpox",
  "cellulitis",
  "erythema",
  "mole",
  "boil",
  "ulcer",
  "dermatosis",
  "skin_burrows",
]);

/**
 * Body systems where symptoms frequently present with visible external manifestations.
 */
export const VISUAL_BODY_SYSTEMS: readonly string[] = Object.freeze([
  "skin",
  "dermatology",
  "integumentary",
  "eye",
  "cutaneous",
]);

/**
 * Determines whether the given symptoms, text, or assessment state contain visual
 * components warranting situational image attachment (idea §3).
 *
 * Visual symptoms include rashes, skin discoloration, swelling, bumps, lesions,
 * blisters, and related dermatological complaints. General systemic symptoms
 * (e.g. fever, fatigue, headache, nausea) do not trigger this check.
 *
 * @param input Symptom list, single symptom object, or user text message.
 * @returns True if at least one visual symptom is detected; otherwise false.
 */
export function hasVisualSymptoms(input: VisualSymptomInput): boolean {
  if (!input) {
    return false;
  }

  // Handle single string (e.g. user chat message or symptom query)
  if (typeof input === "string") {
    return checkTextContainsVisualKeywords(input);
  }

  // Handle array of symptoms or strings
  if (Array.isArray(input)) {
    if (input.length === 0) {
      return false;
    }
    return input.some((item) => {
      if (typeof item === "string") {
        return checkTextContainsVisualKeywords(item);
      }
      return checkSymptomObjectContainsVisual(item);
    });
  }

  // Handle single symptom object
  if (typeof input === "object") {
    return checkSymptomObjectContainsVisual(input);
  }

  return false;
}

/**
 * Helper to escape special regex characters.
 *
 * @param str The raw string to escape.
 * @returns Escaped regex string safe for RegExp constructor.
 */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Checks if a string contains any visual symptom keyword or pattern as a discrete word or phrase.
 *
 * Uses word boundaries so that substrings like "redness" inside "tiredness" do not trigger false positives.
 *
 * @param text The string to evaluate.
 * @returns True if a visual keyword match is found.
 */
function checkTextContainsVisualKeywords(text: string): boolean {
  const normalized = text.toLowerCase().replace(/[-_]/g, " ");

  return VISUAL_SYMPTOM_KEYWORDS.some((keyword) => {
    const normalizedKeyword = keyword.replace(/[-_]/g, " ");
    // Use word boundaries so that e.g. "redness" doesn't falsely match inside "tiredness"
    const regex = new RegExp(`\\b${escapeRegex(normalizedKeyword)}\\b`, "i");
    return regex.test(normalized);
  });
}

/**
 * Checks if a symptom domain object represents a visual symptom.
 *
 * @param symptom The symptom object with optional name, id, bodySystem, or bodyLocation.
 * @returns True if the symptom represents a visual symptom.
 */
function checkSymptomObjectContainsVisual(
  symptom: ConfirmedSymptom | CanonicalSymptomItem | Record<string, unknown>,
): boolean {
  // Check bodySystem if present (e.g. "skin", "eye")
  if ("bodySystem" in symptom && typeof symptom.bodySystem === "string") {
    const normalizedSystem = symptom.bodySystem.trim().toLowerCase();
    if (VISUAL_BODY_SYSTEMS.includes(normalizedSystem)) {
      return true;
    }
  }

  // Check symptom name
  if ("name" in symptom && typeof symptom.name === "string") {
    if (checkTextContainsVisualKeywords(symptom.name)) {
      return true;
    }
  }

  // Check symptom id
  if ("id" in symptom && typeof symptom.id === "string") {
    if (checkTextContainsVisualKeywords(symptom.id)) {
      return true;
    }
  }

  // Check body location if present (e.g. "skin", "face", "forearm", "leg")
  if ("bodyLocation" in symptom && typeof symptom.bodyLocation === "string") {
    const normalizedLoc = symptom.bodyLocation.toLowerCase();
    if (normalizedLoc.includes("skin") || normalizedLoc.includes("scalp")) {
      return true;
    }
  }

  return false;
}
