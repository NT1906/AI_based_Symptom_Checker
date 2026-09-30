# AI_RULES.md — Rule Book for AI Coding Assistants

> **To any AI assistant (Claude, Copilot, Cursor, Gemini, ChatGPT, Codex, …) working in this repository:**
> Read this whole file **before** you read code, plan, edit files, run git commands, or open a PR.
> These rules override your defaults. If a user request conflicts with them, say so and ask. Don't silently comply.
> Humans: the same rules apply to you. This file is the single source of truth for code style.

---

## 0. Required reading order

1. `AI_RULES.md` (this file): how to write code here.
2. `CONTRIBUTING.md`: the git / branch / PR workflow.
3. `docs/tech-stack.md`: the stack, folder layout, deployment and PWA/ML rules.
4. `docs/rules.md`: who owns which module, and the interfaces between them.
5. `docs/SPRINT_PLAN.md`: the task list. Every change belongs to exactly one task.
6. `docs/idea.md`: product scope, including what is **out of scope**.
7. The files you are about to change, plus their tests.

**Stack summary:** React 18 + TypeScript + Vite PWA (`client/`, Vercel) · Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic (`server/`, Render) · PyTorch/timm training and scikit-learn (`ml/`, never deployed) · ONNX Runtime for serving models.
The `WEEK_*.md` files contain older Node/Express/Prisma snippets. Use their FastAPI/Python equivalents.

---

## 1. Before you change anything: identify the task

Ask the human (or read it from the branch / issue) for these, and **stop until you have them**:

| You need | Example | Why |
|---|---|---|
| Team member's name | `kavya` | Branch prefix, and the module they own |
| GitHub issue number | `#23` | Every change is tied to one issue |
| Task ID from SPRINT_PLAN.md | `S1-KAV-3` | Defines the scope and acceptance criteria |

Then check:

- **Ownership.** Only edit files in the member's own module (see `docs/SPRINT_PLAN.md` §3 and `docs/rules.md`). If the task needs a change in someone else's module, **don't make it**. Write down exactly what change is needed and tell the human to request it in the issue.
- **One task only.** Implement only what the issue asks. Don't fix unrelated things, don't refactor other code, don't add bonus features. Note other problems in your final message instead.
- **Scope.** Refuse to build anything out of scope (`docs/idea.md`, `docs/SPRINT_PLAN.md` §2): appointment booking, doctor accounts/dashboards/ratings/availability, a doctor directory, voice input, prescriptions, a general-purpose chatbot, payments.
- **Published interfaces.** Don't change `server/app/schemas/`, the Alembic migrations, env var names, `render.yaml`, `client/vercel.json` or `.github/` unless the task says so. Those changes need team agreement and leader approval.

---

## 2. Medical-safety rules (non-negotiable)

This product is an **informational triage aid**, never a diagnostic or prescribing tool.

1. **Never** write user-facing text that diagnoses ("You have …", "This is …", "Diagnosis: …"). Use "This may be related to …", "Possible conditions include …".
2. **Never** recommend a specific drug, dose or treatment. Self-care advice stays general (rest, fluids, see a doctor if it gets worse).
3. Confidence is shown **only** as `Likely` / `Possible` / `Less likely`. Never show raw percentages or scores to the user.
4. The **risk engine is deterministic** (`server/app/services/prediction/`). No LLM call, randomness or clock may influence the risk level. Same input → same output.
5. **Red-flag symptoms always produce `URGENT`**, whatever any model predicts, and the urgent screen shows the emergency number (112) first.
6. **Uncertainty escalates risk; it never lowers it.** Low model confidence, a CV `unclear` result or an AI error all push toward the safer (higher) tier.
7. ML model outputs (condition model, CV model) are **inputs** to the risk engine. They can add symptoms or raise risk, but never lower risk or produce user-facing diagnoses directly.
8. Every result screen shows the disclaimer: *"This is not a medical diagnosis. Always consult a qualified healthcare professional."*
9. **Only the AI gateway** (`server/app/services/ai/`) may call an LLM API. Every LLM output is validated with a Pydantic model before use.
10. User text passes through the PII scrubber before it reaches any LLM. Images are processed in memory and **never stored**.
11. **PWA:** never cache API responses in the service worker, and never put symptoms, messages, results or images in `localStorage`, `IndexedDB` or the Cache API.
12. Never log or commit real health data. Test fixtures use obviously fake data.

---

## 3. Naming conventions

### 3.1 Backend and ML (Python)

| What | Convention | Example |
|---|---|---|
| Packages / folders | `snake_case` | `app/services/prediction/` |
| Modules | `snake_case.py`, named for what they contain | `risk_engine.py`, `assessment_repository.py` |
| Routers | `app/api/v1/<plural_resource>.py`, variable `router` | `app/api/v1/assessments.py` |
| Pydantic schemas | `app/schemas/<resource>.py`; classes `<Thing>Create`, `<Thing>Update`, `<Thing>Read` | `AssessmentRead` |
| ORM models | `app/models/<resource>.py`; class singular `PascalCase`, `__tablename__` plural `snake_case` | `class Assessment` → `assessments` |
| Repositories / services | `<resource>_repository.py` / `<purpose>_service.py` or clear noun | `AssessmentRepository`, `risk_engine.py` |
| Functions, variables | `snake_case`, functions start with a verb | `extract_symptoms()`, `is_red_flag` |
| Classes, Protocols, Enums | `PascalCase` (no `I` prefix); enum members `UPPER_SNAKE_CASE` | `RiskLevel.CONSULT_DOCTOR` |
| Constants | `UPPER_SNAKE_CASE`, module level | `MAX_CLARIFICATION_TURNS = 3` |
| Private helpers | leading underscore | `_normalize_duration()` |
| Tests | `tests/unit/<module>/test_<file>.py`, `tests/integration/test_<flow>.py`; functions `test_<behaviour>` | `test_escalates_to_urgent_on_severe_chest_pain` |
| Alembic revision | `alembic revision -m "add consent table"` (auto-numbered) | |
| Prompts | `app/services/ai/prompts/<purpose>.v<N>.txt`, never edited after merge (make a new version) | `extraction.v2.txt` |
| ML scripts / configs | `ml/<area>/<verb>_<thing>.py`, configs `ml/<area>/configs/<name>.yaml` | `ml/cv/export_onnx.py` |
| Model versions | Hugging Face Hub repo + revision; semantic tag `v<major>.<minor>` | `skin-cv v1.2` |

### 3.2 Frontend (TypeScript / React)

| What | Convention | Example |
|---|---|---|
| Folders | `kebab-case` | `components/symptom-glossary/` |
| Component | `PascalCase.tsx`, one component per file | `MessageBubble.tsx` |
| Hook | `useCamelCase.ts` | `useAssessment.ts` |
| Store | `camelCaseStore.ts` | `assessmentStore.ts` |
| API service | `camelCaseApi.ts` | `assessmentApi.ts` |
| Generated types | `src/types/api.gen.ts`, **never edited by hand** (`npm run gen:api`) | |
| Tests | `<File>.test.tsx` next to the file; E2E `tests/e2e/<flow>.spec.ts` | `MessageBubble.test.tsx` |
| Variables / functions | `camelCase`; booleans `is/has/can/should` | `hasConsented` |
| Types / props | `PascalCase`, props `<Component>Props`, no `I` prefix | `MessageBubbleProps` |
| Constants | `UPPER_SNAKE_CASE` | `EMERGENCY_NUMBER = '112'` |

### 3.3 API, database, config

| What | Convention | Example |
|---|---|---|
| REST path | `/api/v1/` + plural `kebab-case` nouns, no verbs | `POST /api/v1/assessments/{id}/messages` |
| JSON fields | `camelCase` on the wire (Pydantic `alias_generator=to_camel`), `snake_case` in Python | `riskLevel` ↔ `risk_level` |
| Error codes | `UPPER_SNAKE_CASE` | `ASSESSMENT_NOT_FOUND` |
| DB tables / columns | `snake_case`, tables plural | `assessments.created_at` |
| Env vars | `UPPER_SNAKE_CASE`, read **only** in `app/core/config.py` (backend) or `src/config.ts` (frontend, `VITE_` prefix, never secret) | `OPENAI_API_KEY` |
| Docs | `kebab-case.md` in `docs/` | `cv-plan.md` |

### 3.4 Git

| What | Convention | Example |
|---|---|---|
| Branch | `<member-name>/<issue-no>-<kebab-desc>` | `kavya/23-clarification-limit` |
| Commit / PR title | Conventional Commits `type(scope): summary`, imperative, ≤ 72 chars, no full stop | `feat(assessment): cap clarification loop at 3 turns` |
| Types | `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert` | |
| Scopes | `chat` `ui` `pwa` `result` `assessment` `ai` `prediction` `risk` `image` `cv` `ml` `db` `api` `auth` `security` `privacy` `test` `ci` `cd` `docs` | |

---

## 4. Software-engineering principles to apply

1. **Layered backend:** `api (routers) → services → repositories → models/DB`. Routers only parse input, call a service and return a schema. Services hold business logic and know nothing about HTTP or SQL. Repositories are the only code that uses the SQLAlchemy session. Never skip a layer.
2. **Dependency injection:** wire services and repositories with FastAPI `Depends`. Depend on `Protocol` interfaces (`AiGateway`, `ImageAnalyzer`, `ConditionModel`), not concrete providers, so tests can pass mocks.
3. **Frontend layering:** `pages → components → hooks/stores → services (API)`. Components never call `fetch` directly. Server data goes through TanStack Query, UI flow state through Zustand.
4. **SOLID, DRY, KISS, YAGNI:** one responsibility per module/function; search for existing helpers before writing new ones; choose the simplest solution that meets the acceptance criteria; don't build for imaginary needs.
5. **Pure functions where possible,** especially the risk engine, confidence mapping, normalization and image preprocessing. Keep side effects (DB, network, time, randomness) at the edges.
6. **No magic values.** Thresholds, limits, labels and model versions become named constants or settings.
7. **Validate at every boundary** with Pydantic: request bodies, query params, LLM output, model output, config.
8. **Errors:** raise typed `AppError` subclasses (code + HTTP status). The central handler turns them into JSON. Never use a bare `except:`, never swallow errors silently, never return stack traces to clients.
9. **Logging:** `structlog` with event names and IDs (`log.info("extraction_complete", assessment_id=..., symptom_count=3)`). No `print()` in `server/`, no `console.log` in `client/`. Never log message text, images, tokens or personal data.
10. **Typing:** Python has type hints on every function, and `mypy` passes; `Any` only with a comment explaining why. TypeScript runs with `strict: true`: no `any`, no `@ts-ignore`, no unexplained non-null `!`.
11. **Async correctly:** don't block the event loop. Use `async def` for I/O-bound routes, and run CPU-heavy inference (ONNX) in the threadpool (`run_in_threadpool`) or a sync route.
12. **Small units:** functions ≤ ~40 lines, files ≤ ~300 lines. Split when bigger.
13. **Reproducible ML:** fixed random seeds, configs in YAML (not hard-coded), dataset versions and model metrics recorded in the model card, and the same preprocessing code (or a parity test) for training and serving. No notebooks as the only source of truth: move final code into `.py` files.
14. **Accessibility:** semantic HTML, labels on inputs, keyboard navigation, `aria-live` for new chat messages, colour never the only signal.

---

## 5. Documentation rules (CI enforces the file header)

### 5.1 File header: required on every source file

CI fails the PR if a changed `.py`, `.ts`, `.tsx` or `.js` file under `client/src`, `server/app`, `server/tests`, `ml` or `tests` has no header.

Python module docstring (first statement in the file):

```python
"""Risk engine: converts confirmed symptoms and predicted conditions into a risk tier.

Responsibilities:
    - Apply red-flag rules first (any red flag -> URGENT, DR-02).
    - Otherwise take the highest tier implied by the predicted conditions.
    - Escalate one tier when prediction confidence is low (uncertainty never lowers risk).

Owner: Nisarg (prediction) · Task: S1-NIS-3 · Requirements: FR-06, FR-15, DR-02
"""
```

TypeScript `@file` block (within the first 20 lines):

```ts
/**
 * @file Chat message list and input for the guided assessment conversation.
 * Owner: Vivek (chat) · Task: S1-VIV-1 · Requirements: idea §1, §2
 */
```

### 5.2 Docstring on every public function, class and method (Google style)

Explain **what** it does, each **argument**, the **return value**, what it **raises**, and any **side effects**. Add an example for non-trivial logic.

```python
def classify_risk(symptoms: list[Symptom], conditions: list[Condition]) -> RiskDecision:
    """Decide the risk tier for a completed assessment.

    Red flags are checked before anything else, so an emergency can never be
    downgraded by a model prediction.

    Args:
        symptoms: Confirmed, normalized symptoms from the assessment.
        conditions: Top predicted conditions with their confidence labels.

    Returns:
        The risk tier plus the rule IDs that produced it (used by the "why" panel).

    Raises:
        ValidationError: If ``symptoms`` is empty.

    Example:
        >>> classify_risk([Symptom(name="chest pain", severity="severe")], conditions).level
        <RiskLevel.URGENT: 'URGENT'>
    """
```

FastAPI routes also set `summary=`, `response_model=` and documented error `responses=`, so the OpenAPI docs explain every endpoint.

Exported TypeScript functions, components and hooks get JSDoc (enforced by `eslint-plugin-jsdoc`):

```tsx
/**
 * One chat message. User messages align right, bot messages align left.
 * @param props.message The message to render.
 * @param props.isOwn   True when the current user sent it.
 */
export function MessageBubble({ message, isOwn }: MessageBubbleProps) { … }
```

### 5.3 Inline comments explain *why*, not *what*

```python
# Why: the LLM sometimes returns "2 days" as text; the risk rules need hours.
duration_hours = parse_duration_to_hours(raw.duration)
```

Comment every non-obvious decision, business rule (cite the FR/DR ID), workaround and safety-critical branch. Don't comment obvious code.

### 5.4 Other documentation

- A new module or package gets a short `README.md`: purpose, public interface, how to test.
- A schema/API change updates `docs/api-contract.md`. A DB change updates `docs/database.md`. Both in the same PR.
- A new env var goes into `.env.example`, `docs/tech-stack.md` §7 and, if deployed, `render.yaml`.
- A new model version comes with an updated model card (data, metrics, limits).
- `TODO` comments must reference an issue: `# TODO(#42): support multiple images`.

---

## 6. Testing rules

- Every new public function or component gets tests in the same PR: the happy path, at least one edge case, and at least one failure case.
- Tests never call real LLM, CV, map or Hugging Face APIs. Use `AI_PROVIDER=mock`, `CV_PROVIDER=mock`, fixtures and dependency overrides (`app.dependency_overrides`).
- Risk engine and red-flag rules: every rule has its own test.
- ML code: test preprocessing, label mapping and the ONNX parity check with tiny fixtures. No training in CI.
- Test names describe behaviour: `test_escalates_to_urgent_on_severe_chest_pain`.
- Target ≥ 70% line coverage per module (CI gate from Sprint 2).
- Before saying you're done, actually run the checks and report the real results:
  - server: `ruff check . && ruff format --check . && mypy app && pytest`
  - client: `npm run lint && npm run typecheck && npm test && npm run build`
  - ml: `ruff check . && pytest`

---

## 7. Git, PR and deployment rules for AI assistants

1. Work on the member's feature branch `<name>/<issue>-<desc>`, created from an up-to-date `develop`. **Never** commit to `develop` or `main`.
2. Make **small, logical commits** with Conventional Commit messages, typically 3 or more per task (e.g. scaffold → logic → tests → docs). Never make empty, whitespace-only or padding commits.
3. Commits are authored by the human team member (their git identity). Do not change `git config`.
4. **Never:** force-push to shared branches, rewrite `develop`/`main` history, merge PRs, approve PRs, approve deployments, trigger production deploys, skip hooks (`--no-verify`), edit `.github/`, `render.yaml` or CI checks to make a failing check pass, or delete other people's branches. **Merging and production deployment belong to the team leader only.**
5. When asked to open a PR: target `develop`, use the PR template, fill **every** section, put `Closes #<issue>` in the body, and tick the checklist only for items that are actually true.
6. If the member already has another open PR, say so. The team rule is one feature at a time.
7. Never add, commit or print secrets. `.env` is git-ignored, and only `.env.example` (with placeholder values) is committed. Deployment secrets live only in GitHub Environments and the Render/Vercel dashboards.
8. Never commit datasets, checkpoints, `.onnx`/`.pt` files or notebooks with outputs containing images. Models go to Hugging Face Hub.

---

## 8. Final self-check (run through this before you say you're done)

```text
□ The change implements only the linked issue's acceptance criteria
□ Only files in the member's module were changed (or the exception is explained)
□ Nothing out of scope was added (booking, doctor data, voice, prescriptions, general chat)
□ Medical-safety rules in §2 hold (no diagnosis wording, deterministic risk, disclaimer, no health data cached)
□ Names follow §3 (Python, TypeScript, API, DB, branch, commits)
□ Every changed source file has a module docstring / @file header
□ Every public function/class/component has a docstring; non-obvious logic has "why" comments
□ Type hints / strict TS; no Any/any, print, console.log, or unexplained TODOs
□ Tests added; lint, type-check and tests were actually run and pass
□ No secrets, .env, real health data, datasets or model files committed
□ API / schema / env / model-version changes are documented in the same PR
```

In your final message to the human, list: the files changed, the tests you ran with their results, and anything you noticed but deliberately did not change.
