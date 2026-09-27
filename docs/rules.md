# Team Rules, Ownership Boundaries & Anti-Clash Guidelines

These rules exist to prevent merge conflicts, duplicated work, broken interfaces, and wasted days. Every team member must read and follow this document before writing their first line of code for the AI-Based Symptom Checker.

---

## The Golden Rules (Apply to Everyone)

1. **You own your module. You do not touch anyone else's module without their knowledge.**
2. **Interfaces are sacred.** Once an API contract or Type definition is published to `main`, you cannot change it unilaterally — open a discussion first.
3. **Nothing goes to `main` without a PR.** Direct pushes to `main` are blocked. No exceptions.
4. **Broken `main` = team emergency.** If you break `main`, you fix it before anything else.
5. **If you depend on someone else's work, use mocks until the real implementation is merged.** Never block your own progress waiting on someone else.
6. **Every PR must have a description.** "Added stuff" is not a description. Explain what you changed and why. Mention what tests you ran.
7. **Talk before you refactor.** If you think someone else's code needs restructuring, open a discussion — don't silently reorganize it.
8. **Never put secrets in code.** API keys, passwords, database URLs, and JWT secrets — all go in `.env` files, never committed.

---

## Directory Ownership Map

This is who owns which part of the codebase. **You do not create files in someone else's directory without their approval.**

```text
project-root/
├── client/                   ← Frontend
│   ├── src/
│   │   ├── components/       ← Vivek (chat) / Darshil (layout, forms, results)
│   │   ├── pages/            ← Darshil
│   │   ├── services/         ← Vivek / Darshil (API client hooks)
│   │   ├── store/            ← Vivek (chat state)
│   │   └── types/            ← Shared (mirrors backend contracts)
├── server/                   ← Backend
│   ├── src/
│   │   ├── routes/           ← Rutva (API endpoints)
│   │   ├── middleware/       ← Rutva / Dimple (auth, security, rate-limits)
│   │   ├── services/
│   │   │   ├── assessment/   ← Kavya (orchestration, state machine)
│   │   │   ├── ai/           ← Nishith (extraction, clarification prompts)
│   │   │   ├── prediction/   ← Nisarg (risk engine, conditions mapping)
│   │   │   └── image/        ← Mann (upload processing, CV validation)
│   │   ├── utils/            ← Shared
│   │   └── config/           ← Rutva
│   ├── prisma/               ← Harsh (schema.prisma, migrations ONLY)
├── tests/                    ← Mohit (all e2e, integration, and AI eval files)
└── docs/                     ← Everyone reads, Rutva maintains
```

---

## Per-Member Ownership & Hard Boundaries

---

### 👤 Rutva — Backend Lead + Integration
**You own:** Express server foundation, API routing logic, CI/CD pipelines (GitHub Actions), Docker/Nginx configuration, logging infrastructure (Pino), and overall backend deployment architecture.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Write API routes in `server/src/routes/` that call Kavya/Nishith's services | Write the core assessment state machine logic (that's Kavya) |
| Define the final REST API contract and OpenAPI spec | Write AI extraction logic (that's Nishith) |
| Setup Pino logger, correlation IDs, and application metrics | Change Prisma schema (that's Harsh) |
| Configure production Nginx, Health Checks, and Dockerfiles | Build the frontend application |

**Interface you publish (others depend on this):**
- All REST API endpoints (e.g., `POST /api/v1/assessment`, `POST /api/v1/assessment/:id/message`) with exact URL, method, request body, and response schema.
- Publish this OpenAPI spec on Day 1. Vivek and Darshil mock against it immediately.

---

### 👤 Harsh — Database Lead
**You own:** PostgreSQL schema, all Prisma migrations, connection pooling, indexing, and the core database access layer.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Create and run `npx prisma migrate` | Let anyone else create a migration file |
| Define all Prisma models (`User`, `Assessment`, `Message`, `Symptom`) | Allow anyone to bypass Prisma with raw SQL (unless approved for performance) |
| Enforce data normalization and JSONB usage constraints | Change the API contract (that's Rutva) |
| Add and tune database indexes for performance | Write application-layer logic inside the DB layer |

**Critical rules:**
- **Only Harsh creates migration files.** If someone else needs a schema change, they request it via a GitHub Issue — Harsh creates the migration.
- **Never drop a column in production without a two-step migration** (add new, migrate data, drop old).

---

### 👤 Kavya — Assessment Orchestration Lead
**You own:** The core Assessment State Machine (`START → SYMPTOM_COLLECTION → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`), session coordination, and the central orchestration service (`assessmentOrchestrator.ts`).

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Enforce strict state transitions (e.g., block analysis if state != READY) | Write the actual LLM prompt (that's Nishith) |
| Call AI extraction and save output to the database | Write Express route handlers directly (that's Rutva) |
| Manage the 3-turn clarification loop limit | Write frontend chat UI (that's Vivek) |
| Guard assessment ownership (block cross-user access) | Write database migrations (that's Harsh) |

**Interface you publish (others depend on this):**
```typescript
class AssessmentOrchestrator {
  async processMessage(assessmentId: string, message: string): Promise<ProcessResult>;
  async confirmSymptoms(assessmentId: string, symptoms: Symptom[]): Promise<void>;
  async generateResult(assessmentId: string): Promise<AssessmentResult>;
}
```
Rutva's routes call these methods.

---

### 👤 Nishith — AI / ML Lead
**You own:** LLM integration (OpenAI API Gateway), prompt engineering for symptom extraction and clarification, JSON schema enforcement, multi-turn context parsing, and prompt injection defense.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Write and version extraction & clarification prompts (`ai/prompts/`) | Call LLMs directly from API routes — route through your AI gateway |
| Parse, validate, and repair AI JSON outputs (Zod) | Write the risk calculation logic (that's Nisarg) |
| Handle AI API timeouts, retries, and fallback errors | Write the frontend Chat component |
| Sanitize input against prompt injections (ignore instructions) | Write database migrations (that's Harsh) |

**Critical rules:**
- The AI Gateway is the ONLY place in the codebase that calls the LLM API.
- All LLM outputs MUST be strictly validated against Zod schemas before returning to Kavya's orchestrator.

---

### 👤 Nisarg — Prediction + Risk Engine Lead
**You own:** The deterministic Risk Engine (Urgent vs Consult vs Self-Care), condition prediction mapping, uncertainty escalation rules, and red-flag pattern matching.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Calculate risk based on defined red flags (e.g., severe chest pain -> URGENT) | Let the LLM hallucinate or guess a risk level |
| Map structured symptoms to possible condition probabilities | Write the symptom extraction LLM calls (that's Nishith) |
| Build the Result Composer that formats final guidance and referrals | Manage Express routes or HTTP responses |

**Critical rules:**
- The Risk Engine must be 100% deterministic (no LLMs). Given the same structured symptoms, it must always return the exact same risk level.

---

### 👤 Vivek — Frontend Chat Engine Lead
**You own:** The interactive React chat UI, message bubbles, real-time typing indicators, local chat state (Zustand/Context), session persistence, and connecting the chat to Rutva's API.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Build the conversational interface and message history rendering | Build the final Results dashboard (that's Darshil) |
| Handle API requests for sending/receiving messages | Define backend schemas or routes |
| Implement loading states and error boundaries for the chat | Store sensitive JWT tokens in localStorage (use HttpOnly cookies) |

**Interface you consume (your dependency):**
- Rutva's API spec. If Rutva's API isn't ready, mock the responses using MSW or a hardcoded JSON timeout.

---

### 👤 Darshil — Frontend Assessment UX Lead
**You own:** The overall app shell/layout, symptom confirmation/editing UI, and the final Results presentation (Condition bars, risk level UI, map referrals).

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Present the Risk Engine data beautifully and accessibly (ARIA) | Write the Backend Risk Engine logic (that's Nisarg) |
| Build the external map referral UI and self-care cards | Build the core chat engine (that's Vivek) |
| Implement the optional Image Upload dropzone UI | Write backend image parsing logic (that's Mann) |

---

### 👤 Mann — Image / CV Lead
**You own:** Image upload endpoints, binary file validation (size, MIME type, malware scan), storage management (S3/local disk), and visual symptom extraction via Vision APIs.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Validate image buffers (reject oversized/invalid files) | Write the frontend image picker UI (that's Darshil/Vivek) |
| Call Vision APIs to extract symptoms from skin condition photos | Save images to the DB without checking size limits |
| Manage temporary image cleanup jobs | Write the main NLP extraction prompts (that's Nishith) |

---

### 👤 Mohit — QA + Testing Lead
**You own:** Test infrastructure (Vitest/Supertest), integration tests, E2E test scripts, load testing (Artillery), and the AI Evaluation Harness.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Run automated AI evaluation scripts (testing extraction accuracy) | Write the production code for the AI |
| Mock external dependencies (LLMs, Databases) in unit tests | Call real LLM APIs in standard unit/integration tests |
| File GitHub issues when test coverage drops below 70% | Fix other people's broken production code |

**Critical rules:**
- Test as you go. When a module is merged, write tests for it within 24 hours.
- The AI Extraction Evaluator must run against a fixed set of 50+ test cases to catch prompt regressions.

---

### 👤 Dimple — Security, Privacy & Safety Lead
**You own:** Consent screen logic, PII sanitization (stripping names/SSNs from chat), Helmet/CORS configuration, rate limiting, and ensuring the application remains strictly an *informational aid*.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Audit prompts and UI for mandatory medical disclaimers | Write the LLM prompts from scratch |
| Implement data deletion logic (Right to be Forgotten) | Change the state machine directly |
| Configure JWT expiration, secure cookies, and API rate limiters | Build the chat interface (that's Vivek) |

---

## Dependency & Integration Rules

### Rule 1 — Consume interfaces, not implementations
Wait for Rutva/Harsh to define the TypeScript types/Prisma schema. Depend on those types.
```typescript
// ✅ Correct — depend on the shared type contract
import { AssessmentResult } from '@shared/types';
```

### Rule 2 — Publish your interface before your implementation
On Day 1 of any week, every person should have their **interface stub** published (e.g., hardcoded JSON responses). This lets everyone work in parallel. Vivek cannot be blocked waiting for Nishith to finish prompt engineering.

### Rule 3 — Shared database tables have one writer
For any database table, only one person's code performs `INSERT`, `UPDATE`, and `DELETE`. Others may `SELECT`.
- `assessments` & `messages` → Kavya writes
- `symptoms` → Kavya writes (using data from Nishith)
- `users` → Dimple/Rutva writes

### Rule 4 — Config lives in one place
All configuration (DB URL, API keys, AI model names) lives in `.env`. Access them strictly through a centralized `config.ts` file.

### Rule 5 — Logging is structured
Every log statement must be structured (JSON-compatible).
```typescript
// ✅ Correct
logger.info({ event: 'extraction_complete', assessmentId, symptomCount: 3 });

// ❌ Wrong
console.log(`extracted 3 symptoms for ${assessmentId}`);
```

---

## Cross-Team Integration & Failure Protocols

The hardest part of this project is when one person's module fails. Here is exactly how failure is handled:

### 1. AI API Timeout (Nishith → Kavya → Vivek)
- **Nishith** does NOT crash the server. The AI gateway catches the timeout and returns `{ type: 'ERROR', message: 'Timeout' }`.
- **Kavya** does NOT transition the state to `ANALYZING`. The state remains `SYMPTOM_COLLECTION` or `CLARIFYING`.
- **Vivek** displays a retry-safe error to the user: *"I'm having trouble connecting. Can you say that again?"*

### 2. Invalid Image Upload (Mann → Kavya → Darshil)
- **Mann** rejects the image (e.g., too large, blurry) and returns a standard HTTP 400 error via Rutva's routes.
- **Kavya** ignores the image, treating it as if only text was sent.
- **Darshil** displays a toast notification: *"Image too blurry, continuing with text only."*

### 3. High Uncertainty Prediction (Nisarg → Darshil)
- **Nisarg** does NOT guess a condition. If model uncertainty is high (> 60%), Nisarg elevates the risk to `CONSULT_DOCTOR` to be safe.
- **Darshil** renders the condition list with a "Less Likely" badge and explicitly shows the user the elevated risk warning.

---

## Branch and Git Rules

```text
main                    ← Protected. PR-only. Passing CI required.
develop                 ← Integration branch.
kavya/state-machine     ← Your working branch. Format: {owner}/{description}
```

**Branch naming format:** `{owner}/{description}`
- Example: `nishith/clarification-prompt`
- Example: `harsh/user-schema`

**PR rules:**
- PR description must include: what changed, why, how to test it, and any interface changes.
- PRs into `main` require 1 approval from the module owner and 1 from Rutva (Backend) or Darshil/Vivek (Frontend).
- PRs must not break any existing CI tests.

**Commit message format:**
```text
feat(ai): extract severity and duration from prompt

- Implements Zod validation for symptom extraction
- Handles edge cases for missing duration

Task: W1-04
```

---

## What Happens When Rules Are Broken

| Violation | Consequence |
|-----------|-------------|
| Direct push to `main` | Revert immediately, PR required |
| Prisma Migration by non-Harsh | Deleted, Harsh rewrites it |
| LLM called outside Nishith's gateway | PR blocked until refactored |
| Secret committed to git | Rotate the secret immediately, scrub git history |
| Bypassing Kavya's state machine | Critical bug, fix before any other work |
| Interface changed without notice | Revert change, open a discussion, re-agree |

These are not punishments — they're guardrails that keep the team moving fast without breaking each other's work.

---

## Quick Reference Card

Print this and keep it visible.

```text
BEFORE WRITING CODE:
□ Does this touch another person's directory? → Ask first
□ Am I changing a published interface? → Discussion first
□ Do I depend on something not merged yet? → Use a mock

BEFORE OPENING A PR:
□ CI passes?
□ No secrets in code?
□ PR description complete?
□ Interface change documented?

WHEN BLOCKED:
□ Use a mock and keep going
□ File a GitHub Issue tagging the blocker
□ Flag in team channel after 4 hours

COMMUNICATION:
□ Bugs / schema changes → GitHub Issues
□ Quick questions → Slack
□ Architecture decisions → GitHub Discussions + documented in PR
```
