# AI_RULES.md — Rule Book for AI Coding Assistants

> **To any AI assistant (Claude, Copilot, Cursor, Gemini, ChatGPT, Codex, …) working in this repository:**
> Read this whole file **before** you read code, plan, edit files, run git commands, or open a PR.
> These rules override your defaults. If a user request conflicts with them, say so and ask. Don't silently comply.
> Humans: the same rules apply to you. This file is the single source of truth for code style.

---

## 0. Required reading order

1. `AI_RULES.md` (this file): how to write code here.
2. `CONTRIBUTING.md`: the git / branch / PR workflow.
3. `docs/rules.md`: who owns which module, and the interfaces between them.
4. `docs/SPRINT_PLAN.md`: the task list. Every change belongs to exactly one task.
5. `docs/idea.md`: product scope, including what is **out of scope**.
6. The files you are about to change, plus their tests.

---

## 1. Before you change anything: identify the task

Ask the human (or read it from the branch / issue) for these, and **stop until you have them**:

| You need | Example | Why |
|---|---|---|
| Team member's name | `kavya` | Branch prefix, and the module they own |
| GitHub issue number | `#23` | Every change is tied to one issue |
| Task ID from SPRINT_PLAN.md | `S1-KAV-3` | Defines the scope and acceptance criteria |

Then check:

- **Ownership.** Only edit files in the member's own module (see the ownership table in `docs/rules.md` and `docs/SPRINT_PLAN.md` §3). If the task needs a change in someone else's module, **don't make it**. Write down exactly what change is needed and tell the human to request it in the issue.
- **One task only.** Implement only what the issue asks. Don't fix unrelated things "while you're here", don't refactor other code, don't add bonus features. Note other problems in your final message instead.
- **Scope.** Refuse to build anything listed as out of scope in `docs/idea.md` or `docs/SPRINT_PLAN.md` §2: appointment booking, doctor accounts/dashboards/ratings/availability, a doctor directory, voice input, prescriptions, a general-purpose chatbot, payments.
- **Published interfaces.** Don't change `shared/types/`, the OpenAPI spec, the Prisma schema or env var names unless the task says so. Those changes need team agreement first.

---

## 2. Medical-safety rules (non-negotiable)

This product is an **informational triage aid**, never a diagnostic or prescribing tool.

1. **Never** write user-facing text that diagnoses ("You have …", "This is …", "Diagnosis: …"). Use "This may be related to …", "Possible conditions include …".
2. **Never** recommend a specific drug, dose, or treatment. Self-care advice stays general (rest, fluids, see a doctor if it gets worse).
3. Confidence is shown **only** as `Likely` / `Possible` / `Less likely`. Never show raw percentages or scores to the user.
4. The **risk engine is deterministic** (`server/src/services/prediction/`). No LLM call, randomness or clock may influence the risk level. Same input → same output.
5. **Red-flag symptoms always produce `URGENT`**, whatever the model predicts, and the urgent screen shows the emergency number (112 in India) first.
6. **Uncertainty escalates risk; it never lowers it.** When unsure, pick the safer (higher) tier.
7. Every result screen shows the disclaimer: *"This is not a medical diagnosis. Always consult a qualified healthcare professional."*
8. **Only the AI gateway** (`server/src/services/ai/`) may call an LLM API. Every LLM output is validated with a Zod schema before anyone uses it.
9. User text is passed through the PII scrubber before it is sent to any LLM.
10. Never log or commit real health data. Test fixtures use obviously fake data.

---

## 3. Naming conventions

### 3.1 Files and folders

| What | Convention | Example |
|---|---|---|
| Folders | `kebab-case` | `client/src/components/symptom-glossary/` |
| React component | `PascalCase.tsx`, one component per file | `MessageBubble.tsx` |
| React hook | `useCamelCase.ts` | `useAssessment.ts` |
| Zustand store | `camelCaseStore.ts` | `assessmentStore.ts` |
| Backend layer file | `camelCase.<layer>.ts` | `assessment.routes.ts`, `assessment.controller.ts`, `riskEngine.service.ts`, `assessment.repository.ts`, `auth.middleware.ts`, `assessment.schema.ts` (Zod), `app.config.ts` |
| Shared types | `camelCase.types.ts` | `assessment.types.ts` |
| Utility module | `camelCase.ts` | `formatDuration.ts` |
| Test file | same name + `.test.ts(x)` next to the file, or in `tests/` | `riskEngine.service.test.ts` |
| E2E test | `kebab-case.spec.ts` in `tests/e2e/` | `happy-path.spec.ts` |
| Python module | `snake_case.py` | `evaluate_extraction.py` |
| Prompt file | `purpose.v<N>.txt`, never edited after merge (make a new version) | `extraction.v2.txt` |
| Dataset | `snake_case.json/csv` + a `README.md` naming the source | `conditions_v1.json` |
| Docs | `kebab-case.md` in `docs/` (existing `WEEK_*.md` files are kept) | `image-pipeline.md` |

### 3.2 Code identifiers

| What | Convention | Example |
|---|---|---|
| Variables, functions | `camelCase`, functions start with a verb | `extractSymptoms()`, `isRedFlag` |
| Booleans | `is/has/can/should` prefix | `hasConsented` |
| Classes, interfaces, types | `PascalCase`, **no** `I` prefix | `AssessmentOrchestrator`, `Symptom` |
| Enums | `PascalCase` name, `UPPER_SNAKE_CASE` members | `RiskLevel.CONSULT_DOCTOR` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_CLARIFICATION_TURNS = 3` |
| React props type | `<Component>Props` | `MessageBubbleProps` |
| Python | `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants | `load_cases()` |
| Env vars | `UPPER_SNAKE_CASE`, read **only** in `server/src/config/` | `OPENAI_API_KEY` |

### 3.3 Database and API

| What | Convention | Example |
|---|---|---|
| Prisma model | `PascalCase` singular | `model Assessment` |
| Prisma field | `camelCase` | `createdAt` |
| DB table / column | `snake_case` plural tables, via `@@map` / `@map` | `assessments.created_at` |
| REST path | `/api/v1/` + plural `kebab-case` nouns, no verbs | `POST /api/v1/assessments/:id/messages` |
| JSON fields | `camelCase` | `{ "riskLevel": "URGENT" }` |
| Error codes | `UPPER_SNAKE_CASE` | `ASSESSMENT_NOT_FOUND` |

### 3.4 Git

| What | Convention | Example |
|---|---|---|
| Branch | `<member-name>/<issue-no>-<kebab-desc>` | `kavya/23-clarification-limit` |
| Commit / PR title | Conventional Commits `type(scope): summary`, imperative, ≤ 72 chars, no full stop | `feat(assessment): cap clarification loop at 3 turns` |
| Types | `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert` | |
| Scopes | `chat` `ui` `result` `assessment` `ai` `prediction` `risk` `image` `db` `api` `auth` `security` `privacy` `test` `ci` `docs` | |

---

## 4. Software-engineering principles to apply

1. **Layered architecture (backend):** `routes → controllers → services → repositories → Prisma`. Routes only wire things up. Controllers handle HTTP (parse, validate, respond). Services hold business logic and know nothing about HTTP. Repositories are the only code that touches Prisma. Never skip a layer.
2. **Frontend layering:** `pages → components → hooks/stores → services (API)`. Components never call `fetch`/`axios` directly.
3. **SOLID:** one responsibility per module/class/function; depend on interfaces (`AiGateway`, `ImageAnalyzer`), not concrete providers; inject dependencies through constructors or parameters so tests can pass mocks.
4. **DRY / KISS / YAGNI:** reuse existing helpers (search before you write), choose the simplest solution that meets the acceptance criteria, and don't build for imaginary future needs.
5. **Pure functions where possible,** especially the risk engine, confidence mapping and normalization. Keep side effects (DB, network, time) at the edges.
6. **No magic values.** Thresholds, limits and labels become named constants or config.
7. **Validate at the boundary.** Every request body, param and query is validated with Zod. Every LLM/CV output is validated too. Trust nothing from outside the process.
8. **Error handling:** throw typed errors (`AppError` subclasses with a code and HTTP status) and let the central error handler respond. Never swallow errors silently, and never expose stack traces to clients.
9. **Logging:** structured Pino logs only (`logger.info({ event, assessmentId })`). No `console.log` in committed code. Never log message text, images, tokens or personal data.
10. **Configuration:** all config comes from `server/src/config/` (backend) or `import.meta.env` via one `client/src/config.ts` (frontend). No `process.env` anywhere else.
11. **TypeScript strictness:** `strict: true`. No `any` (use `unknown` + narrowing), no `@ts-ignore`, no non-null `!` without a comment explaining why.
12. **Small units:** functions ≤ ~40 lines and files ≤ ~300 lines. Split when bigger.
13. **Accessibility:** semantic HTML, labels on every input, keyboard navigation, `aria-live` for new chat messages, colour is never the only signal (risk badges also have text and an icon).

---

## 5. Documentation rules (CI enforces the file header)

### 5.1 File header: required on every source file (`.ts .tsx .js .py`)

CI fails a PR if a changed source file has no header.

```ts
/**
 * @file Risk engine: converts confirmed symptoms + predicted conditions into a risk tier.
 *
 * Responsibilities:
 *  - Apply red-flag rules first (any red flag → URGENT, DR-02).
 *  - Otherwise take the highest tier implied by the predicted conditions.
 *  - Escalate one tier when prediction confidence is low (uncertainty never lowers risk).
 *
 * Owner: Nisarg (prediction module) · Task: S1-NIS-3 · Requirements: FR-06, FR-15, DR-02
 */
```

```python
"""Extraction evaluation harness.

Runs every case in ai/evaluation/cases.json through the extraction endpoint and
reports precision, recall and F1 per symptom field.

Owner: Mohit (QA) · Task: S1-MOH-3 · Requirements: NFR-07
"""
```

### 5.2 Doc comment on every exported function, class, method, component and type

Explain **what** it does, each **parameter**, what it **returns**, what it **throws**, and any **side effects**. Add an `@example` for non-trivial logic.

```ts
/**
 * Decides the risk tier for a completed assessment.
 *
 * Red flags are checked before anything else, so an emergency can never be
 * downgraded by the prediction model.
 *
 * @param symptoms   Confirmed, normalized symptoms from the assessment.
 * @param conditions Top predicted conditions with their confidence labels.
 * @returns The risk tier plus the rule IDs that produced it (used for the "why" panel).
 * @throws {ValidationError} If `symptoms` is empty.
 * @example
 *   classifyRisk([{ name: 'chest pain', severity: 'severe' }], conditions)
 *   // → { level: RiskLevel.URGENT, reasons: ['RF_CHEST_PAIN_SEVERE'] }
 */
export function classifyRisk(symptoms: Symptom[], conditions: Condition[]): RiskDecision { … }
```

React components describe their props and what the component renders:

```tsx
/**
 * One chat message. User messages align right, bot messages align left.
 * New bot messages are announced to screen readers through the parent's aria-live region.
 */
export function MessageBubble({ message, isOwn }: MessageBubbleProps) { … }
```

Python uses Google-style docstrings (`Args:`, `Returns:`, `Raises:`).

### 5.3 Inline comments explain *why*, not *what*

```ts
// ✅ Why: the LLM sometimes returns "2 days" as a string; the risk rules need hours.
const durationHours = parseDurationToHours(raw.duration);

// ❌ What (adds nothing): set durationHours to the parsed duration
```

Add an inline comment for every non-obvious decision, business rule (cite the FR/DR ID), workaround, or safety-critical branch. Don't comment obvious code.

### 5.4 Other documentation

- A new module gets a short `README.md` in its folder: purpose, public interface, how to test.
- An API change updates `docs/api/openapi.yaml` in the same PR.
- A schema change updates `docs/database.md` in the same PR.
- A new env var goes into `.env.example` with a comment.
- `TODO` comments must reference an issue: `// TODO(#42): handle multi-image uploads`.

---

## 6. Testing rules

- Every new exported function or component gets unit tests in the same PR: the happy path, at least one edge case, and at least one failure case.
- Tests never call real LLM, CV or map APIs. Use `AI_PROVIDER=mock` and mocks/fixtures.
- Risk engine and red-flag rules: every rule has its own test.
- Test names describe behaviour: `it('escalates to URGENT when chest pain is severe')`.
- Target ≥ 70% line coverage per module (CI gate from Sprint 2).
- Run `npm run lint && npm run typecheck && npm test` (or `ruff check . && pytest`) before saying the work is done, and report the actual results.

---

## 7. Git and PR rules for AI assistants

1. Work on the member's feature branch `<name>/<issue>-<desc>`, created from an up-to-date `develop`. **Never** commit to `develop` or `main`.
2. Make **small, logical commits** with Conventional Commit messages, typically 3 or more per task (e.g. scaffold → logic → tests → docs). Never make empty, whitespace-only or padding commits.
3. Commits are authored by the human team member (their git identity). Do not change `git config`.
4. **Never:** force-push to shared branches, rewrite `develop`/`main` history, merge PRs, approve PRs, skip hooks (`--no-verify`), disable or edit CI checks or `.github/` to make a failing check pass, or delete other people's branches.
5. When asked to open a PR: target `develop`, use the PR template, fill **every** section, put `Closes #<issue>` in the body, and tick the checklist only for items that are actually true.
6. If the member already has another open PR, say so. The team rule is one feature at a time.
7. Never add, commit or print secrets. `.env` is git-ignored, and only `.env.example` (with placeholder values) is committed.

---

## 8. Final self-check (run through this before you say you're done)

```text
□ The change implements only the linked issue's acceptance criteria
□ Only files in the member's module were changed (or the exception is explained)
□ Nothing out of scope was added (booking, doctor data, voice, prescriptions, general chat)
□ Medical-safety rules in §2 hold (no diagnosis wording, deterministic risk, disclaimer shown)
□ Names follow §3 (files, identifiers, DB, API, branch, commits)
□ Every changed source file has a @file header / module docstring
□ Every exported symbol has a doc comment; non-obvious logic has "why" comments
□ Tests added; lint, typecheck and tests were actually run and pass
□ No secrets, .env, real health data, console.log, `any`, or unexplained TODOs
□ API / schema / env changes are documented in the same PR
```

In your final message to the human, list: the files changed, the tests you ran with their results, and anything you noticed but deliberately did not change.
