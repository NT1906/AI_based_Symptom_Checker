# AI-Based Symptom Checker (Group 14 · IT314 Software Engineering)

A conversational, **informational** triage aid: users describe symptoms in plain language (optionally with a photo), confirm what the system understood, and get the 2–3 most likely conditions with a plain-language confidence level, a risk tier (self-care / consult a doctor / urgent), and a next step: self-care tips or a map search for the right kind of specialist.

> ⚠️ This is not a medical diagnosis tool. It never diagnoses, prescribes or books appointments.

## Start here

| If you are… | Read |
|---|---|
| A team member starting a task | [CONTRIBUTING.md](CONTRIBUTING.md) → [docs/SPRINT_PLAN.md](docs/SPRINT_PLAN.md) |
| Looking for a command (setup, daily start, run, test, git) | [docs/commands.md](docs/commands.md) |
| An AI coding assistant | [AI_RULES.md](AI_RULES.md), before anything else |
| Checking who owns what | [docs/rules.md](docs/rules.md) |
| Checking the product scope | [docs/idea.md](docs/idea.md) |
| Checking the stack / deployment | [docs/tech-stack.md](docs/tech-stack.md) |
| The team leader | [docs/github-setup.md](docs/github-setup.md) |

## Timeline

| Sprint | Dates (2026) | Goal |
|---|---|---|
| 0 | 10–13 Oct | Setup & contracts |
| 1 | 14–27 Oct | Walking skeleton (end-to-end flow) |
| 2 | 28 Oct–10 Nov | Feature complete |
| 3 | 11–20 Nov | Hardening, release & demo |

## Tech stack

**Frontend:** React 18 + TypeScript + Vite, installable **PWA**, Tailwind, Zustand, TanStack Query, deployed on **Vercel**.
**Backend:** Python 3.12 + **FastAPI**, Pydantic v2, SQLAlchemy 2.0 + Alembic, PostgreSQL (Neon), shipped as a **Docker** image and deployed on **Render** or any **VPS** ([deployment guide](docs/deployment.md)).
**AI/ML:** OpenAI through a single AI gateway (mock provider for dev); CV models trained with PyTorch + timm on Kaggle/Colab, served as ONNX; scikit-learn condition model.
**Quality:** pytest, Vitest, Playwright, ruff, mypy, ESLint; GitHub Actions CI/CD (staging on every merge, production after leader approval).

Details and reasoning: [docs/tech-stack.md](docs/tech-stack.md).

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
