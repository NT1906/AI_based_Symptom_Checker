/**
 * @file Curated plain-language symptom glossary definitions for client tooltips.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-3 · Requirements: FR-18
 */

/** Plain-language symptom glossary definition record (FR-18). */
export interface SymptomGlossaryEntry {
  /** Canonical identifier matching backend glossary. */
  id: string;
  /** Human-readable display label. */
  name: string;
  /** Plain-language, non-diagnostic explanation of the symptom. */
  plainDefinition: string;
  /** Physiological body system classification. */
  bodySystem?: string;
}

/** Curated client-side symptom definitions aligned with knowledge service glossary. */
export const SYMPTOM_GLOSSARY: Record<string, SymptomGlossaryEntry> = Object.freeze({
  fever: {
    id: "fever",
    name: "Fever",
    plainDefinition:
      "A temporary increase in body temperature above normal (typically above 38°C or 100.4°F), often part of the body's natural defense against infection.",
    bodySystem: "general",
  },
  headache: {
    id: "headache",
    name: "Headache",
    plainDefinition:
      "A pain or aching sensation in any part of the head, ranging from a dull ache to sharp or throbbing pain.",
    bodySystem: "neurological",
  },
  fatigue: {
    id: "fatigue",
    name: "Tiredness or weakness",
    plainDefinition:
      "An overwhelming feeling of tiredness, lack of energy, or physical weakness that does not improve with ordinary rest or sleep.",
    bodySystem: "general",
  },
  cough: {
    id: "cough",
    name: "Cough",
    plainDefinition:
      "A reflex action that clears your airways of mucus, irritants, or foreign particles. It can be dry or produce phlegm.",
    bodySystem: "respiratory",
  },
  shortness_of_breath: {
    id: "shortness_of_breath",
    name: "Shortness of breath",
    plainDefinition:
      "A sensation of difficult, uncomfortable, or labored breathing, or feeling like you cannot get enough air into your lungs.",
    bodySystem: "respiratory",
  },
  chest_pain: {
    id: "chest_pain",
    name: "Chest pain or pressure",
    plainDefinition:
      "Any discomfort, tightness, burning, or crushing pain felt anywhere in the chest area between the neck and upper abdomen.",
    bodySystem: "cardiovascular",
  },
  nausea: {
    id: "nausea",
    name: "Nausea or feeling sick",
    plainDefinition:
      "An unsettled feeling in the stomach accompanied by an urge or sensation that you might vomit.",
    bodySystem: "gastrointestinal",
  },
  skin_rash: {
    id: "skin_rash",
    name: "Skin rash or redness",
    plainDefinition:
      "An area of irritated, inflamed, swollen, or discolored skin that may itch, burn, or form bumps, patches, or flakes.",
    bodySystem: "skin",
  },
  dizziness: {
    id: "dizziness",
    name: "Dizziness or lightheadedness",
    plainDefinition:
      "A feeling of faintness, unsteadiness, or a spinning sensation (vertigo) affecting balance.",
    bodySystem: "neurological",
  },
  sore_throat: {
    id: "sore_throat",
    name: "Sore throat",
    plainDefinition:
      "Pain, scratchiness, or irritation of the throat that often worsens when you swallow.",
    bodySystem: "ent",
  },
  skin_swelling: {
    id: "skin_swelling",
    name: "Swelling or localized edema",
    plainDefinition:
      "Enlargement or puffiness of body tissue caused by an accumulation of fluid or inflammation beneath the skin.",
    bodySystem: "skin",
  },
  joint_pain: {
    id: "joint_pain",
    name: "Joint pain or stiffness",
    plainDefinition:
      "Discomfort, ache, or stiffness felt in one or more joints (such as knees, hips, or fingers), often worsening with movement.",
    bodySystem: "musculoskeletal",
  },
  abdominal_pain: {
    id: "abdominal_pain",
    name: "Stomach or abdominal pain",
    plainDefinition:
      "Pain or cramping occurring in the area between the chest and groin, ranging from mild generalized cramps to sharp localized pain.",
    bodySystem: "gastrointestinal",
  },
  chills: {
    id: "chills",
    name: "Chills or shivering",
    plainDefinition:
      "Involuntary muscle shivering and feeling intensely cold, which commonly occurs as body temperature begins to rise during a fever.",
    bodySystem: "general",
  },
});

/**
 * Retrieves a plain-language symptom glossary entry by ID or symptom name.
 *
 * @param identifier Canonical symptom ID (e.g. "skin_rash") or display name (e.g. "Skin rash").
 * @returns The matching glossary definition entry, or null if not found.
 */
export function getSymptomDefinition(identifier: string): SymptomGlossaryEntry | null {
  if (!identifier || typeof identifier !== "string") {
    return null;
  }

  const clean = identifier.trim().toLowerCase();
  const normalizedKey = clean.replace(/[\s-]+/g, "_");

  // Direct ID lookup
  if (normalizedKey in SYMPTOM_GLOSSARY) {
    return SYMPTOM_GLOSSARY[normalizedKey];
  }

  // Exact display-name lookup only. Why: a partial match would show the wrong
  // definition (e.g. "pain" -> chest pain), which is unsafe medical text.
  for (const entry of Object.values(SYMPTOM_GLOSSARY)) {
    if (entry.name.toLowerCase() === clean) {
      return entry;
    }
  }

  return null;
}
