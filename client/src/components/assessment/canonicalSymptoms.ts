/**
 * @file Curated canonical symptom vocabulary for client-side search and selection.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-1 · Requirements: FR-03, FR-16
 */

/** Canonical symptom item available in the selectable search list. */
export interface CanonicalSymptomItem {
  /** Unique canonical identifier. */
  id: string;
  /** Human-readable display label. */
  name: string;
  /** Physiological body system classification. */
  bodySystem: string;
}

/** Pre-populated list of common canonical symptoms matching the knowledge dataset. */
export const CANONICAL_SYMPTOMS: CanonicalSymptomItem[] = [
  { id: "fever", name: "Fever", bodySystem: "general" },
  { id: "chills", name: "Chills or shivering", bodySystem: "general" },
  { id: "fatigue", name: "Tiredness or weakness", bodySystem: "general" },
  { id: "body_aches", name: "Body or muscle aches", bodySystem: "general" },
  { id: "sweating", name: "Excessive sweating", bodySystem: "general" },
  { id: "headache", name: "Headache", bodySystem: "neurological" },
  { id: "dizziness", name: "Dizziness or lightheadedness", bodySystem: "neurological" },
  { id: "confusion", name: "Confusion or disorientation", bodySystem: "neurological" },
  { id: "sore_throat", name: "Sore throat", bodySystem: "ent" },
  { id: "runny_nose", name: "Runny or stuffy nose", bodySystem: "ent" },
  { id: "ear_pain", name: "Ear pain or earache", bodySystem: "ent" },
  { id: "loss_of_smell", name: "Loss of smell or taste", bodySystem: "ent" },
  { id: "cough", name: "Cough", bodySystem: "respiratory" },
  { id: "shortness_of_breath", name: "Shortness of breath", bodySystem: "respiratory" },
  { id: "wheezing", name: "Wheezing", bodySystem: "respiratory" },
  { id: "chest_pain", name: "Chest pain or pressure", bodySystem: "cardiovascular" },
  { id: "palpitations", name: "Heart racing or palpitations", bodySystem: "cardiovascular" },
  { id: "nausea", name: "Nausea or feeling sick", bodySystem: "gastrointestinal" },
  { id: "vomiting", name: "Vomiting", bodySystem: "gastrointestinal" },
  { id: "diarrhea", name: "Diarrhea or loose stools", bodySystem: "gastrointestinal" },
  { id: "abdominal_pain", name: "Stomach or abdominal pain", bodySystem: "gastrointestinal" },
  { id: "acid_reflux", name: "Heartburn or acid reflux", bodySystem: "gastrointestinal" },
  { id: "painful_urination", name: "Pain or burning when urinating", bodySystem: "urinary" },
  { id: "frequent_urination", name: "Frequent urination", bodySystem: "urinary" },
  { id: "joint_pain", name: "Joint pain or stiffness", bodySystem: "musculoskeletal" },
  { id: "back_pain", name: "Back pain", bodySystem: "musculoskeletal" },
  { id: "neck_stiffness", name: "Stiff neck", bodySystem: "musculoskeletal" },
  { id: "skin_rash", name: "Skin rash or redness", bodySystem: "skin" },
  { id: "itching", name: "Itchy skin", bodySystem: "skin" },
  { id: "skin_swelling", name: "Swelling or localized edema", bodySystem: "skin" },
  { id: "eye_redness", name: "Eye redness or irritation", bodySystem: "eye" },
  { id: "photophobia", name: "Sensitivity to bright light", bodySystem: "eye" },
];

