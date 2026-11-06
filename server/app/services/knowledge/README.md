# Knowledge Service: Symptom Normalization, Vocabulary, Curated Glossary & Self-Care Guidance

**Owner:** Kavya (knowledge) · **Tasks:** S1-KAV-1, S1-KAV-3, S2-KAV-1 · **Requirements:** FR-03, FR-18, idea §8, DR-05  
**Clinical & Safety Review:** Dimple (Medical Safety & Privacy Lead)

The knowledge service provides three core clinical capabilities for the AI-Based Symptom Checker:
1. **Deterministic Symptom Normalization (FR-03 / S1-KAV-1):** Maps colloquial lay language (including Indian transliterated Hinglish) to the 100 canonical clinical symptoms in `symptoms.json` (aligned with `conditions.json`).
2. **Curated Symptom Glossary (FR-18 / S1-KAV-3):** Provides plain-language, non-diagnostic symptom definitions, red-flag care guidance, and keyword search for UI tooltips, user education, and intent handling.
3. **Condition Self-Care Guidance (idea §8, DR-05 / S2-KAV-1):** Provides curated, non-prescriptive supportive self-care recommendations, clinical warning signs, and safe monitoring tips for all 38 conditions in the catalog.

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
    # Condition Self-Care Guidance (idea §8, DR-05)
    SelfCareService,
    get_self_care_service,
    lookup_self_care,
    get_self_care_guidance,
    SelfCareGuidance,
)
```

---

## 2. Condition Self-Care Guidance (idea §8, DR-05)

When a triage assessment produces candidate conditions, the user receives general, everyday self-care suggestions and explicit warning signs. This guidance is non-prescriptive and avoids pharmaceutical dosage advice.

### 2.1 Direct Condition Lookup

```python
# Functional lookup by condition ID
guidance = lookup_self_care("common_cold")
assert guidance is not None
assert guidance.condition_id == "common_cold"
assert guidance.condition_name == "Common cold"
print(guidance.general_advice)
# ('Ensure adequate physical rest to support recovery.', ...)
print(guidance.when_to_seek_care)
# ('Fever lasting more than 3 to 4 days, or fever returning after subsiding.', ...)
```

### 2.2 Aggregation and Deduplication for Triage Results

To feed directly into `ResultComposer` or `AssessmentOrchestrator.generate_result()`:

```python
# Aggregate and deduplicate advice across multiple candidate conditions
steps = get_self_care_guidance(["common_cold", "acute_pharyngitis"], max_steps=5)
# Returns a clean tuple of deduplicated supportive steps
```

### 2.3 Self-Care Schema (`SelfCareGuidance`)

| Field | Type | Description |
|---|---|---|
| `condition_id` | `str` | Canonical snake_case condition ID aligned with `conditions.json` |
| `condition_name` | `str` | Human-readable condition display name |
| `general_advice` | `tuple[str, ...]` | Non-prescriptive, everyday supportive self-care steps |
| `when_to_seek_care` | `tuple[str, ...]` | Warning signs and symptoms requiring clinical consultation |
| `monitoring_tips` | `tuple[str, ...]` | Safe self-monitoring suggestions |

---

## 3. Curated Symptom Glossary (FR-18)

The glossary provides empathetic, plain-language explanations of all 100 canonical symptoms at a 6th-to-8th grade reading level, reviewed for clinical safety and safe medical wording.

### 3.1 Direct Definition & Entry Lookup

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

### 3.2 Keyword Search & Ranking

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

### 3.3 Body System Filtering

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

---

## 4. Symptom Normalization (FR-03)

### 4.1 Direct Phrase Normalization

```python
# Returns full NormalizedSymptom schema
result = normalize_symptom("tummy ache")
assert result.canonical_id == "abdominal_pain"
assert result.confidence == 1.0

# Shortcut returning string ID only
canonical_id = normalize_symptom_id("badan dard")
assert canonical_id == "body_aches"
```

### 4.2 Free-Text Mention Extraction

```python
normalizer = get_normalizer()
text = "I have a severe headache and high temperature since yesterday"
matches = normalizer.extract_symptoms_from_text(text)

# Returns non-overlapping TextMatchSpan objects ordered by appearance
```

---

## 5. Medical Safety & Clinical Design Principles (DR-05)

1. **Strictly Non-Diagnostic (`AI_RULES.md §2`):** Text describes supportive measures and symptom management. It never provides definitive diagnostic statements ("You have...", "Diagnosis:").
2. **Zero Medication Prescriptions:** Content never prescribes drugs, specific dosages (e.g. "take 500 mg"), or pharmaceutical treatments.
3. **Emergency Red-Flag Guidance:** Critical conditions (chest pain, stroke signs, breathing difficulty, severe bleeding, anaphylaxis) explicitly highlight immediate emergency services (`112`).
4. **100% Deterministic:** Lookup and normalization use fast, in-memory hash indices with zero LLM dependence in the critical path.
5. **Catalog Parity:** Every condition in `conditions.json` strictly corresponds to an entry in `self_care.json`.
6. **Automated Safety Gate:** All text is audited via `assert_safe_wording()` to guarantee complete adherence to `DR-05`.

---

## 6. Running Tests

Run the full unit test suite for the knowledge service:

```bash
# In the server directory:
pytest tests/unit/knowledge/ -v
```
