# Knowledge Service: Symptom Normalization, Vocabulary & Curated Glossary

**Owner:** Kavya (knowledge) · **Tasks:** S1-KAV-1, S1-KAV-3 · **Requirements:** FR-03, FR-18

The knowledge service provides two core clinical capabilities for the AI-Based Symptom Checker:
1. **Deterministic Symptom Normalization (FR-03 / S1-KAV-1):** Maps colloquial lay language (including Indian transliterated Hinglish) to the 100 canonical clinical symptoms in `symptoms.json` (aligned with `conditions.json`).
2. **Curated Symptom Glossary (FR-18 / S1-KAV-3):** Provides plain-language, non-diagnostic symptom definitions, red-flag care guidance, and keyword search for UI tooltips, user education, and intent handling.

---

## 1. Public Interface

Import from `app.services.knowledge`:

```python
from app.services.knowledge import (
    # Symptom Normalizer (FR-03)
    SymptomNormalizer,
    get_normalizer,
    normalize_symptom,
    normalize_symptom_id,
    CanonicalSymptom,
    NormalizedSymptom,
    TextMatchSpan,
    # Curated Glossary (FR-18)
    SymptomGlossary,
    get_glossary,
    lookup_glossary,
    get_symptom_definition,
    GlossaryEntry,
)
```

---

## 2. Curated Symptom Glossary (FR-18)

The glossary provides empathetic, plain-language explanations of all 100 canonical symptoms at a 6th-to-8th grade reading level, reviewed for clinical safety and safe medical wording.

### 2.1 Direct Definition & Entry Lookup

```python
# Functional lookup by canonical ID, display name, or lay term
entry = lookup_glossary("chest_pain")
assert entry is not None
assert entry.id == "chest_pain"
assert entry.body_system == "cardiovascular"

# Retrieve definition string directly
definition = get_symptom_definition("tummy ache")
assert "stomach" in definition.lower()

# Transliterated Hinglish lookup
hinglish_entry = lookup_glossary("bukhar")
assert hinglish_entry.id == "fever"
```

### 2.2 Keyword Search & Ranking

Search across clinical names, lay terms, and plain-language definitions:

```python
glossary = get_glossary()

# Returns ranked list of up to limit results
results = glossary.search("cough", limit=5)
assert results[0].id == "cough"

# Prefix search
prefix_results = glossary.search("palp", limit=3)
assert any(r.id == "palpitations" for r in prefix_results)
```

### 2.3 Body System Filtering

Browse or filter symptom entries by anatomical category:

```python
glossary = get_glossary()

# Filter by system
respiratory_entries = glossary.list_entries(body_system="respiratory")
assert len(respiratory_entries) == 7

# List all 100 canonical entries sorted alphabetically
all_entries = glossary.list_entries()
assert len(all_entries) == 100
```

### 2.4 Glossary Schema (`GlossaryEntry`)

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Canonical snake_case symptom ID aligned with `symptoms.json` |
| `name` | `str` | Clinical display name |
| `body_system` | `str` | Anatomical body system |
| `plain_definition` | `str` | Plain-language, non-diagnostic description |
| `when_to_seek_care` | `str` | Actionable guidance on when medical evaluation is advised |
| `lay_terms` | `tuple[str, ...]` | Colloquial synonyms and search aliases |

---

## 3. Symptom Normalization (FR-03)

### 3.1 Direct Phrase Normalization

```python
# Returns full NormalizedSymptom schema
result = normalize_symptom("tummy ache")
assert result.canonical_id == "abdominal_pain"
assert result.confidence == 1.0

# Shortcut returning string ID only
canonical_id = normalize_symptom_id("badan dard")
assert canonical_id == "body_aches"
```

### 3.2 Free-Text Mention Extraction

```python
normalizer = get_normalizer()
text = "I have a severe headache and high temperature since yesterday"
matches = normalizer.extract_symptoms_from_text(text)

# Returns non-overlapping TextMatchSpan objects ordered by appearance
```

---

## 4. Medical Safety & Clinical Design Principles

1. **Strictly Non-Diagnostic (Rule §2):** Definitions describe *what a symptom feels like* and everyday contexts. They never state diagnostic conclusions ("You have...", "Diagnosis:").
2. **Zero Medication Prescriptions:** Glossary entries never prescribe drugs, dosages, or pharmaceutical treatments.
3. **Emergency Red-Flag Guidance:** Critical conditions (chest pain, stroke signs, breathing difficulty, severe bleeding, self-harm) explicitly highlight immediate emergency services (`112`).
4. **100% Deterministic:** Lookup and normalization use fast, in-memory hash indices with zero LLM dependence in the critical path.
5. **Vocabulary Parity:** Every entry in `glossary.json` strictly corresponds to an ID in `symptoms.json` and `conditions.json`.

---

## 5. Running Tests

Run the full unit test suite for the knowledge service:

```bash
# In the server directory:
pytest tests/unit/knowledge/ -v
```
