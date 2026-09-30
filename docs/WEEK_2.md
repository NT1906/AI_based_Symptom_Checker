# AI-Based Symptom Checker — Week 2 Development Roadmap

> **Stack update (30 Sep 2026):** the backend is now **FastAPI (Python)**, not Node/Express/Prisma, and the frontend is a **PWA on Vercel**. See [tech-stack.md](tech-stack.md) and [SPRINT_PLAN.md](SPRINT_PLAN.md). The goals and flows below still apply; translate the code snippets into their FastAPI / SQLAlchemy / Pydantic / pytest equivalents.


**Project:** AI-Based Symptom Checker  
**Duration:** Week 2 of 3  
**Team Size:** 10 members  
**Dependency:** Week 1 must be integrated and tagged before Week 2 begins.

---

# 1. Week 2 Goal

Week 1 established the foundation:

```text
Chat
 ↓
Symptom Extraction
 ↓
Normalization
 ↓
Clarification
 ↓
Confirmation
 ↓
Structured State
 ↓
Baseline Prediction
 ↓
Basic Result
```

Week 2 turns that foundation into a **more complete, robust, testable assessment system**.

The main Week 2 objective is:

```text
Week 1 Prototype
       ↓
Stronger AI/NLP
       ↓
Improved Prediction
       ↓
Risk Classification
       ↓
Image Analysis
       ↓
Account + Guest Handling
       ↓
Privacy/Data Controls
       ↓
Better Result UX
       ↓
Error Recovery
       ↓
Automated Testing
       ↓
Integrated System
```

---

# 2. Week 2 Definition of Done

At the end of Week 2, a user should be able to:

```text
Open Application
      ↓
Continue as Guest OR Sign In
      ↓
Start Assessment
      ↓
Describe Symptoms Naturally
      ↓
System Extracts + Normalizes
      ↓
System Asks Relevant Clarifications
      ↓
User Confirms / Edits
      ↓
Optional Image Upload
      ↓
Image Validation + Analysis Interface
      ↓
Structured Assessment
      ↓
Condition Candidate Generation
      ↓
Risk Classification
      ↓
Safety Validation
      ↓
Result
      ↓
Low Risk → General Self-Care Guidance
Higher Risk → Relevant Doctor/Search Referral
      ↓
Assessment Saved if User Consents
      ↓
User Can Restart / View Appropriate History
```

### Week 2 must improve

- AI extraction accuracy
- clarification quality
- structured symptom quality
- prediction pipeline
- risk-level logic
- result presentation
- image pipeline
- guest/account behavior
- privacy controls
- error handling
- test coverage
- observability/logging
- integration reliability

---

# 3. Week 2 Architecture

```text
                         USER
                           │
                           ▼
                  ┌─────────────────┐
                  │   CHAT CLIENT   │
                  └────────┬────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      TEXT SYMPTOMS                  IMAGE INPUT
             │                           │
             ▼                           ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ Symptom NLP     │          │ Image Pipeline  │
    │                 │          │                 │
    │ Extraction      │          │ Validation      │
    │ Normalization   │          │ Quality Check   │
    │ Missing Info    │          │ Preprocessing   │
    │ Clarification   │          │ Analyzer        │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └─────────────┬──────────────┘
                           ▼
                ┌────────────────────┐
                │ Structured State   │
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │ Safety Validation  │
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │ Prediction Engine  │
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │ Risk Classification│
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │ Result Composer    │
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │ Result UI          │
                └────────────────────┘
```

Supporting systems:

```text
Authentication
Privacy / Consent
Database
Object Storage
Logging
Testing
Monitoring
```

---

# 4. Week 2 Core Principles

## 4.1 Do not turn the system into a general chatbot

The conversation remains assessment-focused.

```text
Allowed:
"I have a headache."

Allowed:
"How long have you had it?"

Not the product goal:
"Tell me a joke."

Not the product goal:
"Explain quantum computing."
```

---

## 4.2 AI is not the medical authority

Separate:

```text
Language Understanding
        ↓
Structured Information
        ↓
Prediction
        ↓
Risk Logic
        ↓
Safety Validation
        ↓
User Result
```

Do not let a single unconstrained LLM response directly determine the final user-facing result.

---

## 4.3 Do not invent missing information

Never convert:

```text
"I feel bad."
```

into:

```text
FEVER = 39°C
```

if the user never provided a temperature.

---

## 4.4 Uncertainty must remain visible

Use:

```text
Likely
Possible
Less likely
```

Do not imply:

```text
100% diagnosis
73.2% medical certainty
```

---

## 4.5 Safety takes priority over convenience

If information is incomplete or uncertain:

```text
Do not silently downgrade risk.
```

The project specification states that uncertain situations should err toward the safer/higher risk classification.

---

# 4.6 Week 2 Implementation Architecture

Week 2 introduces several cross-cutting concerns that must be architecturally sound before feature work begins.

## Authentication and Session Management

Guest and authenticated flows must coexist without duplicating assessment logic.

### JWT authentication middleware

```typescript
// server/src/middleware/auth.ts
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { AppError } from '../utils/AppError';

export interface AuthPayload {
  userId: string;
  email: string;
  iat: number;
  exp: number;
}

export interface AuthRequest extends Request {
  user?: AuthPayload;
  sessionId: string;
}

/**
 * Extracts JWT if present. Does NOT reject unauthenticated requests.
 * Use `requireAuth` for endpoints that require login.
 */
export function optionalAuth(req: AuthRequest, _res: Response, next: NextFunction) {
  const token = req.cookies?.token || req.headers.authorization?.replace('Bearer ', '');
  if (token) {
    try {
      req.user = jwt.verify(token, process.env.JWT_SECRET!) as AuthPayload;
    } catch {
      // Invalid/expired token — treat as guest
    }
  }
  // Always ensure a session ID exists (for guests)
  req.sessionId = req.user?.userId || (req.cookies?.sessionId as string) || generateSessionId();
  next();
}

/**
 * Rejects unauthenticated requests with 401.
 */
export function requireAuth(req: AuthRequest, _res: Response, next: NextFunction) {
  if (!req.user) throw AppError.unauthorized('Authentication required');
  next();
}

function generateSessionId(): string {
  return `guest_${crypto.randomUUID()}`;
}
```

### Assessment ownership guard

```typescript
// server/src/middleware/assessmentOwnership.ts
import { AuthRequest } from './auth';
import { prisma } from '../config/database';
import { AppError } from '../utils/AppError';

export async function assertAssessmentOwnership(
  req: AuthRequest,
  assessmentId: string,
): Promise<void> {
  const assessment = await prisma.assessment.findUnique({
    where: { id: assessmentId },
    select: { userId: true, sessionId: true },
  });

  if (!assessment) throw AppError.notFound('Assessment');

  const isOwner = req.user
    ? assessment.userId === req.user.userId
    : assessment.sessionId === req.sessionId;

  if (!isOwner) throw AppError.forbidden('You do not own this assessment');
}
```

## Registration and Login

```typescript
// server/src/routes/auth.routes.ts
import { Router } from 'express';
import { z } from 'zod';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { prisma } from '../config/database';

const router = Router();

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(128),
  age: z.number().int().min(1).max(150).optional(),
  sex: z.enum(['MALE', 'FEMALE', 'OTHER']).optional(),
});

router.post('/auth/register', async (req, res) => {
  const body = registerSchema.parse(req.body);
  const existing = await prisma.user.findUnique({ where: { email: body.email } });
  if (existing) throw AppError.conflict('EMAIL_EXISTS', 'Email already registered');

  const passwordHash = await bcrypt.hash(body.password, 12);
  const user = await prisma.user.create({
    data: { email: body.email, passwordHash, age: body.age, sex: body.sex },
  });

  const token = jwt.sign(
    { userId: user.id, email: user.email },
    process.env.JWT_SECRET!,
    { expiresIn: process.env.JWT_EXPIRES_IN || '7d' },
  );

  res.cookie('token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });

  res.status(201).json({ success: true, data: { userId: user.id, email: user.email } });
});

export { router as authRouter };
```

## Caching Strategy

For Week 2, introduce in-memory caching (Node.js LRU cache) for expensive lookups. Redis can be added in Week 3 if needed.

```typescript
// server/src/utils/cache.ts
import { LRUCache } from 'lru-cache';

export const symptomDictionaryCache = new LRUCache<string, string>({
  max: 500,          // Max 500 canonical symptom entries
  ttl: 60 * 60_000,  // 1 hour TTL
});

export const predictionCache = new LRUCache<string, unknown>({
  max: 100,
  ttl: 5 * 60_000,   // 5 minute TTL for prediction results
});
```

## Structured Observability

Every service call must produce structured logs with correlation IDs for debugging across the full request lifecycle.

```typescript
// server/src/config/logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: process.env.NODE_ENV === 'development'
    ? { target: 'pino-pretty', options: { colorize: true } }
    : undefined,
  redact: {
    paths: ['req.headers.authorization', 'req.headers.cookie'],
    censor: '[REDACTED]',
  },
});

// Usage in services:
// logger.info({ assessmentId, event: 'extraction_complete', symptomCount: 3, latencyMs: 450 });
// logger.warn({ assessmentId, event: 'ai_retry', attempt: 2, reason: 'timeout' });
// logger.error({ assessmentId, event: 'prediction_failed', error: err.message });
```

### Structured log events to implement

| Event | Level | When |
|---|---|---|
| `assessment_created` | info | New assessment started |
| `message_received` | info | User sends a message |
| `extraction_complete` | info | AI extraction returns structured symptoms |
| `extraction_failed` | error | AI extraction times out or returns invalid JSON |
| `clarification_generated` | info | System generates a follow-up question |
| `confirmation_accepted` | info | User confirms symptoms |
| `prediction_complete` | info | Prediction engine returns candidates |
| `risk_calculated` | info | Risk engine returns classification |
| `red_flag_detected` | warn | Safety-critical symptom pattern detected |
| `image_uploaded` | info | Image received and validated |
| `image_quality_low` | warn | Image failed quality checks |
| `assessment_completed` | info | Full assessment flow finished |
| `ai_retry` | warn | AI call retried due to failure |
| `unauthorized_access` | warn | Ownership check failed |

## Rate Limiting

Protect expensive endpoints from abuse, especially AI-calling endpoints.

```typescript
// server/src/middleware/rateLimiter.ts
import rateLimit from 'express-rate-limit';

export const messageRateLimiter = rateLimit({
  windowMs: 60_000,     // 1 minute
  max: 20,              // 20 messages per minute per IP
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    error: { code: 'RATE_LIMITED', message: 'Too many requests. Please wait.' },
  },
});

export const analysisRateLimiter = rateLimit({
  windowMs: 60_000,
  max: 5,               // 5 analysis requests per minute
  message: {
    success: false,
    error: { code: 'RATE_LIMITED', message: 'Analysis rate limit exceeded.' },
  },
});

export const authRateLimiter = rateLimit({
  windowMs: 15 * 60_000, // 15 minutes
  max: 10,               // 10 login attempts per 15 minutes
  message: {
    success: false,
    error: { code: 'RATE_LIMITED', message: 'Too many login attempts.' },
  },
});
```

## Concrete NLP Prompt Engineering

The extraction prompt must produce deterministic, schema-compliant JSON. This is the most critical prompt in the system.

### Symptom extraction prompt (v2)

```text
# ai/prompts/extraction.v2.txt

You are a medical symptom extraction assistant. Your ONLY job is to extract
structured symptom information from user messages.

RULES:
1. Extract ONLY symptoms the user explicitly mentioned.
2. Do NOT invent symptoms, severity, duration, or body locations.
3. If information is missing, set the field to null — do NOT guess.
4. Map common language to canonical symptom names using the provided dictionary.
5. Support multiple symptoms in one message.
6. Severity mapping:
   - "really bad", "terrible", "worst" → SEVERE
   - "pretty bad", "moderate", "noticeable" → MODERATE
   - "slight", "mild", "little bit" → MILD
   - If unclear → UNKNOWN
7. Duration mapping:
   - "since yesterday" → { value: 1, unit: "DAY" }
   - "for a couple days" → { value: 2, unit: "DAY" }
   - "for a week" → { value: 1, unit: "WEEK" }
   - If unclear → null

PREVIOUS CONVERSATION CONTEXT:
{conversation_history}

CURRENT USER MESSAGE:
{user_message}

RESPOND WITH VALID JSON ONLY. No explanation, no markdown.

{
  "symptoms": [
    {
      "name": "CANONICAL_NAME",
      "severity": "MILD|MODERATE|SEVERE|UNKNOWN",
      "duration": { "value": number, "unit": "HOUR|DAY|WEEK|MONTH" } | null,
      "body_location": "string" | null
    }
  ],
  "associated_symptoms": [],
  "requires_clarification": true | false,
  "clarification_reason": "string" | null
}
```

### Clarification prompt (v2)

```text
# ai/prompts/clarification.v2.txt

You are generating a follow-up question for a symptom assessment.

CURRENT STRUCTURED STATE:
{structured_state_json}

ALREADY ASKED QUESTIONS:
{previously_asked_questions}

RULES:
1. Ask about the MOST IMPORTANT missing information first.
2. Safety-critical information takes priority (e.g., chest pain duration > headache location).
3. Do NOT re-ask any question from the "already asked" list.
4. Maximum total questions: 3. Current count: {clarification_count}.
5. If count >= 3, set "should_ask" to false.
6. Ask ONE question at a time.
7. Use conversational, non-clinical language.

RESPOND WITH JSON:
{
  "should_ask": true | false,
  "question": "string",
  "question_type": "DURATION|SEVERITY|LOCATION|ASSOCIATED|CONTEXT",
  "target_symptom": "CANONICAL_NAME" | null
}
```

### AI response validation

```typescript
// server/src/services/ai/aiResponseValidator.ts
import { z } from 'zod';
import { logger } from '../../config/logger';

const extractionResponseSchema = z.object({
  symptoms: z.array(z.object({
    name: z.string().min(1).max(100),
    severity: z.enum(['MILD', 'MODERATE', 'SEVERE', 'UNKNOWN']),
    duration: z.object({
      value: z.number().positive().max(365),
      unit: z.enum(['HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR']),
    }).nullable(),
    body_location: z.string().max(100).nullable(),
  })).max(10),  // Cap at 10 symptoms per extraction
  associated_symptoms: z.array(z.string()).max(10),
  requires_clarification: z.boolean(),
  clarification_reason: z.string().max(500).nullable(),
});

export function validateExtractionResponse(raw: unknown, assessmentId: string) {
  const result = extractionResponseSchema.safeParse(raw);
  if (!result.success) {
    logger.error({
      assessmentId,
      event: 'extraction_validation_failed',
      errors: result.error.flatten(),
      rawResponse: JSON.stringify(raw).slice(0, 500),
    });
    return null;
  }
  return result.data;
}
```

## Assessment Orchestration Service

The orchestrator is the single entry point for processing a user message. It coordinates AI extraction, state management, and response generation.

```typescript
// server/src/services/assessment/assessmentOrchestrator.ts
import { prisma } from '../../config/database';
import { extractSymptoms } from '../ai/extractionService';
import { generateClarification } from '../ai/clarificationService';
import { validateExtractionResponse } from '../ai/aiResponseValidator';
import { assertValidTransition } from './stateGuard';
import { logger } from '../../config/logger';

export async function processMessage(
  assessmentId: string,
  userMessage: string,
  sessionId: string,
): Promise<ProcessMessageResult> {
  const startTime = Date.now();

  // 1. Load current assessment
  const assessment = await prisma.assessment.findUniqueOrThrow({
    where: { id: assessmentId },
    include: { symptoms: true, messages: { orderBy: { createdAt: 'asc' } } },
  });

  // 2. Save user message
  await prisma.assessmentMessage.create({
    data: {
      assessmentId,
      sender: 'USER',
      content: userMessage,
      messageType: 'TEXT',
    },
  });

  // 3. Call AI extraction with conversation context
  const conversationHistory = assessment.messages
    .map(m => `${m.sender}: ${m.content}`)
    .join('\n');

  const rawExtraction = await extractSymptoms(userMessage, conversationHistory);
  const extraction = validateExtractionResponse(rawExtraction, assessmentId);

  if (!extraction) {
    // AI returned invalid response — safe fallback
    return {
      type: 'ERROR',
      message: 'I had trouble understanding that. Could you try rephrasing your symptoms?',
    };
  }

  // 4. Upsert symptoms into database
  for (const symptom of extraction.symptoms) {
    await prisma.assessmentSymptom.upsert({
      where: { assessmentId_name: { assessmentId, name: symptom.name } },
      create: {
        assessmentId,
        name: symptom.name,
        severity: symptom.severity,
        durationValue: symptom.duration?.value ?? null,
        durationUnit: symptom.duration?.unit ?? null,
        bodyLocation: symptom.body_location,
        source: 'AI_EXTRACTED',
      },
      update: {
        severity: symptom.severity,
        durationValue: symptom.duration?.value ?? null,
        durationUnit: symptom.duration?.unit ?? null,
        bodyLocation: symptom.body_location,
      },
    });
  }

  // 5. Determine next action
  const currentClarificationCount = assessment.messages
    .filter(m => m.messageType === 'CLARIFICATION').length;

  if (extraction.requires_clarification && currentClarificationCount < 3) {
    assertValidTransition(assessment.state, 'CLARIFYING');
    const clarification = await generateClarification(assessmentId, currentClarificationCount);

    await prisma.assessment.update({
      where: { id: assessmentId },
      data: { state: 'CLARIFYING' },
    });

    logger.info({
      assessmentId,
      event: 'clarification_generated',
      latencyMs: Date.now() - startTime,
    });

    return { type: 'CLARIFICATION', message: clarification.question };
  }

  // 6. Move to confirmation
  assertValidTransition(assessment.state, 'CONFIRMING');
  await prisma.assessment.update({
    where: { id: assessmentId },
    data: { state: 'CONFIRMING' },
  });

  const allSymptoms = await prisma.assessmentSymptom.findMany({
    where: { assessmentId },
  });

  logger.info({
    assessmentId,
    event: 'moving_to_confirmation',
    symptomCount: allSymptoms.length,
    latencyMs: Date.now() - startTime,
  });

  return { type: 'CONFIRMATION', symptoms: allSymptoms };
}
```

---

# 5. Week 2 Team Ownership

| Member | Week 2 Primary Ownership |
|---|---|
| Nishith | Advanced symptom NLP + clarification quality + AI guardrails |
| Nisarg | Prediction improvement + risk model + evaluation |
| Vivek | Full assessment frontend + account/guest UI integration |
| Darshil | Result UX + image interaction + responsive polish |
| Kavya | Backend business logic + auth/session + referral APIs |
| Harsh | Database refinement + history + retention/data controls |
| Mann | Image analysis prototype + image quality/model pipeline |
| Mohit | Full QA + AI evaluation + security/safety testing |
| Dimple | Privacy/consent + safety UX + accessibility + usability |
| Rutva | System integration + reliability + deployment/staging |

---

# 6. Nishith — AI/ML Lead

## Week 2 Goal

Upgrade the Week 1 symptom-understanding engine from a basic prototype into a more reliable structured extraction and clarification pipeline.

```text
User Message
    ↓
Intent Check
    ↓
Symptom Extraction
    ↓
Normalization
    ↓
Context Resolution
    ↓
Contradiction Detection
    ↓
Missing Information
    ↓
Clarification
    ↓
Validated Structured State
```

---

## Day 1 — Review Week 1 AI Errors

Collect Week 1 failures.

Create categories:

```text
EXTRACTION_ERROR
NORMALIZATION_ERROR
SEVERITY_ERROR
DURATION_ERROR
LOCATION_ERROR
ASSOCIATED_SYMPTOM_ERROR
MISSING_INFO_ERROR
DUPLICATE_QUESTION
WRONG_CLARIFICATION
UNSAFE_OUTPUT
```

Create an error dataset.

Example:

```json
{
  "input": "my head has been hurting badly for a couple days",
  "expected": {
    "symptom": "HEADACHE",
    "severity": "SEVERE",
    "duration": {
      "value": 2,
      "unit": "DAY"
    }
  }
}
```

### Deliverables

- Week 1 error report
- categorized failure dataset
- prioritized AI issues
- improvement plan

---

## Day 2 — Context-Aware Extraction

Improve extraction across multiple messages.

Example:

```text
User:
"I have a headache."

System:
"How long?"

User:
"Since yesterday."

System:
"How severe?"

User:
"Pretty bad."
```

Final state must become:

```text
HEADACHE
duration = 1 DAY
severity = SEVERE
```

The system must combine information across turns instead of treating each message independently.

---

## Day 3 — Contradiction and Correction Handling

Handle:

```text
"I have a headache."

Later:
"Actually, it isn't a headache. It's mostly pressure around my eyes."
```

The latest user correction should be reflected in the structured state.

Detect contradictions such as:

```text
duration = 1 day
later = 3 weeks
```

Do not silently choose one.

Possible system behavior:

```text
"I want to make sure I understood that correctly. Has this been happening for 1 day or about 3 weeks?"
```

---

## Day 4 — Better Clarification Selection

Create a scoring/prioritization system for questions.

Concept:

```text
Question Priority =
Safety Importance
+
Prediction Information Gain
+
Missingness
-
Already Asked
```

Do not implement unnecessary mathematical complexity if a deterministic scoring system is sufficient.

The important result is:

```text
Most useful unanswered question
        ↓
Ask it
```

instead of:

```text
Ask random question
```

---

## Day 5 — Prompt and Schema Hardening

Move prompts/configuration into versioned files.

Example:

```text
ai/
├── prompts/
│   ├── extraction.v2.txt
│   ├── clarification.v2.txt
│   └── safety.v2.txt
├── schemas/
│   ├── symptom-state.json
│   └── ai-response.json
└── validators/
```

Add:

- strict output schema
- enum validation
- length limits
- question-count limit
- unsupported-claim detection

---

## Day 6 — Out-of-Scope Detection

Detect requests outside the product purpose.

Examples:

```text
"Write my resume."
"Tell me a joke."
"Give me a prescription."
"Tell me exactly what disease I have."
```

The system should redirect to the assessment scope or provide a safe boundary response.

This is not a general chatbot feature.

---

## Day 7 — AI Regression Suite

Run all Week 1 cases plus Week 2 cases.

Target categories:

```text
Simple
Multiple symptoms
Long descriptions
Typos
Synonyms
Ambiguous
Contradictory
Correction
Multi-turn
Out-of-scope
Safety-sensitive
```

### Final Nishith deliverables

- context-aware extraction
- contradiction handling
- improved clarification engine
- versioned prompts
- strict schemas
- out-of-scope handling
- AI regression dataset
- AI evaluation report

---

# 7. Nisarg — Prediction + Risk Engine

## Week 2 Goal

Turn the Week 1 baseline prediction into a more structured candidate-ranking and risk-classification pipeline.

```text
Structured Symptoms
        ↓
Feature Engineering
        ↓
Candidate Generation
        ↓
Candidate Ranking
        ↓
Confidence Label
        ↓
Risk Assessment
        ↓
Safety Rule
        ↓
Result
```

---

## Day 1 — Baseline Error Analysis

Analyze Week 1 predictions.

Create:

```text
Correct
Incorrect
Ambiguous
Insufficient Information
No Result
Unsafe Result
```

Build a confusion/error report.

Identify:

- frequently confused conditions
- symptoms that contribute little
- missing features
- class imbalance
- noisy labels

---

## Day 2 — Feature Pipeline Improvement

Improve feature representation.

Potential features:

```text
symptom presence
symptom count
severity
duration
body location
associated symptoms
age
sex
existing conditions
image_available
```

Every feature must be traceable to the structured state.

Avoid hidden features.

---

## Day 3 — Candidate Ranking

Build:

```text
Condition A → score
Condition B → score
Condition C → score
...
```

Then:

```text
Sort
 ↓
Top candidates
 ↓
Remove invalid/unsupported candidates
 ↓
Return top 2–3
```

The prediction engine should not return dozens of conditions to the user.

---

## Day 4 — Confidence Mapping

Define deterministic mapping:

```text
Model / rule score
        ↓
Confidence band
        ↓
Likely / Possible / Less likely
```

Document thresholds.

Do not present these labels as clinically validated probabilities.

---

## Day 5 — Risk Classification

Create a separate risk engine.

Conceptual input:

```text
Symptoms
Severity
Associated symptoms
Age/context
Candidate conditions
Prediction uncertainty
Red-flag indicators
```

Output:

```text
SELF_CARE
CONSULT_DOCTOR
URGENT_EMERGENCY
```

Important:

```text
Prediction ≠ Risk
```

A condition prediction and urgency assessment are separate outputs.

---

## Day 6 — Safety Rules and Red Flags

Build an explicit rule layer.

Example architecture:

```text
Structured State
      ↓
Red Flag Detector
      ↓
Risk Override
      ↓
Prediction Result
```

If a safety-critical condition is detected, the risk layer must be able to override a low-risk prediction.

Do not depend entirely on the ML model to identify urgent situations.

---

## Day 7 — Evaluation

Compare:

```text
Week 1 baseline
vs
Week 2 improved pipeline
```

Track:

- Top-1
- Top-3
- precision
- recall
- invalid output rate
- no-result rate
- risk classification agreement on the test set
- red-flag detection test results

Do not claim clinical accuracy from prototype evaluation.

### Final Nisarg deliverables

- improved feature pipeline
- candidate ranking
- confidence mapping
- risk engine
- red-flag rule layer
- evaluation report
- model/version metadata

---

# 8. Vivek — Frontend Application

## Week 2 Goal

Turn the Week 1 chat into a complete assessment application.

---

## Day 1 — Assessment State Management

Centralize frontend state.

Suggested:

```text
assessmentStore
```

State:

```text
assessmentId
messages
symptoms
clarificationQuestion
confirmationStatus
imageStatus
analysisStatus
result
error
```

Do not duplicate assessment state across many components.

---

## Day 2 — Edit Symptom Flow

Implement real editing.

User should be able to:

```text
Add symptom
Remove symptom
Edit severity
Edit duration
Edit location
Correct extracted symptom
```

Every change must update the backend.

---

## Day 3 — Image Upload UI

Build:

```text
Attach image
 ↓
Preview
 ↓
Validate
 ↓
Upload
 ↓
Processing
 ↓
Quality result
```

States:

```text
IDLE
SELECTED
UPLOADING
PROCESSING
READY
LOW_QUALITY
ERROR
```

---

## Day 4 — Account / Guest Flow

Implement:

```text
Continue as Guest
        OR
Sign In / Create Account
```

The assessment itself should remain the primary flow.

Do not force registration unnecessarily.

---

## Day 5 — Result Screen

Build the complete result page:

```text
Risk level
   ↓
What this might be
   ↓
Confidence labels
   ↓
General guidance
   ↓
When to seek care
   ↓
Doctor/search referral when appropriate
   ↓
Limitations/disclaimer
```

Do not overload the user with technical model information.

---

## Day 6 — History / Previous Assessment UI

For authenticated users, create a minimal history screen.

Display only information actually approved for storage/display.

Example:

```text
Previous Assessment
Date
Main symptoms
Risk level
View summary
```

Do not create a full medical-record system.

---

## Day 7 — Frontend Hardening

Test:

- refresh during assessment
- network disconnect
- API timeout
- duplicate send
- browser back
- mobile keyboard
- long messages
- image failure
- restart

### Final Vivek deliverables

- assessment state management
- editing
- image upload UI
- guest/account flow
- complete result page
- minimal history
- frontend error recovery

---

# 9. Darshil — Assessment UX + Result Design

## Week 2 Goal

Make the product understandable and trustworthy when the user reaches the most sensitive parts: clarification, image upload, result, risk, and referral.

---

## Day 1 — Result Information Hierarchy

Design the result around:

```text
1. Urgency
2. What to do next
3. Possible explanations
4. Confidence
5. General guidance
6. Limitations
```

The user should not need to scan a long paragraph to find the risk level.

---

## Day 2 — Risk-Level UX

Design three states:

```text
SELF CARE
CONSULT DOCTOR
URGENT / EMERGENCY
```

Do not use color alone to communicate urgency.

Use:

- text
- icon
- heading
- supporting explanation

---

## Day 3 — Self-Care Guidance UX

Create a reusable guidance component.

Example structure:

```text
General self-care

• Rest
• Stay hydrated
• Monitor symptoms

Seek medical advice if symptoms worsen or new concerning symptoms appear.
```

The component must not become a prescription UI.

---

## Day 4 — Doctor Referral UX

When the risk requires professional care:

```text
Your next step
      ↓
Consider consulting a relevant healthcare professional.
      ↓
[Find nearby options]
```

The system should open/search an external map/search service.

No:

```text
booking
availability
doctor rating
doctor account
```

---

## Day 5 — Image UX

Design contextual image upload.

It should appear when a visible symptom makes an image potentially useful.

Example:

```text
Your symptom appears to involve a visible skin change.

You can optionally upload a photo to provide additional visual information.
```

Do not imply that every uploaded image will produce a reliable medical conclusion.

---

## Day 6 — Responsive and Accessibility Pass

Review:

- keyboard navigation
- focus states
- readable text
- contrast
- touch targets
- screen width
- long content
- error messages
- loading states
- reduced-motion behavior where applicable

---

## Day 7 — Usability Test

Run a short test with users.

Tasks:

```text
Start assessment
Describe symptom
Answer question
Correct symptom
Upload image
View result
Understand risk
Restart
```

Record:

```text
Task
Observed problem
Severity
Suggested fix
Status
```

### Final Darshil deliverables

- result hierarchy
- risk UX
- self-care UX
- referral UX
- image UX
- accessibility pass
- usability report

---

# 10. Kavya — Backend Business Logic

## Week 2 Goal

Expand the backend from API scaffolding into a reliable assessment service.

---

## Day 1 — Assessment Orchestration

Create a service responsible for:

```text
receive message
 ↓
load assessment
 ↓
validate state
 ↓
call AI
 ↓
validate AI result
 ↓
update symptoms
 ↓
generate next action
 ↓
persist
```

Avoid putting the entire flow inside route handlers.

---

## Day 2 — Authentication / Session Integration

Support:

```text
Guest Session
Authenticated User
```

Assessment ownership must be enforced.

A user must not access another user's assessment by changing an ID.

---

## Day 3 — Symptom Editing

Implement transactional update behavior.

Example:

```text
PATCH /assessment/:id/symptoms
```

Validation:

- symptom exists
- value is valid
- assessment is editable
- user owns assessment
- state permits editing

---

## Day 4 — Prediction + Risk Orchestration

Create:

```text
PredictionService
RiskService
ResultService
```

Flow:

```text
READY
 ↓
Prediction
 ↓
Risk
 ↓
Safety Validation
 ↓
Result
 ↓
Persist
```

Do not let frontend directly decide risk level.

---

## Day 5 — Image Integration

Connect:

```text
upload
 ↓
validation
 ↓
storage
 ↓
preprocessing
 ↓
image analyzer
 ↓
assessment state
```

Handle analyzer failure safely.

---

## Day 6 — Referral Endpoint / External Search

If the application needs backend-generated referral metadata, define a narrow endpoint.

Example:

```http
GET /api/v1/assessment/:id/referral
```

Return only what the product actually needs.

Do not build:

```text
doctor database
doctor profiles
doctor ratings
booking
```

---

## Day 7 — Backend Reliability

Test:

- concurrent requests
- duplicate analysis
- repeated message submission
- invalid state
- unauthorized access
- expired session
- AI timeout
- prediction failure
- database failure
- image failure

### Final Kavya deliverables

- assessment orchestration
- guest/auth session handling
- symptom editing
- prediction/risk orchestration
- image integration
- referral support
- robust error handling

---

# 11. Harsh — Database + Privacy Data Layer

## Week 2 Goal

Refine the Week 1 database to support authenticated users, assessment history, consent, retention, and safe data access.

---

## Day 1 — Schema Review

Review Week 1 schema.

Identify:

```text
unused columns
missing constraints
duplicate data
missing indexes
privacy-sensitive fields
```

Do not add fields simply because they might be useful later.

---

## Day 2 — User + Session Data

Support:

```text
users
sessions / guest sessions
assessments
```

Define relationships clearly.

Guest assessment:

```text
user_id = NULL
session_id = guest-session
```

Authenticated assessment:

```text
user_id = authenticated-user
```

---

## Day 3 — Assessment History

Implement efficient retrieval:

```text
GET /api/v1/assessments
```

Support pagination.

Do not load every historical assessment at once.

Example:

```text
page
limit
cursor
```

Use whichever pagination strategy matches the backend.

---

## Day 4 — Consent Records

Create a structured consent record if required by the implementation.

Potential fields:

```text
id
user_id / session_id
consent_type
policy_version
accepted_at
withdrawn_at
```

Do not store a simple boolean if the project needs to know which version the user accepted.

---

## Day 5 — Data Retention / Deletion

Define:

```text
What is stored?
How long?
When is it deleted?
What happens to guest data?
What happens after account deletion?
```

Implement only the retention policy actually approved by the team.

Do not claim a retention period that the application does not enforce.

---

## Day 6 — Access Control and Privacy Queries

Test:

```text
User A → own assessments
User A → cannot access User B
Guest → only own session
Admin → no unnecessary health-data access
```

Use least-privilege access.

---

## Day 7 — Migration + Backup/Recovery Test

Verify:

```text
fresh database
migration
seed
upgrade migration
rollback where supported
recovery procedure
```

### Final Harsh deliverables

- refined schema
- assessment history
- consent records
- retention implementation
- deletion flow support
- access control
- migrations
- database recovery documentation

---

# 12. Mann — Computer Vision / Image Analysis

## Week 2 Goal

Move from the Week 1 image interface to a working image-analysis prototype, while keeping uncertainty and failure handling explicit.

---

## Day 1 — Dataset and Class Definition

Finalize the image task.

Do not define an unnecessarily large medical classification problem.

Define:

```text
input
classes
labels
expected output
unknown class
quality requirements
```

Document dataset limitations.

---

## Day 2 — Image Quality Model / Heuristics

Build quality checks:

```text
blur
brightness
resolution
orientation
crop
background
```

Possible output:

```json
{
  "quality": "ACCEPTABLE",
  "issues": []
}
```

or:

```json
{
  "quality": "LOW",
  "issues": ["BLURRY", "TOO_DARK"]
}
```

---

## Day 3 — Preprocessing Pipeline

Implement reproducible preprocessing:

```text
Original
 ↓
Decode
 ↓
Orientation
 ↓
Resize
 ↓
Crop / pad
 ↓
Normalize
 ↓
Model input
```

Document exact dimensions and preprocessing settings used by the selected model.

---

## Day 4 — Baseline Image Model

If the selected dataset supports it, create a small baseline.

Possible approaches:

```text
Transfer Learning
OR
Small CNN
OR
Pretrained image encoder + classifier
```

Do not optimize for complexity.

Record:

- training set
- validation set
- test set
- model version
- preprocessing version
- metrics

---

## Day 5 — Unknown / Low-Confidence Handling

The image model must have a safe failure path.

Example:

```text
Prediction confidence insufficient
        ↓
Do not force a condition
        ↓
Return:
"Image could not be reliably interpreted."
```

The image model should not always return a disease class.

---

## Day 6 — Image + Text Fusion Contract

Define how image information reaches the assessment system.

Possible architecture:

```text
Text Analysis
     │
     ├──────────────┐
     │              │
     ▼              ▼
Text Features   Image Observations
     │              │
     └──────┬───────┘
            ▼
      Assessment State
            ↓
      Prediction Layer
```

Do not allow raw image-model output to override safety rules.

---

## Day 7 — Evaluation

Test:

- different image qualities
- supported/unsupported formats
- lighting
- different backgrounds
- different skin tones where represented by the dataset
- unknown images
- non-target images
- blurry images

Record limitations.

### Final Mann deliverables

- image dataset setup
- quality checker
- preprocessing pipeline
- baseline CV model
- unknown/low-confidence handling
- text-image integration contract
- CV evaluation report

---

# 13. Mohit — QA, AI Evaluation, Security Testing

## Week 2 Goal

Move from basic testing to systematic validation of the complete application.

---

## Day 1 — Regression Framework

Run all Week 1 tests automatically.

Create:

```text
regression/
    nlp/
    clarification/
    prediction/
    risk/
    image/
    api/
    frontend/
```

---

## Day 2 — API Security Tests

Test:

```text
unauthorized access
wrong assessment ID
modified assessment ID
invalid token
expired session
malformed payload
oversized payload
invalid file
```

---

## Day 3 — AI Adversarial Tests

Test:

```text
prompt injection
role manipulation
false medical facts
contradictory symptoms
extremely long input
repeated input
malicious instructions
out-of-scope requests
```

Expected:

```text
The system preserves assessment scope and structured output constraints.
```

---

## Day 4 — Risk Engine Testing

Create cases for:

```text
low-risk
moderate-risk
urgent-risk
uncertain
missing information
red-flag indicators
conflicting indicators
```

Verify that risk rules behave deterministically.

---

## Day 5 — Image Testing

Test:

```text
valid image
invalid MIME
renamed file
corrupt image
huge image
tiny image
blurry image
dark image
non-target image
```

---

## Day 6 — Full E2E Matrix

Run:

```text
Guest + text
Guest + text + image
Account + text
Account + text + image
Edit before confirmation
Restart
API failure
AI failure
Image failure
Prediction failure
```

---

## Day 7 — Quality Report

Generate:

```text
test count
passed
failed
blocked
critical bugs
high bugs
medium bugs
low bugs
AI regression results
risk tests
image tests
E2E results
```

### Final Mohit deliverables

- regression suite
- API security tests
- AI adversarial tests
- risk tests
- image tests
- E2E matrix
- QA report
- bug backlog

---

# 14. Dimple — Privacy, Safety, Accessibility, Usability

## Week 2 Goal

Make the sensitive parts of the application understandable and safe.

---

## Day 1 — Privacy Flow Review

Trace:

```text
Input
 ↓
Backend
 ↓
AI service
 ↓
Database
 ↓
Image storage
 ↓
Result
```

For each step document:

```text
What data exists?
Why is it needed?
Is it stored?
Who can access it?
How long is it retained?
```

---

## Day 2 — Consent Improvements

Review consent UX.

Ensure:

- clear language
- no hidden consent
- optional data is clearly optional
- storage implications are visible
- policy/version is identifiable

---

## Day 3 — Safety Result Review

Review every result state:

```text
SELF_CARE
CONSULT_DOCTOR
URGENT_EMERGENCY
UNCERTAIN
```

Ensure wording does not overstate certainty.

---

## Day 4 — Image Privacy UX

Clearly explain:

- image is optional
- why it may be useful
- what happens after upload
- whether it is stored
- how the user can cancel

Avoid implying:

```text
"Upload a photo and we will diagnose you."
```

---

## Day 5 — Accessibility

Perform an accessibility review:

```text
keyboard navigation
focus order
labels
alt text
error announcements
contrast
font size
touch targets
screen reader behavior
```

---

## Day 6 — Usability Testing

Run structured tasks:

```text
Start
Describe
Clarify
Edit
Upload
Confirm
View result
Find referral
Restart
```

Record:

```text
Task
Time
Confusion
Error
User comment
Suggested change
```

---

## Day 7 — Safety/Privacy Sign-Off

Create a Week 2 review document:

```text
Privacy issues
Safety issues
UX issues
Accessibility issues
Open risks
Required fixes
```

### Final Dimple deliverables

- privacy data-flow review
- consent improvements
- safety copy review
- image privacy UX
- accessibility report
- usability report
- safety/privacy sign-off checklist

---

# 15. Rutva — Backend Lead + Integration / Reliability

## Week 2 Goal

Turn the Week 1 integrated prototype into a stable staging-ready system.

---

## Day 1 — Integration Review

Review every service:

```text
Frontend
Backend
AI
Prediction
Risk
Database
Image
Authentication
Testing
```

Identify duplicate responsibilities.

---

## Day 2 — Service Contracts

Freeze Week 2 contracts.

Define:

```text
request
response
errors
timeouts
versions
```

Document service dependencies.

---

## Day 3 — Error and Retry Strategy

Define:

```text
AI timeout
AI invalid output
DB timeout
image processing failure
prediction failure
external map failure
```

For each:

```text
retry?
fallback?
user message?
log?
```

Do not retry unsafe or non-idempotent operations blindly.

---

## Day 4 — Observability

Add structured logs.

Example:

```json
{
  "event": "assessment_analysis_completed",
  "assessment_id": "...",
  "model_version": "...",
  "duration_ms": 1240,
  "status": "SUCCESS"
}
```

Do not log unnecessary health information.

Use identifiers that do not expose sensitive content in normal logs.

---

## Day 5 — Performance

Measure:

```text
frontend response
API latency
AI latency
prediction latency
image processing latency
database query latency
```

Find bottlenecks.

Do not optimize prematurely.

---

## Day 6 — Staging Environment

Create:

```text
development
staging
production
```

or the environments supported by the team's deployment setup.

Ensure:

- environment variables
- secrets
- database config
- storage config
- AI keys
- CORS
- error handling

are environment-specific.

---

## Day 7 — Full Integration and Release Candidate

Run:

```text
build
migration
tests
AI regression
E2E
security checks
image tests
privacy checks
```

Create:

```text
week-2-release-candidate
```

### Final Rutva deliverables

- integrated services
- error/retry strategy
- structured logging
- performance report
- staging environment
- release candidate
- deployment documentation

---

# 15.1 Risk Engine Implementation

The risk engine is deliberately separate from the prediction engine. It receives the structured state, predicted conditions, and safety indicators, then produces an independent risk classification.

### Risk engine architecture

```typescript
// server/src/services/prediction/riskEngine.ts
import { logger } from '../../config/logger';

interface RiskInput {
  assessmentId: string;
  symptoms: Array<{
    name: string;
    severity: string;
    duration: { value: number; unit: string } | null;
  }>;
  predictedConditions: Array<{ name: string; score: number }>;
  age: number | null;
  predictionUncertainty: number;  // 0.0 to 1.0
}

interface RiskOutput {
  riskLevel: 'SELF_CARE' | 'CONSULT_DOCTOR' | 'URGENT_EMERGENCY';
  overridden: boolean;
  overrideReason: string | null;
  redFlagsDetected: string[];
}

// RED FLAG PATTERNS — deterministic, not ML-dependent
const RED_FLAGS: Array<{ pattern: (input: RiskInput) => boolean; flag: string }> = [
  {
    pattern: (i) => i.symptoms.some(s => s.name === 'CHEST_PAIN' && s.severity === 'SEVERE'),
    flag: 'SEVERE_CHEST_PAIN',
  },
  {
    pattern: (i) => i.symptoms.some(s => s.name === 'SHORTNESS_OF_BREATH' && s.severity === 'SEVERE'),
    flag: 'SEVERE_BREATHING_DIFFICULTY',
  },
  {
    pattern: (i) => i.symptoms.some(s =>
      s.name === 'HEADACHE' && s.severity === 'SEVERE' &&
      i.symptoms.some(s2 => ['CONFUSION', 'VISION_CHANGES', 'NECK_STIFFNESS'].includes(s2.name)),
    ),
    flag: 'SEVERE_HEADACHE_WITH_NEUROLOGICAL',
  },
  {
    pattern: (i) => i.symptoms.some(s =>
      s.name === 'FEVER' && s.severity === 'SEVERE' &&
      s.duration && s.duration.value >= 3 && s.duration.unit === 'DAY',
    ),
    flag: 'PROLONGED_HIGH_FEVER',
  },
  {
    pattern: (i) => i.symptoms.some(s => s.name === 'LOSS_OF_CONSCIOUSNESS'),
    flag: 'LOSS_OF_CONSCIOUSNESS',
  },
  {
    pattern: (i) => i.symptoms.some(s =>
      s.name === 'BLEEDING' && s.severity === 'SEVERE',
    ),
    flag: 'SEVERE_BLEEDING',
  },
];

export function calculateRisk(input: RiskInput): RiskOutput {
  // Step 1: Detect red flags
  const detectedFlags = RED_FLAGS
    .filter(rf => rf.pattern(input))
    .map(rf => rf.flag);

  // Step 2: If any red flag detected, override to URGENT regardless of prediction
  if (detectedFlags.length > 0) {
    logger.warn({
      assessmentId: input.assessmentId,
      event: 'red_flag_detected',
      flags: detectedFlags,
    });
    return {
      riskLevel: 'URGENT_EMERGENCY',
      overridden: true,
      overrideReason: `Red flag(s) detected: ${detectedFlags.join(', ')}`,
      redFlagsDetected: detectedFlags,
    };
  }

  // Step 3: Score-based risk assessment
  let riskScore = 0;

  // Severity contribution
  for (const symptom of input.symptoms) {
    if (symptom.severity === 'SEVERE') riskScore += 3;
    else if (symptom.severity === 'MODERATE') riskScore += 2;
    else if (symptom.severity === 'MILD') riskScore += 1;
  }

  // Multiple symptoms increase risk
  if (input.symptoms.length >= 4) riskScore += 2;

  // Age-based adjustment
  if (input.age && (input.age < 5 || input.age > 65)) riskScore += 2;

  // Uncertainty escalation — per project spec, uncertainty moves risk UPWARD
  if (input.predictionUncertainty > 0.6) riskScore += 2;

  // Step 4: Map score to risk level
  let riskLevel: RiskOutput['riskLevel'];
  if (riskScore >= 8) riskLevel = 'URGENT_EMERGENCY';
  else if (riskScore >= 4) riskLevel = 'CONSULT_DOCTOR';
  else riskLevel = 'SELF_CARE';

  logger.info({
    assessmentId: input.assessmentId,
    event: 'risk_calculated',
    riskScore,
    riskLevel,
    symptomCount: input.symptoms.length,
    uncertainty: input.predictionUncertainty,
  });

  return {
    riskLevel,
    overridden: false,
    overrideReason: null,
    redFlagsDetected: [],
  };
}
```

### Confidence label mapping

```typescript
// server/src/services/prediction/confidenceMapper.ts

/**
 * Maps raw model scores to qualitative labels.
 * CRITICAL: These are NOT clinical probabilities.
 * They represent relative ranking within model output.
 */
export function mapConfidence(score: number): 'LIKELY' | 'POSSIBLE' | 'LESS_LIKELY' {
  if (score >= 0.6) return 'LIKELY';
  if (score >= 0.3) return 'POSSIBLE';
  return 'LESS_LIKELY';
}

/**
 * Calculate overall prediction uncertainty.
 * High uncertainty = top candidate score is low, or gap between candidates is small.
 */
export function calculateUncertainty(scores: number[]): number {
  if (scores.length === 0) return 1.0;
  const sorted = [...scores].sort((a, b) => b - a);
  const topScore = sorted[0];
  const gap = sorted.length > 1 ? sorted[0] - sorted[1] : sorted[0];

  // Low top score OR small gap between top candidates = high uncertainty
  const scoreUncertainty = 1 - topScore;
  const gapUncertainty = 1 - gap;

  return Math.min(1.0, (scoreUncertainty + gapUncertainty) / 2);
}
```

### Result composer

```typescript
// server/src/services/prediction/resultComposer.ts
import { mapConfidence, calculateUncertainty } from './confidenceMapper';
import { calculateRisk } from './riskEngine';

export async function composeResult(
  assessmentId: string,
  symptoms: StructuredSymptom[],
  predictions: Array<{ condition: string; score: number }>,
  context: { age: number | null; sex: string | null },
): Promise<AssessmentResult> {
  const uncertainty = calculateUncertainty(predictions.map(p => p.score));

  // Generate risk independently from prediction
  const riskResult = calculateRisk({
    assessmentId,
    symptoms,
    predictedConditions: predictions.map(p => ({ name: p.condition, score: p.score })),
    age: context.age,
    predictionUncertainty: uncertainty,
  });

  // Map top 3 candidates to qualitative labels
  const topCandidates = predictions
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map((p, index) => ({
      name: p.condition,
      confidence: mapConfidence(p.score),
      rank: index + 1,
    }));

  // Generate guidance based on risk level
  const guidance = generateGuidance(riskResult.riskLevel);

  // Determine referral need
  const referral = {
    required: riskResult.riskLevel !== 'SELF_CARE',
    specialty: riskResult.riskLevel !== 'SELF_CARE'
      ? inferSpecialty(topCandidates[0]?.name)
      : null,
  };

  return {
    assessmentId,
    riskLevel: riskResult.riskLevel,
    conditions: topCandidates,
    guidance,
    referral,
    limitations: [
      'This result is informational and does not confirm a diagnosis.',
      'Consult a healthcare professional for medical advice.',
      riskResult.overridden
        ? 'Risk level was elevated due to safety-critical symptom patterns.'
        : null,
    ].filter(Boolean) as string[],
    modelVersion: process.env.MODEL_VERSION || 'v1.0.0-prototype',
    createdAt: new Date().toISOString(),
  };
}

function generateGuidance(risk: string): string[] {
  switch (risk) {
    case 'SELF_CARE':
      return [
        'Rest and stay hydrated.',
        'Monitor your symptoms over the next 24–48 hours.',
        'Seek medical attention if symptoms worsen or new concerning symptoms appear.',
      ];
    case 'CONSULT_DOCTOR':
      return [
        'Consider scheduling an appointment with a healthcare professional.',
        'Monitor your symptoms and note any changes.',
        'If symptoms significantly worsen before your appointment, seek urgent care.',
      ];
    case 'URGENT_EMERGENCY':
      return [
        'Seek immediate medical attention.',
        'Call emergency services or visit the nearest emergency room.',
        'Do not delay seeking care.',
      ];
    default:
      return ['Please consult a healthcare professional for guidance.'];
  }
}

function inferSpecialty(conditionName?: string): string {
  // Basic specialty mapping — to be expanded with medical reference data
  const specialtyMap: Record<string, string> = {
    'Common Cold': 'General Practitioner',
    'Influenza': 'General Practitioner',
    'Migraine': 'Neurologist',
    'Sinusitis': 'ENT Specialist',
    'Dermatitis': 'Dermatologist',
    'Pneumonia': 'Pulmonologist',
  };
  return conditionName ? (specialtyMap[conditionName] || 'General Practitioner') : 'General Practitioner';
}
```

---

# 16. Week 2 Daily Dependency Plan

## Day 1 — Analyze and Stabilize

```text
All members
    ↓
Review Week 1
    ↓
Identify failures
    ↓
Prioritize Week 2
```

Primary output:

```text
Week 1 bug backlog
+
Week 2 implementation plan
```

---

## Day 2 — Core Intelligence Upgrade

```text
Nishith → multi-turn/context extraction
Nisarg  → feature improvement
Mann    → image quality
Kavya   → orchestration
Harsh   → schema refinement
```

---

## Day 3 — User Interaction Upgrade

```text
Vivek   → edit + image UI
Darshil → result/risk UX
Dimple  → consent/accessibility
Kavya   → auth/session
```

---

## Day 4 — Prediction + Risk

```text
Structured State
      ↓
Prediction
      ↓
Risk
      ↓
Safety Rules
      ↓
Result
```

This is the most important technical integration point of Week 2.

---

## Day 5 — Image + Account + History

```text
Image
 +
Guest/Auth
 +
History
```

must work without breaking the assessment flow.

---

## Day 6 — Testing + Hardening

Run:

```text
AI regression
API tests
security tests
image tests
risk tests
E2E
accessibility
```

Fix critical issues.

---

## Day 7 — Release Candidate

Complete:

```text
Integration
 ↓
Testing
 ↓
Bug Fixes
 ↓
Documentation
 ↓
Staging
 ↓
Week 2 Release Candidate
```

---

# 17. Week 2 Data Flow

## Text Path

```text
User Text
   ↓
Message API
   ↓
Conversation Context
   ↓
Symptom Extraction
   ↓
Normalization
   ↓
Contradiction Detection
   ↓
Structured State
```

---

## Clarification Path

```text
Structured State
   ↓
Missing Information
   ↓
Priority
   ↓
Question
   ↓
User Answer
   ↓
Structured State Update
```

---

## Image Path

```text
Image
 ↓
Upload
 ↓
Validation
 ↓
Quality Check
 ↓
Preprocessing
 ↓
Image Analyzer
 ↓
Image Observation
 ↓
Structured Assessment
```

---

## Prediction Path

```text
Structured State
       ↓
Feature Vector
       ↓
Candidate Generation
       ↓
Candidate Ranking
       ↓
Confidence Label
       ↓
Risk Engine
       ↓
Safety Override
       ↓
Result
```

---

# 18. Risk Engine Design

The risk engine should be independent from the condition prediction engine.

```text
              STRUCTURED STATE
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
  CONDITION PREDICTION      RISK ENGINE
          │                     │
          ▼                     ▼
 Possible Conditions        Risk Level
          │                     │
          └──────────┬──────────┘
                     ▼
              RESULT COMPOSER
```

Possible states:

```text
SELF_CARE
CONSULT_DOCTOR
URGENT_EMERGENCY
UNCERTAIN
```

The UI can map these to the project's three user-facing categories.

---

# 19. Result Composer

The backend should produce structured result data.

Example:

```json
{
  "risk_level": "CONSULT_DOCTOR",
  "conditions": [
    {
      "name": "Condition A",
      "confidence": "Likely",
      "rank": 1
    },
    {
      "name": "Condition B",
      "confidence": "Possible",
      "rank": 2
    }
  ],
  "guidance": [
    "General informational guidance"
  ],
  "referral": {
    "required": true,
    "specialty": "Relevant specialist"
  },
  "disclaimer": "This result is informational and does not confirm a diagnosis."
}
```

The frontend should render structured fields rather than parsing a large AI-generated paragraph.

---

# 20. Account vs Guest Behavior

## Guest

```text
Start
 ↓
Assessment
 ↓
Result
 ↓
Restart
```

Only data required for the active session should be retained according to the approved retention policy.

---

## Account

```text
Sign In
 ↓
Assessment
 ↓
Consent-based storage
 ↓
History
 ↓
Future assessment
```

Account creation must not automatically imply unlimited medical-data retention.

---

# 21. Image Analysis Rules

The image system must support:

```text
ACCEPTED
LOW_QUALITY
UNSUPPORTED
CORRUPTED
NOT_ANALYZABLE
ANALYZED
```

Never assume:

```text
Uploaded image = useful medical evidence
```

The system must be able to continue safely without image analysis.

---

# 22. Week 2 API Expansion

Recommended endpoints:

```http
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout

GET    /api/v1/assessments
GET    /api/v1/assessment/:id

PATCH  /api/v1/assessment/:id/symptoms
POST   /api/v1/assessment/:id/message

POST   /api/v1/assessment/:id/image
GET    /api/v1/assessment/:id/image/:imageId

POST   /api/v1/assessment/:id/analyze
GET    /api/v1/assessment/:id/result

GET    /api/v1/assessment/:id/referral
```

Exact authentication implementation can vary according to the selected stack.

---

# 23. Week 2 Testing Matrix

| Area | Week 2 Tests |
|---|---|
| Multi-turn AI | Context preserved across messages |
| Extraction | Corrections update state |
| Contradiction | Conflicts detected |
| Clarification | Questions prioritized |
| Prediction | Top candidates stable |
| Risk | Red-flag rules override appropriately |
| Result | Structured result renders correctly |
| Image | Quality/failure paths work |
| Authentication | Ownership enforced |
| Guest | Guest cannot access another session |
| History | Pagination works |
| Privacy | Consent records correct |
| Security | Unauthorized access rejected |
| Performance | Latency measured |
| E2E | Guest + account flows pass |
| Accessibility | Keyboard/screen-reader basics pass |

---

# 23.1 Week 2 Performance Budgets

Define measurable performance targets based on Week 1 baseline. These are engineering targets, not SLAs.

| Operation | Target p50 | Target p95 | Hard Timeout |
|---|---|---|---|
| API response (non-AI) | < 100ms | < 300ms | 5s |
| AI extraction call | < 2s | < 5s | 30s |
| AI clarification call | < 1.5s | < 4s | 30s |
| Prediction engine | < 500ms | < 1.5s | 10s |
| Risk calculation | < 50ms | < 100ms | 1s |
| Image upload + validation | < 1s | < 3s | 30s |
| Image preprocessing | < 2s | < 5s | 30s |
| Database query (single) | < 20ms | < 100ms | 5s |
| History page load | < 200ms | < 500ms | 5s |
| Frontend initial load | < 1.5s | < 3s | N/A |
| Total assessment e2e | < 30s | < 60s | N/A |

### Response time measurement middleware

```typescript
// server/src/middleware/responseTime.ts
import { RequestHandler } from 'express';
import { logger } from '../config/logger';

export function responseTimeLogger(): RequestHandler {
  return (req, res, next) => {
    const start = process.hrtime.bigint();
    res.on('finish', () => {
      const durationMs = Number(process.hrtime.bigint() - start) / 1_000_000;
      logger.info({
        event: 'http_request',
        method: req.method,
        path: req.path,
        status: res.statusCode,
        durationMs: Math.round(durationMs),
        correlationId: req.headers['x-correlation-id'],
      });
    });
    next();
  };
}
```

# 23.2 Advanced Testing Patterns

### AI extraction test harness

Create a reusable test runner that evaluates AI extraction accuracy across the full test suite.

```typescript
// tests/ai/evaluateExtraction.ts
import testCases from '../fixtures/extraction_cases.json';
import { extractSymptoms } from '../../server/src/services/ai/extractionService';
import { validateExtractionResponse } from '../../server/src/services/ai/aiResponseValidator';

interface TestCase {
  id: string;
  input: string;
  expected: { symptoms: Array<{ name: string; severity?: string }> };
}

async function evaluateExtraction() {
  const results = { total: 0, passed: 0, failed: 0, errors: 0, failures: [] as any[] };

  for (const tc of testCases as TestCase[]) {
    results.total++;
    try {
      const raw = await extractSymptoms(tc.input, '');
      const parsed = validateExtractionResponse(raw, `test_${tc.id}`);
      if (!parsed) { results.errors++; continue; }

      const allFound = tc.expected.symptoms.every(exp =>
        parsed.symptoms.some(act => act.name === exp.name),
      );
      if (allFound) results.passed++;
      else {
        results.failed++;
        results.failures.push({ id: tc.id, input: tc.input, expected: tc.expected, actual: parsed });
      }
    } catch { results.errors++; }
  }

  console.log(`\nExtraction Evaluation: ${results.passed}/${results.total} passed`);
  console.log(`  Failed: ${results.failed}, Errors: ${results.errors}`);
}
```

### API integration test example

```typescript
// tests/integration/assessment.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import { app } from '../../server/src/index';
import { prisma } from '../../server/src/config/database';

describe('Assessment API', () => {
  beforeEach(async () => { await prisma.assessment.deleteMany(); });

  it('creates a new assessment', async () => {
    const res = await request(app).post('/api/v1/assessment').send({ sessionId: 'test-123' });
    expect(res.status).toBe(201);
    expect(res.body.data.state).toBe('START');
  });

  it('rejects invalid state transitions', async () => {
    const { body: { data } } = await request(app).post('/api/v1/assessment').send({});
    const res = await request(app).patch(`/api/v1/assessment/${data.id}/state`).send({ state: 'COMPLETED' });
    expect(res.status).toBe(409);
  });

  it('enforces assessment ownership', async () => {
    const { body: { data } } = await request(app)
      .post('/api/v1/assessment').set('Cookie', 'sessionId=user-a').send({});
    const res = await request(app)
      .get(`/api/v1/assessment/${data.id}`).set('Cookie', 'sessionId=user-b');
    expect(res.status).toBe(403);
  });
});
```

---

# 24. Week 2 Security Checklist

- [ ] Authentication works
- [ ] Authorization is enforced
- [ ] Assessment ownership is checked
- [ ] Guest session ownership is checked
- [ ] File MIME validation exists
- [ ] File signature validation exists
- [ ] File size limits exist
- [ ] Request size limits exist
- [ ] Input validation exists
- [ ] AI output is schema validated
- [ ] AI output is safety validated
- [ ] Sensitive health text is not unnecessarily logged
- [ ] API keys are not exposed to frontend
- [ ] Secrets are environment variables
- [ ] Error responses do not expose stack traces
- [ ] CORS is configured appropriately
- [ ] External referral links are safely generated

---

# 25. Week 2 Privacy Checklist

- [ ] Guest data flow documented
- [ ] Account data flow documented
- [ ] Consent flow tested
- [ ] Consent version stored where required
- [ ] Image storage documented
- [ ] AI data flow documented
- [ ] Retention behavior documented
- [ ] Deletion behavior documented
- [ ] Assessment history access restricted
- [ ] Sensitive logs reviewed
- [ ] Privacy promises match actual implementation

---

# 26. Week 2 AI Evaluation Dataset

Create a reusable dataset:

```text
evaluation/
├── simple.json
├── multi_symptom.json
├── multi_turn.json
├── ambiguous.json
├── contradictory.json
├── correction.json
├── clarification.json
├── prediction.json
├── risk.json
├── image.json
├── safety.json
└── out_of_scope.json
```

Each case should contain:

```json
{
  "id": "case_001",
  "conversation": [],
  "expected_behavior": {},
  "actual_behavior": {},
  "status": "PASS"
}
```

---

# 27. Week 2 Documentation

Update:

```text
docs/
├── architecture/
│   ├── system-architecture.md
│   ├── assessment-state-machine.md
│   └── week2-integration.md
│
├── api/
│   ├── api-contract.md
│   └── authentication.md
│
├── ai/
│   ├── extraction-v2.md
│   ├── clarification-v2.md
│   ├── prediction-v2.md
│   └── risk-engine.md
│
├── image/
│   ├── image-pipeline.md
│   └── image-model.md
│
├── database/
│   ├── schema.md
│   ├── retention.md
│   └── access-control.md
│
├── privacy/
│   ├── data-flow.md
│   └── consent.md
│
├── testing/
│   ├── regression.md
│   ├── ai-evaluation.md
│   └── week2-report.md
│
└── deployment/
    └── staging.md
```

---

# 32. Week 2 Final Demo

Use at least three scenarios.

## Scenario A — Simple Text Assessment

```text
Guest
 ↓
Symptoms
 ↓
Clarification
 ↓
Confirmation
 ↓
Prediction
 ↓
Risk
 ↓
Result
 ↓
Restart
```

---

## Scenario B — Visible Symptom

```text
Guest
 ↓
Describe visible symptom
 ↓
Optional image upload
 ↓
Image validation
 ↓
Image analysis / quality result
 ↓
Combined assessment
 ↓
Result
```

---

## Scenario C — Authenticated User

```text
Sign in
 ↓
Consent
 ↓
Assessment
 ↓
Result
 ↓
Saved history
 ↓
Open history
 ↓
Start new assessment
```

---

# 34. Week 2 Performance Targets

These are engineering targets, not medical performance claims.

Track:

```text
API response time
AI response time
prediction response time
image processing time
database query time
frontend rendering time
```

Set actual target numbers after observing the Week 1 baseline.

Do not invent arbitrary performance claims without measurement.

---

# 35. Week 2 Code Quality Requirements

Every new module should have:

```text
clear responsibility
typed input/output
error handling
unit test
documentation
logging where appropriate
```

Avoid:

```text
giant route handlers
duplicate AI prompts
hard-coded medical logic scattered across frontend
database calls inside UI components
business logic hidden inside controllers
magic strings everywhere
```

---

# 36. Week 2 Architecture Decision Records

Create ADRs for important decisions.

Suggested:

```text
ADR-001 — Why AI output is schema validated
ADR-002 — Why prediction and risk are separate
ADR-003 — Why qualitative confidence is shown
ADR-004 — Why image analysis can return no prediction
ADR-005 — Guest vs authenticated assessment model
ADR-006 — Assessment data retention strategy
ADR-007 — Risk override / red-flag architecture
```

Each ADR:

```text
Context
Decision
Alternatives
Reason
Consequences
```

---

# 37. Week 2 Final Checklist

## AI

- [ ] Multi-turn context works
- [ ] Corrections work
- [ ] Contradictions are handled
- [ ] Clarification is prioritized
- [ ] Prompt versions exist
- [ ] Schema validation exists
- [ ] Out-of-scope handling works
- [ ] Regression dataset exists

## Prediction

- [ ] Feature pipeline improved
- [ ] Candidate ranking works
- [ ] Top 2–3 output works
- [ ] Confidence labels work
- [ ] Risk engine works
- [ ] Red-flag override exists
- [ ] Evaluation report exists

## Frontend

- [ ] Central assessment state
- [ ] Symptom editing
- [ ] Image upload
- [ ] Guest flow
- [ ] Account flow
- [ ] Result screen
- [ ] History
- [ ] Error recovery
- [ ] Responsive layout

## Backend

- [ ] Assessment orchestration
- [ ] Authentication/session support
- [ ] Authorization
- [ ] Prediction orchestration
- [ ] Risk orchestration
- [ ] Image integration
- [ ] Referral support
- [ ] Retry/error handling

## Database

- [ ] Schema refined
- [ ] History
- [ ] Consent
- [ ] Retention
- [ ] Deletion support
- [ ] Access control
- [ ] Migrations
- [ ] Performance queries

## Image

- [ ] Dataset selected
- [ ] Quality checks
- [ ] Preprocessing
- [ ] Baseline model
- [ ] Unknown handling
- [ ] Evaluation
- [ ] Text-image contract

## QA

- [ ] Regression suite
- [ ] Security tests
- [ ] AI adversarial tests
- [ ] Risk tests
- [ ] Image tests
- [ ] E2E matrix
- [ ] Bug report

## Privacy / UX

- [ ] Consent reviewed
- [ ] Data flow reviewed
- [ ] Image privacy reviewed
- [ ] Safety copy reviewed
- [ ] Accessibility reviewed
- [ ] Usability test completed

## Integration

- [ ] Development works
- [ ] Staging works
- [ ] Environment variables documented
- [ ] Logging works
- [ ] Errors are safe
- [ ] Full E2E works

---

# 39. Week 2 Release Candidate

Create:

```text
week-2-release-candidate
```

Release candidate must contain:

```text
Chat
+
Multi-turn AI
+
Clarification
+
Confirmation/Edit
+
Prediction
+
Risk
+
Image
+
Guest
+
Account
+
Consent
+
History
+
Testing
+
Staging
```

---

# 40. Week 2 Exit Criteria

Week 2 is complete only when:

1. Week 1 functionality still works.
2. Multi-turn symptom context is supported.
3. User corrections update structured state.
4. Contradictory information is handled.
5. Clarification questions are prioritized.
6. Prediction produces structured top candidates.
7. Confidence labels are qualitative.
8. Risk is calculated separately from prediction.
9. Safety rules can override unsafe low-risk outcomes.
10. Image upload has quality/failure handling.
11. A baseline image analysis pipeline exists if the selected dataset supports it.
12. Guest and authenticated flows work.
13. Assessment ownership is enforced.
14. Consent/data handling is implemented according to the approved design.
15. Assessment history works for authenticated users.
16. Critical AI/API/image/security tests pass.
17. Full E2E scenarios pass.
18. Staging environment is usable.
19. No Week 1 critical regressions remain.
20. The system is ready for Week 3 final polish, evaluation, deployment, and presentation.

---

# 41. Week 2 Final System

The expected Week 2 system should look like:

```text
                         USER
                           │
             ┌─────────────┴─────────────┐
             │                           │
           GUEST                       ACCOUNT
             │                           │
             └─────────────┬─────────────┘
                           ▼
                     ASSESSMENT
                           │
                           ▼
                      CHAT INPUT
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
          TEXT PATH                 IMAGE PATH
              │                         │
              ▼                         ▼
        Symptom NLP              Image Pipeline
              │                         │
              └────────────┬────────────┘
                           ▼
                    STRUCTURED STATE
                           │
                           ▼
                    USER CONFIRMATION
                           │
                           ▼
                    PREDICTION ENGINE
                           │
                           ▼
                       RISK ENGINE
                           │
                           ▼
                    SAFETY VALIDATION
                           │
                           ▼
                     RESULT COMPOSER
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
        Self-Care      Consult Doctor   Urgent
            │              │              │
            ▼              ▼              ▼
        Guidance       External Search   Urgent Guidance
                           │
                           ▼
                      SAVE IF CONSENTED
                           │
                           ▼
                         HISTORY
```

---

# 42. Week 2 Handoff to Week 3

At the end of Week 2, prepare the following for Week 3:

```text
AI
→ final candidate pipeline + evaluation results

Prediction
→ model/rule version + metrics

Risk
→ finalized rule set + test cases

Frontend
→ complete UI + known UX issues

Backend
→ stable API + staging deployment

Database
→ migration + retention/deletion behavior

Image
→ baseline model + limitations

QA
→ full test report + remaining bugs

Privacy
→ consent + data-flow review

Integration
→ staging release candidate
```

Week 3 can then focus on:

```text
Final Evaluation
+
Bug Fixing
+
Performance
+
Security
+
UI Polish
+
Deployment
+
Documentation
+
Final Presentation
```

---

# 43. Week 2 Success Definition

The project should **not** be judged by the number of AI features added.

The key Week 2 question is:

> **Can the system take a real user's multi-turn symptom description, safely structure it, optionally use an image, produce a tested candidate/risk result, recover from failures, protect assessment ownership, and present the result clearly without pretending to diagnose the user?**

If yes, the project is ready for the final Week 3 phase.

---

# Week 2 Milestone

```text
WEEK 2
   ↓
AI + PREDICTION + RISK
   ↓
IMAGE
   ↓
ACCOUNT + PRIVACY
   ↓
RESULT UX
   ↓
SECURITY + TESTING
   ↓
STAGING
   ↓
week-2-release-candidate
```

**End of Week 2.**
