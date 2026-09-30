# AI-Based Symptom Checker (Group 14 · IT314 Software Engineering)

A conversational, **informational** triage aid: users describe symptoms in plain language (optionally with a photo), confirm what the system understood, and get the 2–3 most likely conditions with a plain-language confidence level, a risk tier (self-care / consult a doctor / urgent), and a next step: self-care tips or a map search for the right kind of specialist.

> ⚠️ This is not a medical diagnosis tool. It never diagnoses, prescribes or books appointments.

## Start here

| If you are… | Read |
|---|---|
| A team member starting a task | [CONTRIBUTING.md](CONTRIBUTING.md) → [docs/SPRINT_PLAN.md](docs/SPRINT_PLAN.md) |
| An AI coding assistant | [AI_RULES.md](AI_RULES.md), before anything else |
| Checking who owns what | [docs/rules.md](docs/rules.md) |
| Checking the product scope | [docs/idea.md](docs/idea.md) |
| The team leader | [docs/github-setup.md](docs/github-setup.md) |

## Timeline

| Sprint | Dates (2026) | Goal |
|---|---|---|
| 0 | 10–13 Oct | Setup & contracts |
| 1 | 14–27 Oct | Walking skeleton (end-to-end flow) |
| 2 | 28 Oct–10 Nov | Feature complete |
| 3 | 11–20 Nov | Hardening, release & demo |

## Tech stack

React 18 + TypeScript + Vite + Zustand (client) · Node 20 + Express + TypeScript + Zod + Prisma + PostgreSQL (server) · OpenAI via one AI gateway, with a mock provider for development · Python for AI evaluation and the CV service · Vitest, Supertest, Playwright · GitHub Actions CI.

## Team

| Member | Module |
|---|---|
| Nisarg (leader) | Prediction & risk engine |
| Rutva | Backend foundation, integration & DevOps |
| Harsh | Database |
| Kavya | Assessment orchestration |
| Nishith | AI / NLP |
| Vivek | Frontend chat |
| Darshil | Frontend assessment UX |
| Mann | Image / CV |
| Mohit | QA & testing |
| Dimple | Security, privacy & safety |
