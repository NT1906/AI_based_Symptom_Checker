# Sprint Plan — AI-Based Symptom Checker (Group 14)

**Timeline:** Saturday 10 October 2026 → Friday 20 November 2026 (6 weeks). Dates may shift slightly. The leader updates this file and the GitHub milestones together.
**Team:** 10 members in 5 teams. Every member owns specific folders (§3). The full ownership map and per-member boundaries are in [rules.md](rules.md).
**Scope source of truth:** [idea.md](idea.md). **Stack:** [tech-stack.md](tech-stack.md) (React PWA on Vercel, FastAPI in Docker on Render or a VPS, CV models trained in `ml/`). Requirement IDs (FR / NFR / DR) come from the Lab 6 report, `Group_14_project_report.pdf`.

> **Team change, 12 Oct 2026.** Teams were re-formed from the team poll. Starting now, every task below is assigned to its new owner.
> The one exception is **S0-HAR-1**: it is already in review (PR #10) and stays with Harsh. After it merges, the database folders pass to the Database team (Nishith, Kavya, Dimple).

---

## 1. Sprint calendar

| Sprint | Dates | Goal | Tasks per member | Maps to |
|---|---|---|---|---|
| **Sprint 0: Setup & Contracts** | Sat 10 Oct → Tue 13 Oct | Everyone can run the project locally. Shared types, API contract, DB schema and mocks are merged, so nobody is blocked in Sprint 1. | 1 (Nisarg 2) | — |
| **Sprint 1: Walking Skeleton** | Wed 14 Oct → Tue 27 Oct | End-to-end flow works for real: chat → extraction → clarification → confirmation → prediction → risk → result → restart. | 4 (Nisarg 6) | [WEEK_1.md](WEEK_1.md) |
| **Sprint 2: Feature Complete** | Wed 28 Oct → Tue 10 Nov | Image upload, accounts and history, self-care guidance, map referral, privacy controls, uncertainty escalation, full test suites. | 4 (Nisarg 7) | [WEEK_2.md](WEEK_2.md) |
| **Sprint 3: Hardening & Release** | Wed 11 Nov → Fri 20 Nov | No new features. Accuracy, safety, security, accessibility, performance, deployment, demo. | 3 (Nisarg 5) | [WEEK_3.md](WEEK_3.md) |

**Key dates**
- Staging deploys automatically on every merge to `develop`. Production deploys only after the leader merges to `main` **and approves the deployment**.
- **Tue 27 Oct:** Sprint 1 review. Leader merges `develop → main` and tags `v0.1.0`.
- **Tue 10 Nov:** Sprint 2 review. `develop → main`, tag `v0.2.0`. **Feature freeze.**
- **Tue 17 Nov:** Code freeze. Only bug fixes from this date.
- **Fri 20 Nov:** Final release `v1.0.0` and demo.

Every member gets **12 tasks** (1 + 4 + 4 + 3). Nisarg, as leader and AI/ML lead, takes **20** (2 + 6 + 7 + 5). Every task is **one issue, one branch and one PR**.

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

## 3. Teams and ownership codes

Stack and folder layout: [tech-stack.md](tech-stack.md).

### 3.1 Teams

| Team | Members | Share of the team's work |
|---|---|---|
| **AI / ML** | Nisarg (lead), Nishith, Kavya | Nisarg ≈ 60% (prediction, risk engine, CV model, vector retrieval). Nishith and Kavya split the rest equally (≈ 20% each). |
| **Backend** | Darshil, Harsh, Vivek, Mohit | Orchestration, API foundation, auth, security and privacy services, backend tests |
| **Database** | Nishith, Kavya, Dimple | Models, migrations, repositories, retention and deletion at the data layer |
| **Frontend + Deployment** | Rutva, Dimple, Mann | React PWA, Vercel, CI/CD, Docker, Render/VPS, monitoring |
| **Testing** | Mohit (lead), Rutva, Mann, Nisarg | Test infrastructure, integration/E2E/load tests, CD smoke tests, model and risk-engine verification |

### 3.2 Ownership codes

| Code | Member | Teams | Owns |
|---|---|---|---|
| NIS | Nisarg (leader) | AI/ML lead, Testing | `server/app/services/prediction/`, `server/app/services/image/` (CV analyzer, ONNX inference), `ml/prediction/`, `ml/cv/`, `ml/datasets/conditions/`, `ml/datasets/images/` |
| NIT | Nishith | AI/ML, Database | `server/app/services/ai/` (gateway, prompts, extraction); shared with the Database team: `server/app/{models,repositories,db}/`, `server/alembic/` |
| KAV | Kavya | AI/ML, Database | `server/app/services/knowledge/` (symptom normalization, glossary, self-care content), `ml/nlp_eval/`, `ml/datasets/symptoms/`; shared with the Database team: `server/app/{models,repositories,db}/`, `server/alembic/` |
| DAR | Darshil | Backend | `server/app/services/assessment/` (orchestration, state machine), `server/app/schemas/` (API contracts) |
| HAR | Harsh | Backend | `server/app/middleware/`, `server/app/services/privacy/` (consent, PII scrubbing, safety wording, export/deletion) |
| VIV | Vivek | Backend | `server/app/{main.py,api,core}`, `server/app/services/auth/`, `server/app/services/upload/` (image upload validation) |
| MOH | Mohit | Backend, Testing lead | `server/tests/integration/`, `server/tests/conftest.py`, `tests/e2e/` |
| RUT | Rutva | Frontend + Deployment, Testing | `client/` scaffold and config, `client/src/components/chat/`, `client/src/{stores,services}/`, `client/vite.config.ts`, `server/Dockerfile`, `render.yaml`, `deploy/`, CI/CD workflows (leader approves) |
| MAN | Mann | Frontend + Deployment, Testing | `client/src/pages/`, `client/src/components/{layout,assessment,result}/`, `client/src/i18n/` |
| DIM | Dimple | Frontend + Deployment, Database | `client/src/components/{consent,privacy,risk}/`, `client/vercel.json`; shared with the Database team: consent, retention and deletion code in `server/app/{models,repositories}/` |

**Shared database folders.** Nishith, Kavya and Dimple share `server/app/{models,repositories,db}/` and `server/alembic/`. Only one of them works on migrations at a time: say "starting a migration" in the team channel first, so two migrations never branch from the same head.

**Pages.** `client/src/pages/` belongs to Mann. A page that another member's task creates (landing, profile, privacy, history) is owned by that member, and Mann reviews it.

Task IDs look like `S1-DAR-2` (Sprint 1, Darshil, 2nd task). Do tasks **in the listed order** unless the leader says otherwise.
Unit tests for a module are written by its owner in the same PR (`server/tests/unit/<module>/`, or next to the component in `client/`).

---

## 4. Sprint 0: Setup & Contracts (10–13 Oct)

| ID | Owner | Task | Req. |
|---|---|---|---|
| S0-VIV-1 | Vivek | Scaffold `server/`: FastAPI app factory, pydantic-settings config, structlog JSON logging, central error handler, `GET /api/v1/health` returning `{status, version}` (version = `APP_VERSION`), `Dockerfile` + `.dockerignore` meeting the image contract in [deployment.md](deployment.md) §1 (Rutva reviews; she owns the Dockerfile after this), `docker-compose.yml` (services `db` = Postgres 16 and `api` = the server image, matching [commands.md](commands.md)), root `.env.example` with mock providers, `requirements.txt` + `requirements-dev.txt`, `pyproject.toml` (ruff, mypy, pytest). Enable pip in `dependabot.yml`. | NFR-08 |
| S0-RUT-1 | Rutva | Scaffold `client/`: Vite + React 18 + TS, Tailwind, React Router, Zustand, TanStack Query, `vite-plugin-pwa` (manifest, app-shell caching, API `NetworkOnly`), Vite dev proxy `/api → :8000`, Vitest + RTL + MSW, ESLint (+ `eslint-plugin-jsdoc`) + Prettier, `vercel.json` (SPA fallback, `/api` rewrite to staging, security headers, `git.deploymentEnabled` off for `main`/`develop`). Scripts: `lint`, `typecheck`, `test`, `build`. Enable npm in `dependabot.yml`. | NFR-08, NFR-09 |
| S0-DAR-1 | Darshil | API contracts as Pydantic models in `server/app/schemas/`: `AssessmentState`, `Symptom`, `Message`, `Condition`, `ConfidenceLabel`, `RiskLevel`, `AssessmentResult`. Contract doc `docs/api-contract.md` with example JSON for every endpoint. | — |
| S0-HAR-1 | Harsh | *(In review, PR #10.)* SQLAlchemy 2.0 models (`User`, `Assessment`, `Message`, `Symptom`, `Consent`), DB session, Alembic init + first migration, seed script, ER diagram in `docs/database.md`. With the leader: Neon project with `staging` and `main` branches. | FR-01 |
| S0-NIT-1 | Nishith | `AiGateway` protocol + `MockAiProvider` (`AI_PROVIDER=mock`) returning fixture extractions; prompt folder `server/app/services/ai/prompts/` with versioned files. | — |
| S0-KAV-1 | Kavya | Canonical symptom vocabulary v0 in `ml/datasets/symptoms/` (symptom ID, display name, body system), covering every symptom used by the condition dataset (S0-NIS-1). NLP eval case format + first 20 cases in `ml/nlp_eval/cases.json`. | FR-03 |
| S0-NIS-1 | Nisarg | Condition dataset v0 in `ml/datasets/conditions/`: ~30 common conditions with ICD-10 code, key symptoms, specialty, and a red-flag symptom list (JSON). Sources documented. | DR-03, DR-04 |
| S0-NIS-2 | Nisarg | `docs/cv-plan.md`: target classes (common visible skin conditions + `unclear`), dataset choice and licences (SCIN, Fitzpatrick17k, DermNet), split strategy balanced by skin tone, metrics, model choice, ONNX size/latency budget. `ml/cv/` scaffold: `requirements.txt`, config YAML, `train.py` skeleton, Kaggle notebook link. | NFR-07 |
| S0-MAN-1 | Mann | UX foundation: wireframes of every screen in `docs/ux/`, design tokens (Tailwind theme), PWA icons and splash images (192, 512, maskable), `AppLayout` with persistent disclaimer footer (after S0-RUT-1 merges). | DR-01, NFR-06 |
| S0-MOH-1 | Mohit | `docs/TEST_PLAN.md` (levels, tools, 70% coverage target), `server/tests/conftest.py` (test DB, mock providers, HTTP client fixture), Playwright scaffold in `tests/e2e/`. | NFR-07 |
| S0-DIM-1 | Dimple | `docs/privacy-and-safety.md`: data inventory, DPDP Act 2023 checklist, final disclaimer and consent wording, banned-phrases list ("you have", "diagnosis", "take X mg"…), PWA storage rules (no health data in cache/localStorage). | DR-01, DR-05, DR-06, DR-08 |

**Sprint 0 exit:** `develop` is green in CI, both apps run locally, contracts are merged, and the staging backend health check is live.

---

## 5. Sprint 1: Walking Skeleton (14–27 Oct)

| ID | Owner | Task | Req. |
|---|---|---|---|
| **AI / ML** | | | |
| S1-NIS-1 | Nisarg | Baseline condition predictor: weighted symptom-overlap scoring over the dataset, returning the top 3, with confidence mapped to "Likely / Possible / Less likely" (never raw percentages to the user). | FR-05, FR-22, FR-23 |
| S1-NIS-2 | Nisarg | Deterministic risk engine: SELF_CARE / CONSULT_DOCTOR / URGENT, with red-flag override. | FR-06, FR-15, DR-02 |
| S1-NIS-3 | Nisarg | Specialty mapper + `ResultComposer` that builds the final `AssessmentResult`. | FR-07, DR-04 |
| S1-NIS-4 | Nisarg | `ImageAnalyzer` protocol + `MockImageAnalyzer` (`CV_PROVIDER=mock`) wired to the orchestrator contract. | — |
| S1-NIS-5 | Nisarg | CV dataset pipeline in `ml/datasets/images/`: download scripts, cleaning, label mapping, train/val/test split balanced by skin tone, dataset card. | NFR-07 |
| S1-NIS-6 | Nisarg | Baseline CV model: transfer learning (EfficientNet-B0 or MobileNetV3 via `timm`) on Kaggle GPU, W&B tracking, first metrics report. | NFR-07 |
| S1-NIT-1 | Nishith | Extraction prompt v1 + Pydantic output schema (symptom, severity, duration, onset, body site). | FR-03, FR-17 |
| S1-NIT-2 | Nishith | Missing-information detection + clarification question generation (max 3). | FR-04, FR-19, FR-20 |
| S1-NIT-3 | Nishith | Real OpenAI provider: structured JSON output, timeout, 2 retries, typed `AiError` on failure. | NFR-05 |
| S1-KAV-1 | Kavya | Symptom normalization in `services/knowledge/`: map lay terms to canonical symptom IDs ("tummy ache" → abdominal pain). Deterministic lookup first. | FR-03 |
| S1-KAV-2 | Kavya | NLP eval harness v1 (`ml/nlp_eval/evaluate.py`), 50 cases, precision/recall/F1 report. | NFR-07 |
| S1-KAV-3 | Kavya | Curated symptom glossary v0 (plain-language definitions, reviewed by Dimple for safe wording) + lookup function. | FR-18 |
| **Database** | | | |
| S1-NIT-4 | Nishith | Repository layer: `assessment_repository.py`, `message_repository.py`, `symptom_repository.py` (typed CRUD; symptoms as structured JSONB with severity, duration, body site). | FR-17 |
| S1-KAV-4 | Kavya | Guest sessions: anonymous session token model, assessment ownership by session. | idea §10 |
| S1-DIM-4 | Dimple | Indexes for hot queries, migration review, realistic demo seed data, migrations verified on Neon staging. | NFR-01 |
| **Backend** | | | |
| S1-DAR-1 | Darshil | Assessment state machine: `START → SYMPTOM_COLLECTION → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`, with guarded transitions and unit tests. | — |
| S1-DAR-2 | Darshil | `process_message()`: store message → AI extraction → merge symptoms → decide next state. | FR-03, FR-17 |
| S1-DAR-3 | Darshil | Clarification loop capped at 3 turns. After the cap, move to confirmation and flag low confidence. | FR-04, FR-19, FR-20 |
| S1-DAR-4 | Darshil | `confirm_symptoms()` (add / remove / edit) and `restart_assessment()`. | FR-16, FR-21, FR-25 |
| S1-VIV-1 | Vivek | Routers for all assessment endpoints with stub responses (`POST /assessments`, `POST /assessments/{id}/messages`, `PUT /assessments/{id}/symptoms`, `POST /assessments/{id}/confirm`, `GET /assessments/{id}/result`). OpenAPI export script (Rutva adds `npm run gen:api` and the CI freshness check). | — |
| S1-VIV-2 | Vivek | Error model (`AppError` → JSON error body with code), request-ID middleware, access logging. | NFR-05, NFR-10 |
| S1-VIV-3 | Vivek | Replace stubs: routers → services through FastAPI `Depends` (dependency injection). | — |
| S1-VIV-4 | Vivek | `POST /assessments/{id}/images`: `UploadFile`, 5 MB limit, MIME + magic-byte check, EXIF stripped, processed **in memory only** (never written to disk). | idea §3, DR-06 |
| S1-HAR-1 | Harsh | Security-headers middleware, CORS settings, `slowapi` rate limits on assessment and auth routes. | NFR-03 |
| S1-HAR-2 | Harsh | PII scrubber applied to user text before it reaches the LLM (names, phones, emails, IDs). | NFR-04, DR-06 |
| S1-HAR-3 | Harsh | Safety-wording guard: unit-tested `assert_safe_wording()` used by `ResultComposer` to block banned phrases. | DR-05 |
| S1-HAR-4 | Harsh | Consent service + `POST /consents` with stored consent version (UI by Dimple in S1-DIM-1). | DR-08 |
| **Testing** | | | |
| S1-MOH-1 | Mohit | Unit tests for the state machine (every valid and invalid transition). | — |
| S1-MOH-2 | Mohit | Integration tests (pytest + httpx) for the full assessment API flow with mock providers. | — |
| S1-MOH-3 | Mohit | Contract tests: every endpoint's responses match the published Pydantic schemas / OpenAPI. | — |
| S1-MOH-4 | Mohit | Playwright E2E happy path against the local stack: start → describe → clarify → confirm → result → restart. | — |
| **Frontend + Deployment** | | | |
| S1-RUT-1 | Rutva | Chat UI: `ChatContainer`, `MessageBubble`, `MessageInput`, auto-scroll, `aria-live`. | idea §1, §2 |
| S1-RUT-2 | Rutva | `assessmentStore` + API services using the generated OpenAPI types (`npm run gen:api`), with MSW mocks until S1-VIV-3 merges. | — |
| S1-RUT-3 | Rutva | Typing indicator, loading/error/retry states, offline banner with emergency number 112. | NFR-05 |
| S1-RUT-4 | Rutva | CD live end-to-end: GHCR package access, Render services from `render.yaml` (or a VPS per `deploy/vps/`), Vercel project, GitHub environments filled; a merge to `develop` deploys staging automatically. | NFR-05 |
| S1-MAN-1 | Mann | `SymptomConfirmationCard`: list, edit, remove, add from a selectable list. | FR-16, FR-21, FR-03 |
| S1-MAN-2 | Mann | `ConditionList` with confidence badges and a short "why" line. | FR-22, FR-23 |
| S1-MAN-3 | Mann | Result page: composes `ConditionList`, `RiskBadge`, guidance slot and the disclaimer. | DR-01 |
| S1-MAN-4 | Mann | "Start new assessment" button, always visible, with confirm dialog. | FR-25 |
| S1-DIM-1 | Dimple | Consent step UI before anything is saved (calls `POST /consents`). | DR-08 |
| S1-DIM-2 | Dimple | Landing page + start flow + disclaimer shown before the first message. | DR-01 |
| S1-DIM-3 | Dimple | `RiskBadge` + full-screen urgent-care alert for URGENT results, with the emergency number (112) shown first. | FR-06, FR-15, DR-02 |

**Sprint 1 exit (demo on staging):** "I have fever and headache since yesterday" runs through the deployed app to a result with 2–3 conditions, a risk level and a disclaimer. Then restart. The PWA installs on a phone.

---

## 6. Sprint 2: Feature Complete (28 Oct – 10 Nov)

| ID | Owner | Task | Req. |
|---|---|---|---|
| **AI / ML** | | | |
| S2-NIS-1 | Nisarg | Uncertainty escalation (low confidence always raises the risk tier, never lowers it) + risk-engine test matrix: every red flag, 100% branch coverage. | idea §7, NFR-07, DR-02 |
| S2-NIS-2 | Nisarg | Contributing-factor explanations ("because you reported X and Y"). | FR-24 |
| S2-NIS-3 | Nisarg | Condition model v2: scikit-learn model trained in `ml/prediction/`, exported to ONNX (`skl2onnx`), served with ONNX Runtime, compared with the baseline and documented. | FR-05, NFR-07 |
| S2-NIS-4 | Nisarg | CV model v2: augmentation, class balancing, tuning; per-class and per-skin-tone metrics. | NFR-07 |
| S2-NIS-5 | Nisarg | Export CV model to ONNX + INT8 quantization + parity test (PyTorch vs ONNX); publish to Hugging Face Hub with a model card. | NFR-01, NFR-08 |
| S2-NIS-6 | Nisarg | `OnnxImageAnalyzer` in the server: load the pinned model revision, identical preprocessing, map labels to visual symptoms; image quality checks (blur, darkness, size) + `unclear` abstain threshold with friendly messages. | idea §3, NFR-05, NFR-07 |
| S2-NIS-7 | Nisarg | **Vector retrieval, only if required.** Decide from the S1 eval results: if deterministic normalization (S1-KAV-1) and glossary lookup miss too many eval cases, add semantic matching with `pgvector` on the existing Neon database and a small ONNX sentence-embedding model (no new service, no LLM in the risk path). Otherwise record the "not needed" decision in `docs/`. The migration goes through the Database team (S2-NIT-4). | FR-03, FR-18 |
| S2-NIT-1 | Nishith | Prompt v2: multi-turn context (answers to clarifying questions update the right symptom) + fixes driven by eval results. Target ≥ 85% extraction F1. | FR-19, NFR-07 |
| S2-NIT-2 | Nishith | Intent handling: prompt-injection defence, polite refusal of off-topic chat, and "what is nausea?" questions answered from the curated glossary (S1-KAV-3), not free LLM text. | idea "out of scope", FR-18 |
| S2-KAV-1 | Kavya | Self-care guidance content per condition (general advice only, reviewed by Dimple), served from `services/knowledge/`. | idea §8, DR-05 |
| S2-KAV-2 | Kavya | Eval set v2: 100 cases including Hinglish and misspelled input, per-field metrics, report that feeds S2-NIT-1. | NFR-07 |
| **Database** | | | |
| S2-NIT-3 | Nishith | Audit-log table + repository (who, when, engine/model versions). | NFR-10 |
| S2-NIT-4 | Nishith | History-query indexes + migration review on Neon staging; `pgvector` extension and embeddings table if S2-NIS-7 goes ahead. | NFR-01 |
| S2-KAV-3 | Kavya | Profile model: age band, sex, chronic conditions (all optional). | FR-02 |
| S2-KAV-4 | Kavya | History queries + pagination + ownership filters. | FR-02 |
| S2-DIM-4 | Dimple | Guest data TTL purge (e.g. 24 h) + cascading account deletion at the data layer. | DR-06 |
| **Backend** | | | |
| S2-DAR-1 | Darshil | Claim a guest assessment into a new account after sign-up. | idea §10 |
| S2-DAR-2 | Darshil | Merge image findings into assessment state. | idea §3 |
| S2-DAR-3 | Darshil | Pass profile context (age, chronic conditions) into analysis, as in the activity diagram. | FR-02 |
| S2-DAR-4 | Darshil | Idempotent message processing + transactions (no double answers on retry). | NFR-05 |
| S2-VIV-1 | Vivek | Auth: register, login, logout; argon2 hashing; JWT in an HttpOnly, Secure, SameSite=Lax cookie (same-origin through the Vercel proxy). | FR-01 |
| S2-VIV-2 | Vivek | JWT expiry/refresh, secure cookie flags, CSRF protection. | NFR-03 |
| S2-VIV-3 | Vivek | Profile endpoints (read / update the optional profile). | FR-02 |
| S2-VIV-4 | Vivek | Audit log of every analysis and recommendation (uses S2-NIT-3). | NFR-10 |
| S2-HAR-1 | Harsh | History endpoints: list and view past assessments (paginated). | FR-02 |
| S2-HAR-2 | Harsh | "Delete my data" and "Export my data" endpoints. | DR-06, NFR-04 |
| S2-HAR-3 | Harsh | Consent versioning: re-ask when the policy version changes. | DR-08 |
| S2-HAR-4 | Harsh | Scheduled guest-data purge job (calls the S2-DIM-4 purge). | DR-06 |
| **Testing** | | | |
| S2-MOH-1 | Mohit | Auth, privacy and deletion integration tests. | NFR-03, NFR-04 |
| S2-MOH-2 | Mohit | Image upload API tests: size, MIME, magic bytes, never written to disk. | DR-06 |
| S2-MOH-3 | Mohit | Safety integration tests: urgent path, disclaimer present, no raw percentages in any response. | DR-01, DR-02, FR-23 |
| S2-MOH-4 | Mohit | Coverage gate (70%) in CI for server (pytest-cov) and client (Vitest) + reports as artifacts. | NFR-08 |
| **Frontend + Deployment** | | | |
| S2-RUT-1 | Rutva | Login / register UI + `authStore`. | FR-01 |
| S2-RUT-2 | Rutva | History page (list + detail). | FR-02 |
| S2-RUT-3 | Rutva | PWA polish: install prompt, "update available" toast, offline fallback page, resume an unfinished assessment after refresh (ID only in `sessionStorage`). | NFR-05, NFR-09 |
| S2-RUT-4 | Rutva | Post-deploy Playwright smoke test against staging in CD + rollback runbook (`docs/runbook.md`). | NFR-05 |
| S2-MAN-1 | Mann | Image attach in chat (camera capture on mobile), offered only when visual symptoms are detected. | idea §3 |
| S2-MAN-2 | Mann | Doctor referral: "Find a <specialty> near me" opens an external map search. No doctor data stored. | FR-08*, idea §9 |
| S2-MAN-3 | Mann | Symptom-definition tooltips + "why this result" explanation panel. | FR-18, FR-24 |
| S2-MAN-4 | Mann | Frontend component tests for chat, confirmation and results. | — |
| S2-DIM-1 | Dimple | Profile page (optional fields, clear "why we ask"). | FR-02 |
| S2-DIM-2 | Dimple | Self-care guidance cards for low-risk results. | idea §8 |
| S2-DIM-3 | Dimple | "Delete my data" / "Export my data" UI + privacy policy page + consent re-ask screen. | DR-06, DR-08 |

**Sprint 2 exit:** every in-scope feature works on staging, including real CV inference. Feature freeze.

---

## 7. Sprint 3: Hardening & Release (11–20 Nov)

| ID | Owner | Task | Req. |
|---|---|---|---|
| **AI / ML** | | | |
| S3-NIS-1 | Nisarg | Final model evaluation report: condition model (accuracy, confusion matrix, red-flag recall) and CV model (fairness across skin tones; irrelevant, blurry and edge images). | NFR-07 |
| S3-NIS-2 | Nisarg | Risk-consistency verification (same input → same output, 1000 runs). | DR-02 |
| S3-NIS-3 | Nisarg | Model cards for the condition and CV models (data, method, limits, intended use) in `docs/`. | NFR-08 |
| S3-NIS-4 | Nisarg | CV inference performance on the production CPU (Render free tier or VPS): ≤ 1 s per image, total RAM < 512 MB. | NFR-01 |
| S3-NIS-5 | Nisarg | Release `v1.0.0`: changelog, release notes, final README, demo script. | NFR-08 |
| S3-NIT-1 | Nishith | Fallback provider (Gemini) + latency budget + AI documentation (prompts, limitations, failure modes). | NFR-05, NFR-08 |
| S3-KAV-1 | Kavya | Full AI regression run (extraction, normalization, glossary) + fixes. | NFR-07 |
| **Database** | | | |
| S3-NIT-2 | Nishith | Query performance review (`EXPLAIN ANALYZE`) + index fixes. | NFR-01 |
| S3-NIT-3 | Nishith | Backup and restore procedure on Neon, tested once. | NFR-05 |
| S3-KAV-2 | Kavya | Data-integrity tests + final database documentation. | NFR-08 |
| S3-KAV-3 | Kavya | Migration safety review: every migration backward-compatible, rollback tested on staging. | NFR-05 |
| **Backend** | | | |
| S3-DAR-1 | Darshil | API contract freeze + authorization audit (no cross-user access). | NFR-03 |
| S3-DAR-2 | Darshil | Input validation audit on every endpoint. | NFR-03 |
| S3-DAR-3 | Darshil | Performance: p95 result time ≤ 5 s on staging. | NFR-01 |
| S3-VIV-1 | Vivek | OWASP Top 10 review + fixes. | NFR-03 |
| S3-VIV-2 | Vivek | Graceful-degradation audit: AI, CV and DB failures return safe, typed errors. | NFR-05 |
| S3-VIV-3 | Vivek | Final OpenAPI documentation: summaries, examples and error codes for every endpoint. | NFR-08 |
| S3-HAR-1 | Harsh | Rate-limit tuning + security-header verification on staging. | NFR-03 |
| S3-HAR-2 | Harsh | Retention and deletion verified end to end on staging + DPDP compliance document and final data inventory. | NFR-04, DR-06 |
| S3-HAR-3 | Harsh | Logging and audit-log review: no personal data or message text in logs. | NFR-10 |
| **Testing** | | | |
| S3-MOH-1 | Mohit | Load test (Locust or Artillery) against staging. | NFR-02 |
| S3-MOH-2 | Mohit | Authorization and abuse tests across all endpoints (cross-user access, oversized input). | NFR-03 |
| S3-MOH-3 | Mohit | Bug triage + release QA sign-off report. | — |
| **Frontend + Deployment** | | | |
| S3-RUT-1 | Rutva | First production release through CD (leader-approved), Sentry for the server, UptimeRobot on the health endpoint. | NFR-05 |
| S3-RUT-2 | Rutva | Full regression + E2E matrix (browsers × devices, installed PWA). | NFR-09 |
| S3-RUT-3 | Rutva | Lighthouse ≥ 90 for PWA, performance and accessibility; code splitting. | NFR-01, NFR-06 |
| S3-MAN-1 | Mann | Responsive/mobile pass for all screens + final visual polish, tested as an installed PWA on Android and iOS. | NFR-09 |
| S3-MAN-2 | Mann | i18n with react-i18next + Hindi translation of the UI. | NFR-06 |
| S3-MAN-3 | Mann | Rollback drill on staging (backend target + Vercel) + demo-day plan (paid instance, VPS, or warm-up). | NFR-05 |
| S3-DIM-1 | Dimple | WCAG 2.1 AA audit + usability test with 5 users + top fixes. | NFR-06 |
| S3-DIM-2 | Dimple | Final safety and disclaimer audit of every user-facing string. | DR-01, DR-05 |
| S3-DIM-3 | Dimple | Sentry for the client + Vercel production config check (headers, CSP, SPA fallback, `/api` rewrite). | NFR-03, NFR-05 |

---

## 8. Workload and commit balance

| Member | S0 | S1 | S2 | S3 | Total |
|---|---|---|---|---|---|
| Nisarg | 2 | 6 | 7 | 5 | **20** |
| Nishith, Kavya | 1 | 4 | 4 | 3 | 12 each (≈ 7 AI/ML + 5 Database) |
| Everyone else | 1 | 4 | 4 | 3 | 12 each |

- **Load:** everyone has 12 tasks of similar size; the leader takes 20. AI/ML work splits roughly Nisarg 60%, Nishith 20%, Kavya 20%. If a task turns out much bigger, the leader splits it and moves part to the next sprint.
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
6. The change works on **staging** after the automatic deploy (check it there, not only locally).
