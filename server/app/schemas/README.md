# Schemas (`server/app/schemas/`)

## Purpose
This package defines the canonical Pydantic v2 API contracts for the AI-Based Symptom Checker. These models enforce type safety, input validation, serialization to `camelCase` on the wire, and compliance with non-negotiable medical safety rules (no diagnostic statements, deterministic risk levels, categorical confidence labels, and mandatory disclaimers).

## Public Interface
- **Enums**:
  - `AssessmentState`: Lifecycle states (`START`, `SYMPTOM_COLLECTION`, `CLARIFYING`, `CONFIRMING`, `READY`, `ANALYZING`, `COMPLETED`, `ERROR`).
  - `RiskLevel`: Triage risk tiers (`SELF_CARE`, `CONSULT_DOCTOR`, `URGENT`).
  - `ConfidenceLabel`: Categorical confidence (`LIKELY`, `POSSIBLE`, `LESS_LIKELY`).
  - `Severity`, `DurationUnit`, `SymptomSource`, `MessageRole`, `MessageType`.
- **Domain Models & Schemas**:
  - `Symptom`, `SymptomCreate`, `SymptomUpdate`, `SymptomRead`, `Duration`
  - `Message`, `MessageCreate`, `MessageRead`
  - `Condition`
  - `AssessmentResult`, `ReferralInfo`
  - `AssessmentCreate`, `AssessmentRead`, `AssessmentStateResponse`

## How to Test
Run the schema unit test suite:
```bash
pytest server/tests/unit/schemas/
```
