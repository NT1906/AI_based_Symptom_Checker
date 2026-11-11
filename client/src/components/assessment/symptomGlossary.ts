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
  /** Safe guidance on when this symptom warrants prompt medical evaluation. */
  whenToSeekCare: string;
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
    whenToSeekCare:
      "Seek urgent medical attention if temperature exceeds 39.4°C (103°F), lasts more than 3 days, or is accompanied by a stiff neck, confusion, or difficulty breathing.",
    bodySystem: "general",
  },
  headache: {
    id: "headache",
    name: "Headache",
    plainDefinition:
      "A pain or aching sensation in any part of the head, ranging from a dull ache to sharp or throbbing pain.",
    whenToSeekCare:
      "Seek emergency care if headache is sudden and extraordinarily severe ('thunderclap'), follows a head injury, or comes with fever, confusion, or weakness.",
    bodySystem: "neurological",
  },
  fatigue: {
    id: "fatigue",
    name: "Tiredness or weakness",
    plainDefinition:
      "An overwhelming feeling of tiredness, lack of energy, or physical weakness that does not improve with ordinary rest or sleep.",
    whenToSeekCare:
      "Seek medical advice if tiredness lasts more than two weeks, begins suddenly, or is accompanied by unintended weight loss or shortness of breath.",
    bodySystem: "general",
  },
  cough: {
    id: "cough",
    name: "Cough",
    plainDefinition:
      "A reflex action that clears your airways of mucus, irritants, or foreign particles. It can be dry or produce phlegm.",
    whenToSeekCare:
      "Consult a doctor if coughing up blood, experiencing chest pain, difficulty breathing, or if the cough persists beyond three weeks.",
    bodySystem: "respiratory",
  },
  shortness_of_breath: {
    id: "shortness_of_breath",
    name: "Shortness of breath",
    plainDefinition:
      "A sensation of difficult, uncomfortable, or labored breathing, or feeling like you cannot get enough air into your lungs.",
    whenToSeekCare:
      "Seek emergency medical evaluation (call 112) immediately if breathing difficulty begins suddenly, occurs at rest, or is accompanied by chest tightness or blue lips.",
    bodySystem: "respiratory",
  },
  chest_pain: {
    id: "chest_pain",
    name: "Chest pain or pressure",
    plainDefinition:
      "Any discomfort, tightness, burning, or crushing pain felt anywhere in the chest area between the neck and upper abdomen.",
    whenToSeekCare:
      "Treat new, severe, or crushing chest pain as a potential medical emergency (call 112) immediately, especially if it radiates to the arm, shoulder, back, or jaw.",
    bodySystem: "cardiovascular",
  },
  nausea: {
    id: "nausea",
    name: "Nausea or feeling sick",
    plainDefinition:
      "An unsettled feeling in the stomach accompanied by an urge or sensation that you might vomit.",
    whenToSeekCare:
      "Seek medical attention if nausea prevents keeping any fluids down for more than 24 hours or is accompanied by severe abdominal pain or confusion.",
    bodySystem: "gastrointestinal",
  },
  skin_rash: {
    id: "skin_rash",
    name: "Skin rash or redness",
    plainDefinition:
      "An area of irritated, inflamed, swollen, or discolored skin that may itch, burn, or form bumps, patches, or flakes.",
    whenToSeekCare:
      "Consult a doctor if the rash spreads rapidly, affects the eyes or mouth, becomes extremely painful, develops blisters, or is accompanied by fever.",
    bodySystem: "skin",
  },
  dizziness: {
    id: "dizziness",
    name: "Dizziness or lightheadedness",
    plainDefinition:
      "A feeling of faintness, unsteadiness, or a spinning sensation (vertigo) affecting balance.",
    whenToSeekCare:
      "Seek emergency care if dizziness occurs with chest pain, palpitations, loss of consciousness, speech difficulty, or sudden weakness.",
    bodySystem: "neurological",
  },
  sore_throat: {
    id: "sore_throat",
    name: "Sore throat",
    plainDefinition:
      "Pain, scratchiness, or irritation of the throat that often worsens when you swallow.",
    whenToSeekCare:
      "Consult a healthcare professional if throat pain makes it difficult to breathe or swallow liquids, or persists for longer than a week.",
    bodySystem: "ent",
  },
  skin_swelling: {
    id: "skin_swelling",
    name: "Swelling or localized edema",
    plainDefinition:
      "Enlargement or puffiness of body tissue caused by an accumulation of fluid or inflammation beneath the skin.",
    whenToSeekCare:
      "Seek immediate medical attention if swelling occurs rapidly in the face, tongue, or throat, or if accompanied by difficulty breathing.",
    bodySystem: "skin",
  },
  joint_pain: {
    id: "joint_pain",
    name: "Joint pain or stiffness",
    plainDefinition:
      "Discomfort, ache, or stiffness felt in one or more joints (such as knees, hips, or fingers), often worsening with movement.",
    whenToSeekCare:
      "Consult a physician if joint pain is accompanied by rapid swelling, severe warmth or redness, intense pain preventing weight-bearing, or fever.",
    bodySystem: "musculoskeletal",
  },
  abdominal_pain: {
    id: "abdominal_pain",
    name: "Stomach or abdominal pain",
    plainDefinition:
      "Pain or cramping occurring in the area between the chest and groin, ranging from mild generalized cramps to sharp localized pain.",
    whenToSeekCare:
      "Seek emergency care if abdominal pain is sudden and severe, causes a rigid/tender abdomen, or is accompanied by vomiting blood or high fever.",
    bodySystem: "gastrointestinal",
  },
  chills: {
    id: "chills",
    name: "Chills or shivering",
    plainDefinition:
      "Involuntary muscle shivering and feeling intensely cold, which commonly occurs as body temperature begins to rise during a fever.",
    whenToSeekCare:
      "Consult a doctor if chills are accompanied by uncontrollable shaking rigors, high fever, chest pain, or confusion.",
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

  // Name or partial match lookup
  for (const entry of Object.values(SYMPTOM_GLOSSARY)) {
    const entryName = entry.name.toLowerCase();
    const entryId = entry.id.toLowerCase();

    if (
      entryName === clean ||
      entryId === clean ||
      entryName.includes(clean) ||
      clean.includes(entryId)
    ) {
      return entry;
    }
  }

  return null;
}
