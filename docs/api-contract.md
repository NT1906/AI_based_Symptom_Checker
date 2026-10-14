# API Contract: AI-Based Symptom Checker

> **Owner:** Darshil (Assessment Orchestration & Schemas) · **Task:** S0-DAR-1 · **Status:** Sprint 0 Contract Baseline

This document defines the REST API contract for the AI-Based Symptom Checker backend. All client applications (React PWA), server routers, and mock providers must adhere to these specifications.

---

## 1. Global Conventions

1. **Base URL:** `/api/v1`
2. **Wire Format:** All request and response JSON properties use `camelCase` (e.g., `assessmentId`, `riskLevel`). Python backend models use `snake_case` with automated alias generation.
3. **Medical Safety Rules (`AI_RULES.md` §2):**
   - The product is an **informational triage aid**, never a diagnostic tool.
   - Result responses never include diagnostic phrasing ("You have...", "Diagnosis:...").
   - Confidence levels are categorical only: `LIKELY`, `POSSIBLE`, `LESS_LIKELY`. Raw percentages or scores are never exposed to clients.
   - Every result payload includes the mandatory medical safety disclaimer.
   - Red-flag symptoms produce `URGENT` risk, which automatically triggers referral requirements and highlights the emergency number (`112`).
4. **Assessment Lifecycle State Machine:**
   ```text
   START ──► SYMPTOM_COLLECTION ◄──► CLARIFYING ──► CONFIRMING ──► READY ──► ANALYZING ──► COMPLETED
                                                           ▲                     │
                                                           └────── [edit] ───────┘
   ```
   Invalid state transitions return `409 Conflict`.

---

## 2. Common Data Enums & Types

### 2.1 `AssessmentState`
- `START`: Session initialized with valid user consent.
- `SYMPTOM_COLLECTION`: Collecting primary symptoms from user chat.
- `CLARIFYING`: Follow-up clarifying questions (capped at 3 turns).
- `CONFIRMING`: User reviews and confirms extracted symptoms.
- `READY`: Confirmed symptoms are locked for evaluation.
- `ANALYZING`: Deterministic risk engine and ML models processing.
- `COMPLETED`: Triage evaluation complete; results available.
- `ERROR`: Recoverable session failure state.

### 2.2 `RiskLevel`
- `SELF_CARE`: Minor symptoms manageable with home rest, fluids, and monitoring.
- `CONSULT_DOCTOR`: Non-emergency symptoms recommending evaluation by a primary care physician.
- `URGENT`: High-acuity or red-flag symptoms requiring urgent emergency medical attention (`112`).

### 2.3 `ConfidenceLabel`
- `LIKELY`: High symptom-overlap correlation.
- `POSSIBLE`: Moderate correlation requiring clinical consideration.
- `LESS_LIKELY`: Lower correlation or atypical presentation.

### 2.4 Standard Error Response
```json
{
  "code": "INVALID_STATE_TRANSITION",
  "message": "Cannot analyze assessment in state SYMPTOM_COLLECTION. State must be READY.",
  "details": {
    "currentState": "SYMPTOM_COLLECTION",
    "requiredState": "READY"
  },
  "requestId": "req_01j987abc123"
}
```

---

## 3. Endpoints

---

### 3.1 Create Assessment Session

- **Method / Path:** `POST /api/v1/assessments`
- **Description:** Initializes a new assessment session. Requires an active consent record.
- **Allowed States:** N/A (creates new assessment in `START` state).

#### Request Headers
```http
Content-Type: application/json
```

#### Request Body
```json
{
  "consentId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "userId": null
}
```

#### Response (`201 Created`)
```json
{
  "id": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
  "state": "START",
  "consentId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "userId": null,
  "createdAt": "2026-10-12T17:45:00.000Z",
  "updatedAt": "2026-10-12T17:45:00.000Z"
}
```

#### Error Response (`400 Bad Request`)
```json
{
  "code": "CONSENT_REQUIRED",
  "message": "Valid consentId is required to start an assessment.",
  "details": null,
  "requestId": "req_01j987abc124"
}
```

---

### 3.2 Get Assessment Details

- **Method / Path:** `GET /api/v1/assessments/{id}`
- **Description:** Retrieves basic details and current state of an existing assessment.

#### Response (`200 OK`)
```json
{
  "id": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
  "state": "SYMPTOM_COLLECTION",
  "consentId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "userId": null,
  "createdAt": "2026-10-12T17:45:00.000Z",
  "updatedAt": "2026-10-12T17:46:12.000Z"
}
```

#### Error Response (`404 Not Found`)
```json
{
  "code": "ASSESSMENT_NOT_FOUND",
  "message": "Assessment with id 'e4caa1b2-8493-4a16-928e-5b1287c95e1a' not found.",
  "details": null,
  "requestId": "req_01j987abc125"
}
```

---

### 3.3 Get Assessment State Snapshot

- **Method / Path:** `GET /api/v1/assessments/{id}/state`
- **Description:** Returns the orchestration state, current symptom count, and clarification loop counter.

#### Response (`200 OK`)
```json
{
  "assessmentId": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
  "state": "CLARIFYING",
  "symptoms": [
    {
      "id": "c1f67f08-3e4b-4b2e-a579-2425dc595cf2",
      "name": "headache",
      "severity": "MODERATE",
      "duration": {
        "value": 2.0,
        "unit": "DAY"
      },
      "bodyLocation": "temples",
      "source": "AI_EXTRACTED",
      "extractionConfidence": 0.94
    }
  ],
  "clarificationCount": 1,
  "maxClarifications": 3
}
```

---

### 3.4 Send Assessment Message

- **Method / Path:** `POST /api/v1/assessments/{id}/messages`
- **Description:** Appends a user message to the conversation, invokes AI extraction/clarification orchestration, and transitions the state machine.
- **Allowed States:** `START`, `SYMPTOM_COLLECTION`, `CLARIFYING`.

#### Request Body
```json
{
  "content": "I have had a throbbing headache for 2 days around my temples, and I feel nauseous."
}
```

#### Response (`200 OK`)
```json
{
  "message": {
    "id": "7f8b9e12-4211-4f81-9b12-9c3f81e7d23a",
    "assessmentId": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
    "position": 1,
    "role": "user",
    "content": "I have had a throbbing headache for 2 days around my temples, and I feel nauseous.",
    "messageType": "TEXT",
    "createdAt": "2026-10-12T17:46:12.000Z"
  },
  "assistantMessage": {
    "id": "8a9c0e23-5322-4a92-ac23-0d4a92f8e34b",
    "assessmentId": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
    "position": 2,
    "role": "assistant",
    "content": "Have you noticed any sensitivity to bright light or sound along with the headache?",
    "messageType": "CLARIFICATION",
    "createdAt": "2026-10-12T17:46:14.000Z"
  },
  "nextState": "CLARIFYING"
}
```

#### Error Response (`409 Conflict`)
```json
{
  "code": "INVALID_STATE",
  "message": "Cannot accept new messages in state 'COMPLETED'.",
  "details": {
    "currentState": "COMPLETED"
  },
  "requestId": "req_01j987abc126"
}
```

---

### 3.5 Get Conversation Messages

- **Method / Path:** `GET /api/v1/assessments/{id}/messages`
- **Description:** Returns the ordered history of dialogue messages for an assessment.

#### Response (`200 OK`)
```json
[
  {
    "id": "7f8b9e12-4211-4f81-9b12-9c3f81e7d23a",
    "assessmentId": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
    "position": 0,
    "role": "user",
    "content": "I have a throbbing headache for 2 days.",
    "messageType": "TEXT",
    "createdAt": "2026-10-12T17:46:12.000Z"
  },
  {
    "id": "8a9c0e23-5322-4a92-ac23-0d4a92f8e34b",
    "assessmentId": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
    "position": 1,
    "role": "assistant",
    "content": "Have you experienced any nausea or sensitivity to bright lights?",
    "messageType": "CLARIFICATION",
    "createdAt": "2026-10-12T17:46:14.000Z"
  }
]
```

---

### 3.6 Get Extracted Symptoms

- **Method / Path:** `GET /api/v1/assessments/{id}/symptoms`
- **Description:** Retrieves the list of currently recognized symptoms for the assessment.

#### Response (`200 OK`)
```json
[
  {
    "id": "c1f67f08-3e4b-4b2e-a579-2425dc595cf2",
    "name": "headache",
    "severity": "MODERATE",
    "duration": {
      "value": 2.0,
      "unit": "DAY"
    },
    "bodyLocation": "temples",
    "source": "AI_EXTRACTED",
    "extractionConfidence": 0.94
  },
  {
    "id": "d2e78a19-4f5c-5c3f-b680-3536ed606da3",
    "name": "nausea",
    "severity": "MILD",
    "duration": null,
    "bodyLocation": "abdomen",
    "source": "AI_EXTRACTED",
    "extractionConfidence": 0.89
  }
]
```

---

### 3.7 Confirm / Update Symptoms

- **Method / Path:** `PATCH /api/v1/assessments/{id}/symptoms`
- **Description:** Allows the user to confirm, edit, add, or remove symptoms prior to triage evaluation.
- **Allowed States:** `CONFIRMING`, `SYMPTOM_COLLECTION`.

#### Request Body
```json
{
  "symptoms": [
    {
      "id": "c1f67f08-3e4b-4b2e-a579-2425dc595cf2",
      "name": "headache",
      "severity": "SEVERE",
      "duration": {
        "value": 2.0,
        "unit": "DAY"
      },
      "bodyLocation": "temples",
      "source": "USER_CONFIRMED"
    },
    {
      "name": "photophobia",
      "severity": "MODERATE",
      "duration": {
        "value": 1.0,
        "unit": "DAY"
      },
      "bodyLocation": "eyes",
      "source": "USER_CONFIRMED"
    }
  ]
}
```

#### Response (`200 OK`)
```json
[
  {
    "id": "c1f67f08-3e4b-4b2e-a579-2425dc595cf2",
    "name": "headache",
    "severity": "SEVERE",
    "duration": {
      "value": 2.0,
      "unit": "DAY"
    },
    "bodyLocation": "temples",
    "source": "USER_CONFIRMED",
    "extractionConfidence": null
  },
  {
    "id": "e3f89b20-5a6d-6d4a-c791-4647fe717eb4",
    "name": "photophobia",
    "severity": "MODERATE",
    "duration": {
      "value": 1.0,
      "unit": "DAY"
    },
    "bodyLocation": "eyes",
    "source": "USER_CONFIRMED",
    "extractionConfidence": null
  }
]
```

---

### 3.8 Trigger Assessment Analysis

- **Method / Path:** `POST /api/v1/assessments/{id}/analyze`
- **Description:** Submits the confirmed symptoms to the deterministic risk engine and condition predictor.
- **Allowed States:** Precondition requires state `READY` (or `CONFIRMING`). Transitions state to `ANALYZING` and then `COMPLETED`.

#### Request Body
```json
{}
```

#### Response (`200 OK`)
```json
{
  "assessmentId": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
  "state": "COMPLETED",
  "resultAvailable": true
}
```

#### Error Response (`409 Conflict`)
```json
{
  "code": "INVALID_STATE_TRANSITION",
  "message": "Cannot trigger analysis when state is 'SYMPTOM_COLLECTION'. State must be 'READY'.",
  "details": {
    "currentState": "SYMPTOM_COLLECTION"
  },
  "requestId": "req_01j987abc127"
}
```

---

### 3.9 Get Assessment Result

- **Method / Path:** `GET /api/v1/assessments/{id}/result`
- **Description:** Retrieves the final triage outcome, possible conditions, and referral recommendations.
- **Allowed States:** Assessment must be in `COMPLETED` state.

#### Response: Non-Emergency / Consult Doctor (`200 OK`)
```json
{
  "assessmentId": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
  "riskLevel": "CONSULT_DOCTOR",
  "conditions": [
    {
      "name": "Migraine without aura",
      "confidence": "LIKELY",
      "rank": 1,
      "icd10Code": "G43.0",
      "specialty": "Neurology",
      "description": "A recurring type of headache causing moderate to severe throbbing pain."
    },
    {
      "name": "Tension-type headache",
      "confidence": "POSSIBLE",
      "rank": 2,
      "icd10Code": "G44.2",
      "specialty": "General Medicine",
      "description": "Diffuse, mild to moderate pain described as a tight band around the head."
    }
  ],
  "guidance": [
    "Rest in a quiet, dark environment during episodes.",
    "Keep a headache symptom diary noting triggers, duration, and pain severity.",
    "Schedule an appointment with a general physician for clinical evaluation."
  ],
  "referral": {
    "required": true,
    "specialty": "Neurology",
    "reason": "Moderate to severe recurring headache symptoms with sensory sensitivity.",
    "emergencyNumber": null
  },
  "limitations": [
    "Informational evaluation based on self-reported symptoms.",
    "Physical neurological examination has not been performed."
  ],
  "modelVersion": "1.0.0",
  "disclaimer": "This is not a medical diagnosis. Always consult a qualified healthcare professional.",
  "createdAt": "2026-10-12T17:48:30.000Z"
}
```

#### Response: Red-Flag / Urgent Emergency (`200 OK`)
```json
{
  "assessmentId": "b8a1c920-7f22-4b89-a212-3c8192a01d5e",
  "riskLevel": "URGENT",
  "conditions": [
    {
      "name": "Acute coronary syndrome",
      "confidence": "POSSIBLE",
      "rank": 1,
      "icd10Code": "I24.9",
      "specialty": "Emergency Medicine",
      "description": "Symptoms consistent with acute reduction of blood flow to the heart."
    }
  ],
  "guidance": [
    "Call 112 immediately or proceed to the nearest emergency room.",
    "Do not drive yourself to the emergency hospital.",
    "Rest comfortably while waiting for emergency responders."
  ],
  "referral": {
    "required": true,
    "specialty": "Emergency Medicine",
    "reason": "Red-flag symptom identified: severe crushing chest pain.",
    "emergencyNumber": "112"
  },
  "limitations": [
    "Triage algorithm automatically escalated to URGENT based on critical red-flag rules."
  ],
  "modelVersion": "1.0.0",
  "disclaimer": "This is not a medical diagnosis. Always consult a qualified healthcare professional.",
  "createdAt": "2026-10-12T17:49:10.000Z"
}
```

---

### 3.10 Service Health Check

- **Method / Path:** `GET /api/v1/health`
- **Description:** Verifies service uptime and running deployment version.

#### Response (`200 OK`)
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```
