# Knowledge Service: Symptom Normalization & Vocabulary

**Owner:** Kavya (knowledge) · **Task:** S1-KAV-1 · **Requirements:** FR-03

The knowledge service provides deterministic mapping between natural colloquial/lay language (including Indian transliterated Hinglish) and the 100 canonical clinical symptoms defined in `symptoms.json` (aligned with `conditions.json`).

This service satisfies requirement **FR-03** by guaranteeing that whether a symptom originates from unstructured chat input, AI extraction, or a selectable list, it deterministically resolves to an identical canonical identifier before reaching condition prediction or the risk engine.

---

## 1. Public Interface

Import from `app.services.knowledge`:

```python
from app.services.knowledge import (
    SymptomNormalizer,
    get_normalizer,
    normalize_symptom,
    normalize_symptom_id,
    CanonicalSymptom,
    NormalizedSymptom,
    TextMatchSpan,
)
```

### 1.1 Direct Phrase Normalization

```python
# Returns full NormalizedSymptom schema
result = normalize_symptom("tummy ache")
assert result.canonical_id == "abdominal_pain"
assert result.canonical_name == "Abdominal pain"
assert result.body_system == "gastrointestinal"
assert result.confidence == 1.0

# Shortcut returning string ID only
canonical_id = normalize_symptom_id("badan dard")
assert canonical_id == "body_aches"
```

### 1.2 Free-Text Mention Extraction

```python
normalizer = get_normalizer()
text = "I have a severe headache and high temperature since yesterday"
matches = normalizer.extract_symptoms_from_text(text)

# Returns non-overlapping TextMatchSpan objects ordered by appearance:
# - TextMatchSpan(canonical_id="headache", matched_term="headache", start_char=16, end_char=24)
# - TextMatchSpan(canonical_id="fever", matched_term="high temperature", start_char=29, end_char=45)
```

### 1.3 Vocabulary Lookups

```python
normalizer = get_normalizer()

# Lookup by ID
symptom = normalizer.get_by_id("fever")
assert symptom.name == "Fever"
assert "bukhar" in symptom.lay_terms

# Filter by anatomical body system
respiratory_symptoms = normalizer.get_by_body_system("respiratory")

# Verify canonical ID validity
assert normalizer.is_canonical_id("chest_pain") is True
assert normalizer.is_canonical_id("made_up_symptom") is False
```

---

## 2. Medical Safety and Design Principles

1. **100% Deterministic:** No LLMs, randomness, or heuristics are involved. Same input always maps to the same output.
2. **Longest-Match Priority:** In free-text extraction, compound terms match first (e.g., `"sudden severe headache"` takes precedence over `"headache"`).
3. **Word-Boundary Isolation:** Matching requires word boundaries `\b` to prevent false positive substring collisions (e.g., `"cold"` will not match within `"scold"`, `"sweat"` will not match within `"sweater"`).
4. **Hinglish Support:** Indian colloquial Romanized transliterations (`"pet me dard"`, `"bukhar"`, `"rang udd gaya"`) are directly supported.
5. **No Diagnosis:** This service only normalizes clinical symptom terms; it never performs diagnostic inferences.

---

## 3. Running Tests

Run the dedicated knowledge unit tests:

```bash
# In the server directory:
pytest tests/unit/knowledge/ -v
```
