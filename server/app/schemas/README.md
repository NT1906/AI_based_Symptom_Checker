# Schemas (`server/app/schemas/`)

**Owner:** Darshil (Assessment Orchestration & Schemas) · **Task:** S0-DAR-1, S2-DAR-7 · **Requirements:** NFR-03

## Purpose
This package defines the canonical Pydantic v2 API contracts for the AI-Based Symptom Checker. These models enforce type safety, input validation, serialization to `camelCase` on the wire, mass assignment prevention, and compliance with non-negotiable medical safety rules (no diagnostic statements, deterministic risk levels, categorical confidence labels, and mandatory disclaimers).

## Input Validation & Hardening (S2-DAR-7, NFR-03)
- **`RequestSchemaBase`**: Inherited by all client request payloads. Configured with:
  - `extra="forbid"`: Rejects unknown / unexpected attributes with 422 Unprocessable Entity (mass-assignment defense).
  - `str_strip_whitespace=True`: Automatically strips leading and trailing whitespace from string inputs.
- **Null Byte Rejection**: All string fields reject null bytes (`\x00`) to prevent CWE-158 / string termination attacks.
- **String Length Limits**: Strict character bounds enforced on messages (1–4000), symptom names (1–128), body locations (1–128), and condition names (1–256).
- **Batch Size Bounds**: Symptom batch updates are strictly bounded (1–50 symptoms); user profile chronic condition lists are strictly bounded (max 50 conditions).
- **Numeric Bounds**: `Duration.value` is bounded to `0.0 <= value <= 36500.0` with `allow_inf_nan=False` to disallow NaN and infinite floats.

## Public Interface
- **Enums**:
  - `AssessmentState`: Lifecycle states (`START`, `SYMPTOM_COLLECTION`, `CLARIFYING`, `CONFIRMING`, `READY`, `ANALYZING`, `COMPLETED`, `ERROR`).
  - `RiskLevel`: Triage risk tiers (`SELF_CARE`, `CONSULT_DOCTOR`, `URGENT`).
  - `ConfidenceLabel`: Categorical confidence (`LIKELY`, `POSSIBLE`, `LESS_LIKELY`).
  - `Severity`, `DurationUnit`, `SymptomSource`, `MessageRole`, `MessageType`.
- **Domain Models & Schemas**:
  - `SchemaBase`, `RequestSchemaBase`
  - `Symptom`, `SymptomCreate`, `SymptomUpdate`, `SymptomRead`, `Duration`, `UpdateSymptomsRequest`
  - `Message`, `MessageCreate`, `MessageRead`
  - `ProfileContext`, `ProfileCreate`, `ProfileRead`, `ProfileUpdate`, `AgeBand`, `BiologicalSex`
  - `Condition`
  - `AssessmentResult`, `ReferralInfo`
  - `AssessmentCreate`, `AssessmentRead`, `AssessmentStateResponse`, `ClaimAssessmentRequest`, `ClaimAssessmentResponse`, `ProcessResult`

## How to Test
Run the schema unit test suite:
```bash
pytest server/tests/unit/schemas/
```
