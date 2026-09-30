# Sprint Plan — AI-Based Symptom Checker (Group 14)

**Timeline:** Saturday 10 October 2026 → Friday 20 November 2026 (6 weeks). Dates may shift slightly. The leader updates this file and the GitHub milestones together.
**Team:** 10 members, each owning one module (see [rules.md](rules.md)).
**Scope source of truth:** [idea.md](idea.md). Requirement IDs (FR / NFR / DR) come from the Lab 6 report, `Group_14_project_report.pdf`.

---

## 1. Sprint calendar

| Sprint | Dates | Goal | Tasks per member | Maps to |
|---|---|---|---|---|
| **Sprint 0: Setup & Contracts** | Sat 10 Oct → Tue 13 Oct | Everyone can run the project locally. Shared types, API contract, DB schema and mocks are merged, so nobody is blocked in Sprint 1. | 1 | — |
| **Sprint 1: Walking Skeleton** | Wed 14 Oct → Tue 27 Oct | End-to-end flow works for real: chat → extraction → clarification → confirmation → prediction → risk → result → restart. | 4 | [WEEK_1.md](WEEK_1.md) |
| **Sprint 2: Feature Complete** | Wed 28 Oct → Tue 10 Nov | Image upload, accounts and history, self-care guidance, map referral, privacy controls, uncertainty escalation, full test suites. | 4 | [WEEK_2.md](WEEK_2.md) |
| **Sprint 3: Hardening & Release** | Wed 11 Nov → Fri 20 Nov | No new features. Accuracy, safety, security, accessibility, performance, deployment, demo. | 3 | [WEEK_3.md](WEEK_3.md) |

**Key dates**
- **Tue 27 Oct:** Sprint 1 review. Leader merges `develop → main` and tags `v0.1.0`.
- **Tue 10 Nov:** Sprint 2 review. `develop → main`, tag `v0.2.0`. **Feature freeze.**
- **Tue 17 Nov:** Code freeze. Only bug fixes from this date.
- **Fri 20 Nov:** Final release `v1.0.0` and demo.

Every member gets **12 tasks** in total (1 + 4 + 4 + 3). Every task is **one issue, one branch and one PR**.

---

## 2. Scope decision (read this once)

The Lab 6 report lists some doctor-side requirements. The team later narrowed the scope in [idea.md](idea.md). The narrowed scope wins:

| Report requirement | Decision |
|---|---|
| FR-01, 02, 04–07, 15–25 | **In scope** |
| FR-03 natural language + selectable list | **In scope** (the list is used when editing symptoms) |
| FR-03 voice input | **Out of scope** (voice assistant excluded in idea.md) |
| FR-08 "suggest doctors" | **Reinterpreted:** external map search by specialty (idea.md feature 9). No doctor database. |
| FR-09 to FR-14, DR-07 (doctor directory, booking, reminders, doctor dashboard, ratings, admin panel, credential verification) | **Out of scope** |
| All NFRs and DR-01–06, DR-08 | **In scope** |

If a task seems to need an out-of-scope feature, stop and ask the leader in the issue.

---

## 3. Ownership codes

| Code | Member | Module |
|---|---|---|
| NIS | Nisarg (leader) | Prediction, risk engine, result composer — `server/src/services/prediction/`, `ai/datasets/` |
| RUT | Rutva | Server foundation, routes, config, CI/CD, deployment — `server/src/routes/`, `server/src/config/`, Docker |
| HAR | Harsh | Database — `server/prisma/`, `server/src/repositories/` |
| KAV | Kavya | Assessment orchestration & state machine — `server/src/services/assessment/` |
| NIT | Nishith | AI gateway, prompts, extraction — `server/src/services/ai/`, `ai/prompts/` |
| VIV | Vivek | Chat UI & client state — `client/src/components/chat/`, `client/src/stores/`, `client/src/services/` |
| DAR | Darshil | App shell, confirmation, results, referral UI — `client/src/pages/`, `client/src/components/{assessment,result,common}/` |
| MAN | Mann | Image upload & CV — `server/src/services/image/`, `ai/cv/` |
| MOH | Mohit | Test infrastructure, integration/E2E/AI-eval — `tests/`, `ai/evaluation/` |
| DIM | Dimple | Security, privacy, consent, safety — `server/src/middleware/security/`, `server/src/services/privacy/`, `client/src/components/consent/` |

Task IDs look like `S1-KAV-2` (Sprint 1, Kavya, 2nd task). Do tasks **in the listed order** unless the leader says otherwise.

---

## 4. Sprint 0: Setup & Contracts (10–13 Oct)

| ID | Task | Req. |
|---|---|---|
| S0-RUT-1 | Scaffold `server/`: Express + TypeScript, ESLint (+ `eslint-plugin-jsdoc`), Prettier, Vitest, `config.ts` reading `.env`, Pino logger, `GET /api/v1/health`, `docker-compose.yml` (Postgres), `.env.example`. Scripts: `lint`, `typecheck`, `test`, `dev`. Enable npm/pip in `dependabot.yml`. | NFR-08 |
| S0-VIV-1 | Scaffold `client/`: Vite + React 18 + TypeScript, ESLint (+ jsdoc), Prettier, Vitest + RTL, React Router, Zustand, `apiClient.ts` with base URL from env. Scripts: `lint`, `typecheck`, `test`, `build`. | NFR-08 |
| S0-KAV-1 | Publish shared contracts in `shared/types/`: `AssessmentState` enum, `Symptom`, `Message`, `Condition`, `RiskLevel`, `AssessmentResult`. Frontend and backend both import from here. | — |
| S0-HAR-1 | Prisma init + first migration: `User`, `Assessment`, `Message`, `Symptom`, `Consent`. Seed script with 3 demo assessments. ER diagram in `docs/database.md`. | FR-01 |
| S0-NIT-1 | `AiGateway` interface + `MockAiProvider` (`AI_PROVIDER=mock`) that returns fixture extractions, so nobody needs an API key to develop or test. | — |
| S0-NIS-1 | Dataset v0 in `ai/datasets/`: ~30 common conditions with ICD-10 code, key symptoms, specialty, and a red-flag symptom list (JSON). Sources documented. | DR-03, DR-04 |
| S0-DAR-1 | UX foundation: wireframes of every screen in `docs/ux/`, design tokens (colours, spacing, type), `AppLayout` with persistent disclaimer footer. | DR-01, NFR-06 |
| S0-MAN-1 | Image pipeline design doc (`docs/image-pipeline.md`): accepted types and size, validation steps, storage and deletion policy, `ImageAnalyzer` interface and its mock. | — |
| S0-MOH-1 | `docs/TEST_PLAN.md` (levels, tools, coverage target 70%), Playwright scaffold in `tests/e2e/`, AI eval case format + first 20 cases in `ai/evaluation/cases.json`. | NFR-07 |
| S0-DIM-1 | `docs/privacy-and-safety.md`: data inventory, DPDP Act 2023 checklist, final disclaimer and consent wording, list of banned phrases ("you have", "diagnosis", "take X mg"…). | DR-01, DR-05, DR-06, DR-08 |

**Sprint 0 exit:** `develop` builds in CI, `npm run dev` works in both apps, and all contracts are merged.

---

## 5. Sprint 1: Walking Skeleton (14–27 Oct)

| ID | Task | Req. |
|---|---|---|
| S1-RUT-1 | OpenAPI v1 spec (`docs/api/openapi.yaml`) + route stubs returning mock data: `POST /assessments`, `POST /assessments/:id/messages`, `PUT /assessments/:id/symptoms`, `POST /assessments/:id/confirm`, `GET /assessments/:id/result`. | — |
| S1-RUT-2 | Central error handler, Zod request-validation middleware, correlation-ID middleware, structured request logs. | NFR-05, NFR-10 |
| S1-RUT-3 | Replace stubs: wire routes → controllers → `AssessmentOrchestrator`. | — |
| S1-RUT-4 | Extend CI: build Docker image of server; run Prisma migrations against the CI Postgres. | NFR-08 |
| S1-HAR-1 | Repository layer: `assessment.repository.ts`, `message.repository.ts` (CRUD, typed with Prisma). | — |
| S1-HAR-2 | Symptom persistence with structured JSONB (severity, duration, body site) + `symptom.repository.ts`. | FR-17 |
| S1-HAR-3 | Guest sessions: anonymous session token model, assessment ownership by session. | idea §10 |
| S1-HAR-4 | Indexes for the hot queries, migration review, realistic seed data for the demo. | NFR-01 |
| S1-KAV-1 | Assessment state machine: `START → SYMPTOM_COLLECTION → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`, with guarded transitions and unit tests. | — |
| S1-KAV-2 | `processMessage()`: store message → AI extraction → merge symptoms → decide next state. | FR-03, FR-17 |
| S1-KAV-3 | Clarification loop capped at 3 turns. After the cap, move to confirmation and flag low confidence. | FR-04, FR-19, FR-20 |
| S1-KAV-4 | `confirmSymptoms()` (add / remove / edit) and `restartAssessment()`. | FR-16, FR-21, FR-25 |
| S1-NIT-1 | Extraction prompt v1 + Zod output schema (symptom, severity, duration, onset, body site). | FR-03, FR-17 |
| S1-NIT-2 | Symptom normalization: map lay terms to canonical names ("tummy ache" → abdominal pain). | FR-03 |
| S1-NIT-3 | Missing-information detection + clarification question generation (max 3 questions). | FR-04, FR-19, FR-20 |
| S1-NIT-4 | Real OpenAI provider: JSON mode, timeout, 2 retries, typed `AiError` on failure. | NFR-05 |
| S1-NIS-1 | Baseline condition predictor: weighted symptom-overlap scoring over the dataset, returning the top 3. | FR-05, FR-22 |
| S1-NIS-2 | Confidence mapping to "Likely / Possible / Less likely" (never raw percentages to the user). | FR-23 |
| S1-NIS-3 | Deterministic risk engine: SELF_CARE / CONSULT_DOCTOR / URGENT, with red-flag override. | FR-06, FR-15, DR-02 |
| S1-NIS-4 | Specialty mapper + `ResultComposer` that builds the final `AssessmentResult`. | FR-07, DR-04 |
| S1-VIV-1 | Chat UI: `ChatContainer`, `MessageBubble`, `MessageInput`, auto-scroll. | idea §1, §2 |
| S1-VIV-2 | `assessmentStore` (Zustand) + `assessmentApi.ts`, using MSW mocks until S1-RUT-3 merges. | — |
| S1-VIV-3 | Typing indicator, loading, error and retry states in the chat. | NFR-05 |
| S1-VIV-4 | "Start new assessment" button, always visible, with confirm dialog. | FR-25 |
| S1-DAR-1 | Landing page + start flow + disclaimer banner shown before the first message. | DR-01 |
| S1-DAR-2 | `SymptomConfirmationCard`: list, edit, remove, add from a selectable list. | FR-16, FR-21, FR-03 |
| S1-DAR-3 | `ConditionList` with confidence badges and a short "why" line. | FR-22, FR-23 |
| S1-DAR-4 | `RiskBadge` + full-screen urgent-care alert for URGENT results. | FR-06, FR-15 |
| S1-MAN-1 | `POST /assessments/:id/images`: Multer, 5 MB limit, MIME + magic-byte check. | idea §3 |
| S1-MAN-2 | Sharp preprocessing: strip EXIF/GPS, resize, normalise format. | NFR-04 |
| S1-MAN-3 | Temporary image storage + scheduled cleanup job. | DR-06 |
| S1-MAN-4 | `MockImageAnalyzer` wired to the orchestrator contract (returns visual findings). | — |
| S1-MOH-1 | Unit tests for the state machine (every valid and invalid transition). | — |
| S1-MOH-2 | Supertest integration tests for the full assessment API flow with `AI_PROVIDER=mock`. | — |
| S1-MOH-3 | AI eval harness v1 (`ai/evaluation/evaluate.py`), 50 cases, precision/recall report. | NFR-07 |
| S1-MOH-4 | Playwright E2E happy path: start → describe → clarify → confirm → result → restart. | — |
| S1-DIM-1 | Consent step (UI + `POST /consents` + stored consent version) before anything is saved. | DR-08 |
| S1-DIM-2 | Helmet, CORS allow-list, rate limiting on assessment and auth routes. | NFR-03 |
| S1-DIM-3 | PII scrubber applied to user text before it reaches the LLM (names, phones, emails, IDs). | NFR-04, DR-06 |
| S1-DIM-4 | Safety-language check: unit-tested `assertSafeWording()` used by `ResultComposer`, blocking banned phrases. | DR-05 |

**Sprint 1 exit (demo):** "I have fever and headache since yesterday" runs through the real backend to a result with 2–3 conditions, a risk level and a disclaimer. Then restart.

---

## 6. Sprint 2: Feature Complete (28 Oct – 10 Nov)

| ID | Task | Req. |
|---|---|---|
| S2-RUT-1 | Auth routes: register, login, logout, with JWT in an HttpOnly cookie. | FR-01 |
| S2-RUT-2 | History endpoints: list and view past assessments (paginated). | FR-02 |
| S2-RUT-3 | Staging deployment (Docker, Render/Railway or similar) + auto-deploy from `main`. | NFR-05 |
| S2-RUT-4 | Audit log of every analysis and recommendation (who, when, engine version). | NFR-10 |
| S2-HAR-1 | Profile model: age band, sex, chronic conditions (all optional). | FR-02 |
| S2-HAR-2 | History queries + pagination + ownership filters. | FR-02 |
| S2-HAR-3 | Guest data TTL purge job (e.g. 24 h). | DR-06 |
| S2-HAR-4 | Cascading account deletion at the data layer. | DR-06 |
| S2-KAV-1 | Claim a guest assessment into a new account after sign-up. | idea §10 |
| S2-KAV-2 | Merge image findings into assessment state. | idea §3 |
| S2-KAV-3 | Pass profile context (age, chronic conditions) into analysis, as in the activity diagram. | FR-02 |
| S2-KAV-4 | Idempotent message processing + transactions (no double answers on retry). | NFR-05 |
| S2-NIT-1 | Multi-turn context: answers to clarifying questions update the right symptom. | FR-19 |
| S2-NIT-2 | Prompt-injection defence + polite refusal of off-topic chat. | idea "out of scope" |
| S2-NIT-3 | Symptom definitions on request ("what is nausea?") from a curated glossary, not free LLM text. | FR-18 |
| S2-NIT-4 | Prompt v2 driven by eval results. Target ≥ 85% extraction F1. Prompts versioned in `ai/prompts/`. | NFR-07 |
| S2-NIS-1 | Uncertainty escalation: low confidence always raises the risk tier, never lowers it. | idea §7, NFR-07 |
| S2-NIS-2 | Contributing-factor explanations ("because you reported X and Y"). | FR-24 |
| S2-NIS-3 | Self-care guidance content per condition (general advice only, reviewed by Dimple). | idea §8, DR-05 |
| S2-NIS-4 | Predictor v2 (e.g. Naive Bayes on the dataset) compared against the baseline, with results documented. | FR-05, NFR-07 |
| S2-VIV-1 | Image attach in chat, offered only when visual symptoms are detected. | idea §3 |
| S2-VIV-2 | Login / register UI + `authStore`. | FR-01 |
| S2-VIV-3 | History page (list + detail). | FR-02 |
| S2-VIV-4 | Session persistence: resume an unfinished assessment after refresh. | NFR-05 |
| S2-DAR-1 | Doctor referral: "Find a <specialty> near me" opens an external map search. No doctor data is stored. | FR-08*, idea §9 |
| S2-DAR-2 | Self-care guidance cards for low-risk results. | idea §8 |
| S2-DAR-3 | Profile page (optional fields, clear "why we ask"). | FR-02 |
| S2-DAR-4 | Symptom-definition tooltips + "why this result" explanation panel. | FR-18, FR-24 |
| S2-MAN-1 | CV microservice (FastAPI) with a pretrained skin-condition model behind `ImageAnalyzer`. | idea §3 |
| S2-MAN-2 | Map model labels to visual symptoms the orchestrator understands. | — |
| S2-MAN-3 | Image quality checks (blur, darkness, size) with friendly rejection messages. | NFR-05 |
| S2-MAN-4 | Delete images immediately after analysis. Store findings only. | DR-06 |
| S2-MOH-1 | Risk-engine test matrix: every red flag, 100% branch coverage. | DR-02 |
| S2-MOH-2 | Auth, privacy and deletion integration tests. | NFR-03, NFR-04 |
| S2-MOH-3 | Frontend component tests for chat, confirmation and results. | — |
| S2-MOH-4 | Coverage gate (70%) in CI + test report artifact. | NFR-08 |
| S2-DIM-1 | "Delete my data" and "Export my data" endpoints + UI. | DR-06, NFR-04 |
| S2-DIM-2 | JWT expiry/refresh, secure cookie flags, CSRF protection. | NFR-03 |
| S2-DIM-3 | Emergency UX review: urgent result shows the local emergency number (112) first. | FR-15, DR-02 |
| S2-DIM-4 | Privacy policy page + consent versioning (re-ask when the policy changes). | DR-08 |

**Sprint 2 exit:** every in-scope feature from idea.md works on staging. Feature freeze.

---

## 7. Sprint 3: Hardening & Release (11–20 Nov)

| ID | Task | Req. |
|---|---|---|
| S3-RUT-1 | Production deployment with HTTPS + environment configuration. | NFR-03 |
| S3-RUT-2 | Health checks, uptime monitoring, rollback procedure. | NFR-05 |
| S3-RUT-3 | Release `v1.0.0`: changelog, release notes, final README. | NFR-08 |
| S3-HAR-1 | Query performance review (EXPLAIN) + index fixes. | NFR-01 |
| S3-HAR-2 | Backup and restore script, tested once. | NFR-05 |
| S3-HAR-3 | Data-integrity tests + final database documentation. | NFR-08 |
| S3-KAV-1 | API contract freeze + authorization audit (no cross-user access). | NFR-03 |
| S3-KAV-2 | Input validation and per-endpoint rate-limit audit. | NFR-03 |
| S3-KAV-3 | Performance: p95 result time ≤ 5 s. | NFR-01 |
| S3-NIT-1 | Full AI regression run + fixes. | NFR-07 |
| S3-NIT-2 | Fallback provider (Gemini/Ollama) + latency budget. | NFR-05 |
| S3-NIT-3 | AI documentation: prompts, limitations, failure modes. | NFR-08 |
| S3-NIS-1 | Final model evaluation report (accuracy, confusion matrix, risk recall on red flags). | NFR-07 |
| S3-NIS-2 | Risk-consistency verification (same input → same output, 1000 runs). | DR-02 |
| S3-NIS-3 | Model card: data, method, limits, intended use. | NFR-08 |
| S3-VIV-1 | Responsive/mobile pass for all chat screens. | NFR-09 |
| S3-VIV-2 | Frontend performance: code splitting, Lighthouse ≥ 90. | NFR-01 |
| S3-VIV-3 | i18n framework + Hindi translation of the chat UI. | NFR-06 |
| S3-DAR-1 | WCAG 2.1 AA audit + fixes. | NFR-06 |
| S3-DAR-2 | Usability test with 5 users + top-5 fixes. | NFR-06 |
| S3-DAR-3 | Final visual polish + demo script walkthrough. | — |
| S3-MAN-1 | CV evaluation + failure testing (bad, irrelevant and edge images). | NFR-07 |
| S3-MAN-2 | Inference performance (≤ 3 s per image). | NFR-01 |
| S3-MAN-3 | CV documentation and limitations. | NFR-08 |
| S3-MOH-1 | Full regression + E2E matrix (browsers × devices). | NFR-09 |
| S3-MOH-2 | Load test (Artillery) against staging. | NFR-02 |
| S3-MOH-3 | Bug triage + release QA sign-off report. | — |
| S3-DIM-1 | OWASP Top 10 review + fixes. | NFR-03 |
| S3-DIM-2 | Final safety and disclaimer audit of every user-facing string. | DR-01, DR-05 |
| S3-DIM-3 | DPDP compliance document + final data inventory. | NFR-04, DR-06 |

---

## 8. Workload and commit balance

- **Equal load:** everyone has 12 tasks of similar size. If a task turns out much bigger, the leader splits it and moves part to the next sprint.
- **One task at a time:** you may have only **one open PR** (the "PR policy" check enforces this). Start the next task after the current PR is merged.
- **Commit target:** at least **3 meaningful commits per PR**, which comes to about **40–60 commits per member** by 20 Nov. Commit each logical step: scaffold → logic → tests → docs.
- **Padding is not allowed.** Commits like "update", "fix typo" ×10, or whitespace-only changes are rejected in review. Quality counts, not just quantity.
- **Tracking:** every Monday the **Contribution Report** workflow posts commits and merged PRs per member. Anyone under 75% of the team median is flagged, and the leader rebalances in sprint planning.
- **Your commits must count:** your `git config user.email` must be an email verified on your GitHub account. Otherwise your commits don't show up.

---

## 9. Ceremonies

| When | What | Who |
|---|---|---|
| First day of each sprint | **Sprint planning** (30 min): confirm tasks, leader creates and assigns issues in the sprint milestone | All |
| Daily | **Async stand-up** in the team channel: yesterday / today / blocked? | All |
| Within 24 h of a PR opening | **Review:** leader reviews; module owner is tagged when their area is touched | Leader + owner |
| Last day of each sprint | **Sprint review** (demo on `develop`) → leader merges `develop → main` and tags a release | All |
| Right after review | **Retro** (15 min): keep / stop / start, recorded in `docs/retros/sprint-N.md` | All |

## 10. Definition of Done (every task)

1. Acceptance criteria in the issue are met.
2. Code follows [AI_RULES.md](../AI_RULES.md) (naming, file headers, doc comments, SE principles).
3. Unit tests added. CI is green ("CI passed" + "PR policy").
4. No secrets, no real patient data, no out-of-scope features.
5. Reviewed and merged by the leader into `develop`. Issue closed automatically.
