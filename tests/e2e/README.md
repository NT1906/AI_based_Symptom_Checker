# E2E Tests — AI-Based Symptom Checker

**Owner:** Mohit (testing) · **Task:** S0-MOH-1 (scaffold), S1-MOH-4 (happy-path impl)

This directory contains Playwright end-to-end tests that run the full browser → client → server stack.

## Directory structure

```
tests/e2e/
├── playwright.config.ts     # Playwright project configuration
├── fixtures.ts              # Custom test + page-object helpers (ConsentPage, ChatPage, …)
├── package.json             # @playwright/test dependency
├── specs/
│   ├── health.spec.ts                    # S0-MOH-1: backend health endpoint
│   ├── assessment-happy-path.spec.ts     # S1-MOH-4: consent → chat → confirm → result → restart
│   └── assessment-urgent-path.spec.ts    # S1-MOH-4: red-flag → URGENT + 112 shown first
└── README.md                # This file
```

## Prerequisites

The full local stack must be running before tests start:

```bash
# 1. Start the database
docker compose up -d db

# 2. Start the backend (AI_PROVIDER=mock, CV_PROVIDER=mock)
cd server && uvicorn app.main:app --reload

# 3. Start the frontend dev server
cd client && npm run dev
```

## Running

```bash
cd tests/e2e
npm ci
npx playwright install --with-deps chromium

# Headless (CI default)
npx playwright test

# Headed (interactive debugging)
npx playwright test --headed

# Playwright UI mode
npx playwright test --ui

# Against staging
PLAYWRIGHT_BASE_URL=https://staging.example.com npx playwright test
```

## Adding new specs

1. Create a new file in `specs/` named `<flow>.spec.ts`.
2. Import `test` and `expect` from `../fixtures` (not directly from `@playwright/test`).
3. Use the provided page-object fixtures (`chatPage`, `confirmationPage`, `resultPage`, etc.).
4. Never call real LLM, CV, or map APIs — all tests run against mock providers.
5. Test names must describe behaviour: `"completes a full assessment and shows disclaimer"`.

## Notes

- All tests use `AI_PROVIDER=mock` and `CV_PROVIDER=mock` — no real API keys needed.
- Health data must never be stored in test fixtures or assertions (AI_RULES §2, §6).
- The `playwright-report/` directory is git-ignored; CI uploads it as an artifact.
