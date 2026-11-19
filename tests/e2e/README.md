# E2E Tests — AI-Based Symptom Checker

**Task:** S2-RUT-6 — Full regression and E2E matrix

This directory contains Playwright end-to-end tests covering the browser,
client, and server integration.

## Browser and device matrix

The Playwright configuration includes these projects:

| Project | Browser / Device |
|---|---|
| chromium-desktop | Desktop Chrome |
| firefox-desktop | Desktop Firefox |
| webkit-desktop | Desktop Safari |
| pixel-5-chrome | Pixel 5 |
| iphone-12-safari | iPhone 12 |
| ipad-tablet | iPad (7th generation) |

These projects provide browser and device-emulation coverage.
They do not replace manual testing of an installed PWA on physical devices.

## Prerequisites

The full local stack must be running:

1. Start the database:
   `docker compose up -d db`
2. Start the backend with mock providers:
   `cd server && uvicorn app.main:app --reload`
3. Start the frontend:
   `cd client && npm run dev`

## Install dependencies and browsers

```bash
cd tests/e2e
npm ci
npx playwright install chromium firefox webkit
