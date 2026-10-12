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

## Teams

Teams were re-formed on 12 Oct 2026 from the team poll. The task list for each member is in [SPRINT_PLAN.md](SPRINT_PLAN.md) §3–§7.

| Team | Members |
|---|---|
| **AI / ML** | Nisarg (lead, ≈ 60% of the AI/ML work), Nishith (≈ 20%), Kavya (≈ 20%) |
| **Backend** | Darshil, Harsh, Vivek, Mohit |
| **Database** | Nishith, Kavya, Dimple |
| **Frontend + Deployment** | Rutva, Dimple, Mann |
| **Testing** | Mohit (lead), Rutva, Mann, Nisarg |

---

## Directory Ownership Map

This is who owns which part of the codebase. **You do not create files in someone else's directory without their approval.**

```text
project-root/                     (full layout and stack: docs/tech-stack.md)
├── client/                       ← Frontend: React PWA on Vercel
│   ├── package.json, configs     ← Rutva (scaffold, lint/test/build tooling)
│   ├── src/components/chat/      ← Rutva
│   ├── src/stores/, src/services/← Rutva
│   ├── src/components/{layout,assessment,result}/ ← Mann
│   ├── src/pages/                ← Mann (a page created by someone else's task is theirs; Mann reviews)
│   ├── src/i18n/                 ← Mann
│   ├── src/components/{consent,privacy,risk}/ ← Dimple
│   ├── src/types/api.gen.ts      ← generated from the server OpenAPI; never edit by hand
│   ├── vite.config.ts            ← Rutva (PWA, proxy)
│   └── vercel.json               ← Dimple (headers, rewrites; Rutva reviews)
├── server/                       ← Backend: FastAPI, shipped as a Docker image (Render or VPS)
│   ├── app/main.py, app/api/     ← Vivek (app factory, routers)
│   ├── app/core/                 ← Vivek (config, logging, errors, security utils)
│   ├── app/middleware/           ← Harsh (security headers, rate limits)
│   ├── app/schemas/              ← Darshil (API contracts; changes need team agreement)
│   ├── app/services/
│   │   ├── assessment/           ← Darshil (orchestration, state machine)
│   │   ├── ai/                   ← Nishith (gateway, prompts, extraction)
│   │   ├── knowledge/            ← Kavya (symptom normalization, glossary, self-care content)
│   │   ├── prediction/           ← Nisarg (risk engine, condition model, result composer)
│   │   ├── image/                ← Nisarg (CV analyzer, ONNX inference)
│   │   ├── upload/               ← Vivek (image upload validation)
│   │   ├── auth/                 ← Vivek (accounts, JWT)
│   │   └── privacy/              ← Harsh (consent, PII scrubbing, safety wording, export/deletion)
│   ├── app/models/, app/repositories/, app/db/ ← Database team: Nishith, Kavya, Dimple
│   ├── alembic/                  ← Database team (migrations ONLY)
│   ├── tests/unit/<module>/      ← module owner
│   ├── tests/integration/, tests/conftest.py ← Mohit
│   └── Dockerfile                ← Rutva
├── ml/                           ← Training & evaluation (never deployed)
│   ├── prediction/, datasets/conditions/ ← Nisarg
│   ├── cv/, datasets/images/     ← Nisarg
│   ├── nlp_eval/, datasets/symptoms/ ← Kavya (with Nishith)
├── tests/e2e/                    ← Mohit (Playwright)
├── .github/, render.yaml, deploy/ ← Nisarg (leader) approves; Rutva maintains CI/CD and deployment
└── docs/                         ← Everyone reads, the leader maintains
```

---

## Per-Member Ownership & Hard Boundaries

---

### 👤 Nisarg — Team Leader · AI/ML Lead (Prediction, Risk Engine, CV)
**You own:** The deterministic Risk Engine (Urgent vs Consult vs Self-Care), condition prediction, uncertainty escalation, red-flag rules, the Result Composer, the CV model (dataset pipeline, training, ONNX export, serving), optional vector retrieval, and verification of all of these (risk-engine test matrix, consistency runs, model evaluation and model cards).

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Calculate risk from defined red flags (e.g., severe chest pain -> URGENT) | Let an LLM, a model or randomness decide or lower a risk level |
| Map structured symptoms to possible conditions (rule baseline, then a scikit-learn model trained in `ml/prediction/` and served as ONNX) | Write the symptom extraction LLM calls (that's Nishith) |
| Train, evaluate (incl. per-skin-tone fairness) and serve the CV model | Store images anywhere (disk, DB, logs); they are processed in memory only |
| Build the Result Composer that formats final guidance and referrals | Manage FastAPI routers or HTTP responses (that's Vivek) |

**Critical rules:**
- The Risk Engine must be 100% deterministic (no LLMs). Given the same structured symptoms, it must always return the exact same risk level.
- ML outputs (condition model, CV model, vector retrieval) are inputs to the risk engine. They can add symptoms or raise risk, never lower it.

---

### 👤 Nishith — AI/ML (LLM) + Database
**You own:** LLM integration (the `AiGateway`, OpenAI with Gemini fallback), extraction and clarification prompts, JSON schema enforcement, multi-turn context, prompt-injection defence. On the Database team: repositories, audit-log storage, query performance, backup and restore.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Write and version extraction & clarification prompts (`ai/prompts/`) | Call LLMs from anywhere except the AI gateway |
| Parse, validate, and repair AI JSON outputs (Pydantic) | Write the risk calculation logic (that's Nisarg) |
| Handle AI API timeouts, retries, and fallback errors | Write the frontend chat component (that's Rutva) |
| Write repositories and migrations as part of the Database team | Start a migration without telling the Database team first |

**Critical rules:**
- The AI Gateway is the ONLY place in the codebase that calls the LLM API.
- All LLM outputs MUST be strictly validated against Pydantic models before returning to Darshil's orchestrator.

---

### 👤 Kavya — AI/ML (Normalization, Glossary, Evaluation) + Database
**You own:** The canonical symptom vocabulary, deterministic symptom normalization, the curated symptom glossary, self-care content, and the NLP evaluation harness (`ml/nlp_eval/`). On the Database team: guest sessions, profile and history queries, data-integrity tests, migration safety.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Map lay terms to canonical symptoms deterministically | Generate glossary or self-care text with free LLM output |
| Run the extraction evaluation (50+ fixed cases) and report regressions | Change prompts directly (send the findings to Nishith) |
| Write repositories and migrations as part of the Database team | Start a migration without telling the Database team first |

---

### 👤 Darshil — Backend: Assessment Orchestration
**You own:** The core Assessment State Machine (`START → SYMPTOM_COLLECTION → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`), session coordination, the central orchestration service (`app/services/assessment/orchestrator.py`), and the Pydantic API contracts in `app/schemas/`.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Enforce strict state transitions (e.g., block analysis if state != READY) | Write the actual LLM prompt (that's Nishith) |
| Call AI extraction and save output through the Database team's repositories | Write FastAPI routers directly (that's Vivek) |
| Manage the 3-turn clarification loop limit | Write frontend UI |
| Guard assessment ownership (block cross-user access) | Write database migrations (Database team) |

**Interface you publish (others depend on this):**
```python
class AssessmentOrchestrator:
    async def process_message(self, assessment_id: UUID, message: str) -> ProcessResult: ...
    async def confirm_symptoms(self, assessment_id: UUID, symptoms: list[Symptom]) -> None: ...
    async def generate_result(self, assessment_id: UUID) -> AssessmentResult: ...
```
Vivek's routers call these methods (injected with `Depends`).

---

### 👤 Vivek — Backend: API Foundation, Auth, Uploads
**You own:** The FastAPI app factory, routers, config, structlog logging, the error model and request IDs, auth (accounts, JWT cookies, CSRF), profile endpoints, the audit log, and image upload validation.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Write routers in `server/app/api/v1/` that call the services | Write the assessment state machine logic (that's Darshil) |
| Publish the REST API and OpenAPI spec | Write AI extraction logic (that's Nishith) |
| Validate uploads (size, MIME, magic bytes, EXIF) in memory | Write images to disk, the DB or logs |
| Set up structlog, request IDs and the error model | Change ORM models or migrations (Database team) |

**Interface you publish (others depend on this):**
- All REST API endpoints (e.g., `POST /api/v1/assessments`, `POST /api/v1/assessments/{id}/messages`) with exact URL, method, request body, and response schema. Rutva's frontend mocks against it immediately.

---

### 👤 Harsh — Backend: Security, Privacy & Consent Services
**You own:** Security headers, CORS, rate limits (`slowapi`), the PII scrubber, the safety-wording guard, the consent service and consent versioning, history endpoints, data export/deletion endpoints, and the guest-data purge job.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Scrub PII from user text before it reaches the LLM | Write LLM prompts (that's Nishith) |
| Block banned wording in results (`assert_safe_wording()`) | Change the state machine directly (that's Darshil) |
| Implement export and "delete my data" services | Write migrations (Database team) |

---

### 👤 Mohit — Backend Testing + QA Lead
**You own:** Test infrastructure (pytest fixtures, Vitest setup), integration and contract tests, E2E tests (Playwright), safety and authorization tests, load testing, the coverage gate and the release QA sign-off.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Mock external dependencies (LLMs, CV, DB) in tests | Call real LLM APIs in standard unit/integration tests |
| File GitHub issues when coverage drops below 70% | Fix other people's broken production code |

**Critical rule:** When a module is merged, write its integration tests within 24 hours.

---

### 👤 Rutva — Frontend + Deployment + Testing
**You own:** The `client/` scaffold and tooling, the chat UI, client stores and API services, PWA behaviour, and the whole delivery pipeline: CI/CD workflows, the Dockerfile and image registry, `render.yaml`, `deploy/vps/`, Vercel, production releases and post-deploy smoke tests.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Build the conversational interface and API calls (TanStack Query + Zustand) | Define backend schemas or routes |
| Keep CI/CD green and deployments reproducible | Approve deployments or merge PRs (leader only) |
| Keep API responses out of the service-worker cache | Store tokens or health data in `localStorage` |

---

### 👤 Mann — Frontend + Deployment + Testing
**You own:** The app shell and layout, symptom confirmation/editing UI, the results page, doctor referral via map, the image-attach UI, symptom tooltips and the "why" panel, i18n (Hindi), frontend component tests, and the rollback drill / demo-day plan.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Present the risk engine's output clearly and accessibly (ARIA) | Write backend risk or CV logic (that's Nisarg) |
| Open an external map search for the specialty | Store or show any doctor data |

---

### 👤 Dimple — Frontend + Deployment + Database
**You own:** The consent step UI, landing page and disclaimer, `RiskBadge` and the urgent-care screen (112 first), profile and privacy pages, self-care cards, `vercel.json` and client monitoring, the privacy and safety documentation, and, on the Database team, consent storage, guest-data TTL purge and cascading account deletion.

**Your hard boundaries:**
| ✅ You do this | ❌ You do NOT do this |
|---------------|-----------------------|
| Audit every user-facing string for the mandatory disclaimer and banned phrases | Write the LLM prompts |
| Make the urgent screen show the emergency number first | Change the state machine directly (that's Darshil) |
| Write retention/deletion repositories with the Database team | Start a migration without telling the Database team first |

---

### 🗄️ Database team rules (Nishith, Kavya, Dimple)
- **Only the Database team creates migration files.** Anyone else who needs a schema change requests it in a GitHub Issue.
- One migration at a time: announce "starting a migration" in the team channel, so two migrations never branch from the same head.
- **Never drop a column in production without a two-step migration** (add new, migrate data, drop old).
- Repositories are the only code that touches the SQLAlchemy session.

---

## Dependency & Integration Rules

### Rule 1 — Consume interfaces, not implementations
Kavya publishes the Pydantic API contracts in `server/app/schemas/`. The frontend depends on the TypeScript types generated from them. Nobody hand-writes duplicate types.
```python
# ✅ Correct: depend on the shared contract
from app.schemas.assessment import AssessmentResult
```
```ts
// ✅ Correct: generated from the server OpenAPI (npm run gen:api)
import type { components } from '@/types/api.gen';
type AssessmentResult = components['schemas']['AssessmentResult'];
```

### Rule 2 — Publish your interface before your implementation
On Day 1 of any week, every person should have their **interface stub** published (e.g., hardcoded JSON responses). This lets everyone work in parallel. Rutva's chat UI cannot be blocked waiting for Nishith to finish prompt engineering.

### Rule 3 — Shared database tables have one writer
For any database table, only one person's code performs `INSERT`, `UPDATE`, and `DELETE`. Others may `SELECT`.
- `assessments` & `messages` → Darshil's orchestrator writes
- `symptoms` → Darshil's orchestrator writes (using data from Nishith)
- `users` → Vivek's auth service writes
- `consents` → Harsh's consent service writes

### Rule 4 — Config lives in one place
All configuration (DB URL, API keys, AI model names) lives in `.env`. Access them strictly through `server/app/core/config.py` (pydantic-settings). The frontend has no secrets.

### Rule 5 — Logging is structured
Every log statement must be structured (JSON-compatible).
```python
# ✅ Correct
log.info("extraction_complete", assessment_id=assessment_id, symptom_count=3)

# ❌ Wrong
print(f"extracted 3 symptoms for {assessment_id}")
```

---

## Cross-Team Integration & Failure Protocols

The hardest part of this project is when one person's module fails. Here is exactly how failure is handled:

### 1. AI API Timeout (Nishith → Darshil → Rutva)
- **Nishith** does NOT crash the server. The AI gateway catches the timeout and returns `{ type: 'ERROR', message: 'Timeout' }`.
- **Darshil** does NOT transition the state to `ANALYZING`. The state remains `SYMPTOM_COLLECTION` or `CLARIFYING`.
- **Rutva** displays a retry-safe error to the user: *"I'm having trouble connecting. Can you say that again?"*

### 2. Invalid Image Upload (Vivek / Nisarg → Darshil → Mann)
- **Vivek** rejects an invalid file (too large, wrong type) and **Nisarg's** analyzer returns `unclear` for an unusable photo (blurry, dark). Both come back as a standard HTTP 400 error.
- **Darshil** ignores the image, treating it as if only text was sent.
- **Mann** displays a toast notification: *"Image too blurry, continuing with text only."*

### 3. High Uncertainty Prediction (Nisarg → Mann / Dimple)
- **Nisarg** does NOT guess a condition. If model uncertainty is high (> 60%), Nisarg elevates the risk to `CONSULT_DOCTOR` to be safe.
- **Mann** renders the condition list with a "Less Likely" badge and **Dimple's** `RiskBadge` explicitly shows the user the elevated risk warning.

---

## Branch and Git Rules

The full workflow is in [CONTRIBUTING.md](../CONTRIBUTING.md). GitHub enforces it automatically (see [github-setup.md](github-setup.md)).

```text
main                          ← Stable releases. Leader merges develop → main at each sprint review.
develop                       ← Default/integration branch. Every feature PR targets develop.
kavya/23-clarification-limit  ← Your working branch. Format: {name}/{issue-no}-{short-desc}
```

**PR rules:**
- **One feature at a time:** one open PR per member. One PR = one issue = one task from [SPRINT_PLAN.md](SPRINT_PLAN.md).
- The PR description follows the template: what changed, why, how to test, interface changes, and `Closes #N`.
- **Every PR needs the team leader's approval** (CODEOWNERS), plus green `CI passed` and `PR policy` checks. Only the leader merges.
- If a PR changes another member's interface, tag that member for review. The leader will not merge without their 👍 in the thread.
- Merge method is **merge commit** (squash is disabled) so everyone's commits are kept.

**Commit message format** (Conventional Commits, checked by CI):
```text
feat(ai): extract severity and duration from prompt

- Implements Pydantic validation for symptom extraction
- Handles edge cases for missing duration

Refs: #23
```

**Code style, naming and documentation:** see [AI_RULES.md](../AI_RULES.md). It applies to humans and AI assistants alike.

---

## What Happens When Rules Are Broken

| Violation | Consequence |
|-----------|-------------|
| Direct push to `main` | Revert immediately, PR required |
| Alembic migration from outside the Database team | Deleted, the Database team rewrites it |
| LLM called outside Nishith's gateway | PR blocked until refactored |
| Secret committed to git | Rotate the secret immediately, scrub git history |
| Bypassing Darshil's state machine | Critical bug, fix before any other work |
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
