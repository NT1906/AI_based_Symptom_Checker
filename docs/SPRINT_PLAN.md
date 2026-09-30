# Sprint Plan — AI-Based Symptom Checker (Group 14)

**Timeline:** Saturday 10 October 2026 → Friday 20 November 2026 (6 weeks). Dates may shift slightly. The leader updates this file and the GitHub milestones together.
**Team:** 10 members, each owning one module (see [rules.md](rules.md)).
**Scope source of truth:** [idea.md](idea.md). **Stack:** [tech-stack.md](tech-stack.md) (React PWA on Vercel, FastAPI on Render, CV models trained in `ml/`). Requirement IDs (FR / NFR / DR) come from the Lab 6 report, `Group_14_project_report.pdf`.

---

## 1. Sprint calendar

| Sprint | Dates | Goal | Tasks per member | Maps to |
|---|---|---|---|---|
| **Sprint 0: Setup & Contracts** | Sat 10 Oct → Tue 13 Oct | Everyone can run the project locally. Shared types, API contract, DB schema and mocks are merged, so nobody is blocked in Sprint 1. | 1 | — |
| **Sprint 1: Walking Skeleton** | Wed 14 Oct → Tue 27 Oct | End-to-end flow works for real: chat → extraction → clarification → confirmation → prediction → risk → result → restart. | 4 | [WEEK_1.md](WEEK_1.md) |
| **Sprint 2: Feature Complete** | Wed 28 Oct → Tue 10 Nov | Image upload, accounts and history, self-care guidance, map referral, privacy controls, uncertainty escalation, full test suites. | 4 | [WEEK_2.md](WEEK_2.md) |
| **Sprint 3: Hardening & Release** | Wed 11 Nov → Fri 20 Nov | No new features. Accuracy, safety, security, accessibility, performance, deployment, demo. | 3 | [WEEK_3.md](WEEK_3.md) |

**Key dates**
- Staging deploys automatically on every merge to `develop`. Production deploys only after the leader merges to `main` **and approves the deployment**.
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

Stack and folder layout: [tech-stack.md](tech-stack.md).

| Code | Member | Module |
|---|---|---|
| NIS | Nisarg (leader) | Prediction, risk engine, result composer: `server/app/services/prediction/`, `ml/prediction/`, `ml/datasets/conditions/` |
| RUT | Rutva | FastAPI foundation, routers, config, Docker, CI/CD, deployment: `server/app/{main.py,api,core}`, `server/Dockerfile`, `render.yaml` |
| HAR | Harsh | Database: `server/app/{models,repositories,db}/`, `server/alembic/` |
| KAV | Kavya | Assessment orchestration, state machine, API contracts: `server/app/services/assessment/`, `server/app/schemas/` |
| NIT | Nishith | AI gateway, prompts, extraction: `server/app/services/ai/` |
| VIV | Vivek | Chat UI, client state, API client, PWA: `client/src/components/chat/`, `client/src/{stores,services}/`, `client/vite.config.ts`, `client/vercel.json` |
| DAR | Darshil | App shell, confirmation, results, referral UI: `client/src/pages/`, `client/src/components/{layout,assessment,result,common}/` |
| MAN | Mann | Image upload, CV training and serving: `server/app/services/image/`, `ml/cv/`, `ml/datasets/images/` |
| MOH | Mohit | Test infrastructure, integration/E2E, NLP evaluation: `server/tests/integration/`, `server/tests/conftest.py`, `tests/e2e/`, `ml/nlp_eval/` |
| DIM | Dimple | Security, privacy, consent, safety: `server/app/middleware/`, `server/app/services/privacy/`, `client/src/components/consent/` |

Task IDs look like `S1-KAV-2` (Sprint 1, Kavya, 2nd task). Do tasks **in the listed order** unless the leader says otherwise.
Unit tests for a module are written by its owner in the same PR (`server/tests/unit/<module>/`, or next to the component in `client/`).

---

## 4. Sprint 0: Setup & Contracts (10–13 Oct)

| ID | Task | Req. |
|---|---|---|
| S0-RUT-1 | Scaffold `server/`: FastAPI app factory, pydantic-settings config, structlog JSON logging, central error handler, `GET /api/v1/health` returning `{status, version}` (version = `RENDER_GIT_COMMIT`), `Dockerfile` (python:3.12-slim, non-root user, `alembic upgrade head && uvicorn`), `docker-compose.yml` (Postgres 16), `requirements.txt` + `requirements-dev.txt`, `pyproject.toml` (ruff, mypy, pytest), `.env.example`. Enable pip in `dependabot.yml`. | NFR-08 |
| S0-VIV-1 | Scaffold `client/`: Vite + React 18 + TS, Tailwind, React Router, Zustand, TanStack Query, `vite-plugin-pwa` (manifest, app-shell caching, API `NetworkOnly`), Vite dev proxy `/api → :8000`, Vitest + RTL + MSW, ESLint (+ `eslint-plugin-jsdoc`) + Prettier, `vercel.json` (SPA fallback, `/api` rewrite to staging, security headers, `git.deploymentEnabled` off for `main`/`develop`). Scripts: `lint`, `typecheck`, `test`, `build`. Enable npm in `dependabot.yml`. | NFR-08, NFR-09 |
| S0-KAV-1 | API contracts as Pydantic models in `server/app/schemas/`: `AssessmentState`, `Symptom`, `Message`, `Condition`, `ConfidenceLabel`, `RiskLevel`, `AssessmentResult`. Contract doc `docs/api-contract.md` with example JSON for every endpoint. | — |
| S0-HAR-1 | SQLAlchemy 2.0 models (`User`, `Assessment`, `Message`, `Symptom`, `Consent`), DB session, Alembic init + first migration, seed script, ER diagram in `docs/database.md`. With the leader: Neon project with `staging` and `main` branches. | FR-01 |
| S0-NIT-1 | `AiGateway` protocol + `MockAiProvider` (`AI_PROVIDER=mock`) returning fixture extractions; prompt folder `server/app/services/ai/prompts/` with versioned files. | — |
| S0-NIS-1 | Condition dataset v0 in `ml/datasets/conditions/`: ~30 common conditions with ICD-10 code, key symptoms, specialty, and a red-flag symptom list (JSON). Sources documented. | DR-03, DR-04 |
| S0-DAR-1 | UX foundation: wireframes of every screen in `docs/ux/`, design tokens (Tailwind theme), PWA icons and splash images (192, 512, maskable), `AppLayout` with persistent disclaimer footer (after S0-VIV-1 merges). | DR-01, NFR-06 |
| S0-MAN-1 | `docs/cv-plan.md`: target classes (common visible skin conditions + `unclear`), dataset choice and licences (SCIN, Fitzpatrick17k, DermNet), split strategy balanced by skin tone, metrics, model choice, ONNX size/latency budget. `ml/cv/` scaffold: `requirements.txt`, config YAML, `train.py` skeleton, Kaggle notebook link. | NFR-07 |
| S0-MOH-1 | `docs/TEST_PLAN.md` (levels, tools, 70% coverage target), `server/tests/conftest.py` (test DB, mock providers, HTTP client fixture), Playwright scaffold in `tests/e2e/`, NLP eval case format + first 20 cases in `ml/nlp_eval/cases.json`. | NFR-07 |
| S0-DIM-1 | `docs/privacy-and-safety.md`: data inventory, DPDP Act 2023 checklist, final disclaimer and consent wording, banned-phrases list ("you have", "diagnosis", "take X mg"…), PWA storage rules (no health data in cache/localStorage). | DR-01, DR-05, DR-06, DR-08 |

**Sprint 0 exit:** `develop` is green in CI, both apps run locally, contracts are merged, and the staging backend health check is live.

---

## 5. Sprint 1: Walking Skeleton (14–27 Oct)

| ID | Task | Req. |
|---|---|---|
| S1-RUT-1 | Routers for all assessment endpoints with stub responses (`POST /assessments`, `POST /assessments/{id}/messages`, `PUT /assessments/{id}/symptoms`, `POST /assessments/{id}/confirm`, `GET /assessments/{id}/result`). OpenAPI export script + `npm run gen:api` in client + CI check that generated types are up to date. | — |
| S1-RUT-2 | Error model (`AppError` → JSON error body with code), request-ID middleware, access logging. | NFR-05, NFR-10 |
| S1-RUT-3 | Replace stubs: routers → services through FastAPI `Depends` (dependency injection). | — |
| S1-RUT-4 | CD live end-to-end: Render services from `render.yaml`, Vercel project, GitHub environments/variables filled; a merge to `develop` deploys staging automatically. | NFR-05 |
| S1-HAR-1 | Repository layer: `assessment_repository.py`, `message_repository.py` (typed CRUD). | — |
| S1-HAR-2 | Symptom persistence with structured JSONB (severity, duration, body site) + `symptom_repository.py`. | FR-17 |
| S1-HAR-3 | Guest sessions: anonymous session token model, assessment ownership by session. | idea §10 |
| S1-HAR-4 | Indexes for hot queries, migration review, realistic demo seed data, migrations verified on Neon staging. | NFR-01 |
| S1-KAV-1 | Assessment state machine: `START → SYMPTOM_COLLECTION → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`, with guarded transitions and unit tests. | — |
| S1-KAV-2 | `process_message()`: store message → AI extraction → merge symptoms → decide next state. | FR-03, FR-17 |
| S1-KAV-3 | Clarification loop capped at 3 turns. After the cap, move to confirmation and flag low confidence. | FR-04, FR-19, FR-20 |
| S1-KAV-4 | `confirm_symptoms()` (add / remove / edit) and `restart_assessment()`. | FR-16, FR-21, FR-25 |
| S1-NIT-1 | Extraction prompt v1 + Pydantic output schema (symptom, severity, duration, onset, body site). | FR-03, FR-17 |
| S1-NIT-2 | Symptom normalization: map lay terms to canonical names ("tummy ache" → abdominal pain). | FR-03 |
| S1-NIT-3 | Missing-information detection + clarification question generation (max 3). | FR-04, FR-19, FR-20 |
| S1-NIT-4 | Real OpenAI provider: structured JSON output, timeout, 2 retries, typed `AiError` on failure. | NFR-05 |
| S1-NIS-1 | Baseline condition predictor: weighted symptom-overlap scoring over the dataset, returning the top 3. | FR-05, FR-22 |
| S1-NIS-2 | Confidence mapping to "Likely / Possible / Less likely" (never raw percentages to the user). | FR-23 |
| S1-NIS-3 | Deterministic risk engine: SELF_CARE / CONSULT_DOCTOR / URGENT, with red-flag override. | FR-06, FR-15, DR-02 |
| S1-NIS-4 | Specialty mapper + `ResultComposer` that builds the final `AssessmentResult`. | FR-07, DR-04 |
| S1-VIV-1 | Chat UI: `ChatContainer`, `MessageBubble`, `MessageInput`, auto-scroll, `aria-live`. | idea §1, §2 |
| S1-VIV-2 | `assessmentStore` + API services using the generated OpenAPI types, with MSW mocks until S1-RUT-3 merges. | — |
| S1-VIV-3 | Typing indicator, loading/error/retry states, offline banner with emergency number 112. | NFR-05 |
| S1-VIV-4 | "Start new assessment" button, always visible, with confirm dialog. | FR-25 |
| S1-DAR-1 | Landing page + start flow + disclaimer shown before the first message. | DR-01 |
| S1-DAR-2 | `SymptomConfirmationCard`: list, edit, remove, add from a selectable list. | FR-16, FR-21, FR-03 |
| S1-DAR-3 | `ConditionList` with confidence badges and a short "why" line. | FR-22, FR-23 |
| S1-DAR-4 | `RiskBadge` + full-screen urgent-care alert for URGENT results. | FR-06, FR-15 |
| S1-MAN-1 | `POST /assessments/{id}/images`: `UploadFile`, 5 MB limit, MIME + magic-byte check, EXIF stripped, processed **in memory only** (never written to disk). | idea §3, DR-06 |
| S1-MAN-2 | Dataset pipeline in `ml/datasets/images/`: download scripts, cleaning, label mapping, train/val/test split balanced by skin tone, dataset card. | NFR-07 |
| S1-MAN-3 | Baseline CV model: transfer learning (EfficientNet-B0 or MobileNetV3 via `timm`) on Kaggle GPU, W&B tracking, first metrics report. | NFR-07 |
| S1-MAN-4 | `ImageAnalyzer` protocol + `MockImageAnalyzer` (`CV_PROVIDER=mock`) wired to the orchestrator contract. | — |
| S1-MOH-1 | Unit tests for the state machine (every valid and invalid transition). | — |
| S1-MOH-2 | Integration tests (pytest + httpx) for the full assessment API flow with mock providers. | — |
| S1-MOH-3 | NLP eval harness v1 (`ml/nlp_eval/evaluate.py`), 50 cases, precision/recall/F1 report. | NFR-07 |
| S1-MOH-4 | Playwright E2E happy path against the local stack: start → describe → clarify → confirm → result → restart. | — |
| S1-DIM-1 | Consent step (UI + `POST /consents` + stored consent version) before anything is saved. | DR-08 |
| S1-DIM-2 | Security-headers middleware, CORS settings, `slowapi` rate limits on assessment and auth routes. | NFR-03 |
| S1-DIM-3 | PII scrubber applied to user text before it reaches the LLM (names, phones, emails, IDs). | NFR-04, DR-06 |
| S1-DIM-4 | Safety-wording guard: unit-tested `assert_safe_wording()` used by `ResultComposer` to block banned phrases. | DR-05 |

**Sprint 1 exit (demo on staging):** "I have fever and headache since yesterday" runs through the deployed app to a result with 2–3 conditions, a risk level and a disclaimer. Then restart. The PWA installs on a phone.

---

## 6. Sprint 2: Feature Complete (28 Oct – 10 Nov)

| ID | Task | Req. |
|---|---|---|
| S2-RUT-1 | Auth: register, login, logout; argon2 hashing; JWT in an HttpOnly, Secure, SameSite=Lax cookie (same-origin through the Vercel proxy). | FR-01 |
| S2-RUT-2 | History endpoints: list and view past assessments (paginated). | FR-02 |
| S2-RUT-3 | Post-deploy Playwright smoke test against staging in CD + rollback runbook (`docs/runbook.md`). | NFR-05 |
| S2-RUT-4 | Audit log of every analysis and recommendation (who, when, engine/model versions). | NFR-10 |
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
| S2-NIT-4 | Prompt v2 driven by eval results. Target ≥ 85% extraction F1. | NFR-07 |
| S2-NIS-1 | Uncertainty escalation: low confidence always raises the risk tier, never lowers it. | idea §7, NFR-07 |
| S2-NIS-2 | Contributing-factor explanations ("because you reported X and Y"). | FR-24 |
| S2-NIS-3 | Self-care guidance content per condition (general advice only, reviewed by Dimple). | idea §8, DR-05 |
| S2-NIS-4 | Condition model v2: scikit-learn model trained in `ml/prediction/`, exported to ONNX (`skl2onnx`), served with ONNX Runtime, compared with the baseline and documented. | FR-05, NFR-07 |
| S2-VIV-1 | Image attach in chat (camera capture on mobile), offered only when visual symptoms are detected. | idea §3 |
| S2-VIV-2 | Login / register UI + `authStore`. | FR-01 |
| S2-VIV-3 | History page (list + detail). | FR-02 |
| S2-VIV-4 | PWA polish: install prompt, "update available" toast, offline fallback page, resume an unfinished assessment after refresh (ID only in `sessionStorage`). | NFR-05, NFR-09 |
| S2-DAR-1 | Doctor referral: "Find a <specialty> near me" opens an external map search. No doctor data stored. | FR-08*, idea §9 |
| S2-DAR-2 | Self-care guidance cards for low-risk results. | idea §8 |
| S2-DAR-3 | Profile page (optional fields, clear "why we ask"). | FR-02 |
| S2-DAR-4 | Symptom-definition tooltips + "why this result" explanation panel. | FR-18, FR-24 |
| S2-MAN-1 | CV model v2: augmentation, class balancing, tuning; per-class and per-skin-tone metrics. | NFR-07 |
| S2-MAN-2 | Export to ONNX + INT8 quantization + parity test (PyTorch vs ONNX); publish to Hugging Face Hub with a model card. | NFR-01, NFR-08 |
| S2-MAN-3 | `OnnxImageAnalyzer` in the server: load the pinned model revision, identical preprocessing, map labels to visual symptoms. | idea §3 |
| S2-MAN-4 | Image quality checks (blur, darkness, size) + `unclear` abstain threshold with friendly messages. | NFR-05, NFR-07 |
| S2-MOH-1 | Risk-engine test matrix: every red flag, 100% branch coverage. | DR-02 |
| S2-MOH-2 | Auth, privacy and deletion integration tests. | NFR-03, NFR-04 |
| S2-MOH-3 | Frontend component tests for chat, confirmation and results. | — |
| S2-MOH-4 | Coverage gate (70%) in CI for server (pytest-cov) and client (Vitest) + reports as artifacts. | NFR-08 |
| S2-DIM-1 | "Delete my data" and "Export my data" endpoints + UI. | DR-06, NFR-04 |
| S2-DIM-2 | JWT expiry/refresh, secure cookie flags, CSRF protection. | NFR-03 |
| S2-DIM-3 | Emergency UX review: urgent result shows the emergency number (112) first. | FR-15, DR-02 |
| S2-DIM-4 | Privacy policy page + consent versioning (re-ask when the policy changes). | DR-08 |

**Sprint 2 exit:** every in-scope feature works on staging, including real CV inference. Feature freeze.

---

## 7. Sprint 3: Hardening & Release (11–20 Nov)

| ID | Task | Req. |
|---|---|---|
| S3-RUT-1 | First production release through CD (leader-approved), Sentry for client and server, UptimeRobot on the health endpoint. | NFR-05 |
| S3-RUT-2 | Rollback drill on staging (Render + Vercel) + demo-day plan (paid instance or warm-up). | NFR-05 |
| S3-RUT-3 | Release `v1.0.0`: changelog, release notes, final README. | NFR-08 |
| S3-HAR-1 | Query performance review (`EXPLAIN ANALYZE`) + index fixes. | NFR-01 |
| S3-HAR-2 | Backup and restore procedure on Neon, tested once. | NFR-05 |
| S3-HAR-3 | Data-integrity tests + final database documentation. | NFR-08 |
| S3-KAV-1 | API contract freeze + authorization audit (no cross-user access). | NFR-03 |
| S3-KAV-2 | Input validation and per-endpoint rate-limit audit. | NFR-03 |
| S3-KAV-3 | Performance: p95 result time ≤ 5 s on staging. | NFR-01 |
| S3-NIT-1 | Full AI regression run + fixes. | NFR-07 |
| S3-NIT-2 | Fallback provider (Gemini) + latency budget. | NFR-05 |
| S3-NIT-3 | AI documentation: prompts, limitations, failure modes. | NFR-08 |
| S3-NIS-1 | Final model evaluation report (accuracy, confusion matrix, red-flag recall). | NFR-07 |
| S3-NIS-2 | Risk-consistency verification (same input → same output, 1000 runs). | DR-02 |
| S3-NIS-3 | Model card for the condition model: data, method, limits, intended use. | NFR-08 |
| S3-VIV-1 | Responsive/mobile pass for all chat screens, tested as an installed PWA on Android and iOS. | NFR-09 |
| S3-VIV-2 | Lighthouse ≥ 90 for PWA, performance and accessibility; code splitting. | NFR-01, NFR-06 |
| S3-VIV-3 | i18n with react-i18next + Hindi translation of the chat UI. | NFR-06 |
| S3-DAR-1 | WCAG 2.1 AA audit + fixes. | NFR-06 |
| S3-DAR-2 | Usability test with 5 users + top-5 fixes. | NFR-06 |
| S3-DAR-3 | Final visual polish + demo script walkthrough. | — |
| S3-MAN-1 | Final CV evaluation: fairness across skin tones, failure tests (irrelevant, blurry, edge images). | NFR-07 |
| S3-MAN-2 | Inference performance on Render CPU: ≤ 1 s per image, total RAM < 512 MB. | NFR-01 |
| S3-MAN-3 | CV model card + limitations in `docs/`. | NFR-08 |
| S3-MOH-1 | Full regression + E2E matrix (browsers × devices, installed PWA). | NFR-09 |
| S3-MOH-2 | Load test (Locust or Artillery) against staging. | NFR-02 |
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
6. The change works on **staging** after the automatic deploy (check it there, not only locally).
