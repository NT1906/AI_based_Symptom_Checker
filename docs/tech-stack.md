# Tech Stack & Deployment Architecture

**Status:** decided by the team leader, 30 Sep 2026. This file supersedes the Node/Express/Prisma stack in `WEEK_1.md`–`WEEK_3.md`; the ideas in those files still apply, but their code snippets become their FastAPI/Python equivalents.
Changing anything here needs a PR approved by the leader.

---

## 1. Decisions at a glance

| Layer | Choice | Why |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite | Fast dev server, typed components, team familiarity |
| PWA | `vite-plugin-pwa` (Workbox) | Installable on phones, offline app shell, update prompts |
| Styling | Tailwind CSS | Consistent design tokens, fast iteration |
| Client state / server state | Zustand / TanStack Query | Small store for chat flow; caching + retries for API calls |
| Routing / i18n | React Router / react-i18next | Standard, well documented |
| API types | `openapi-typescript`, generated from FastAPI's OpenAPI | Frontend types can never drift from the backend |
| **Backend** | Python 3.12 + **FastAPI** + Uvicorn | Same language as the ML code, auto OpenAPI docs, Pydantic validation |
| Validation / settings | Pydantic v2 / pydantic-settings | One schema for request validation, docs and types |
| Database | PostgreSQL 16 (**Neon** free tier) | Managed, free, separate branches for staging and production |
| ORM / migrations | SQLAlchemy 2.0 / **Alembic** | Mature, typed, versioned migrations |
| Auth | JWT in an HttpOnly cookie (PyJWT) + argon2 password hashing (`pwdlib`) | No tokens in JS-readable storage |
| Security | FastAPI CORS middleware, custom security-headers middleware, `slowapi` rate limits | OWASP basics |
| Logging | `structlog` (JSON) | Structured, searchable logs |
| **LLM** | OpenAI Python SDK behind one `AiGateway`, model name set by `AI_MODEL` env; Gemini as fallback; `mock` provider for dev/CI | Structured JSON output; nobody needs a key to develop |
| **Prediction model** | Deterministic rule engine for risk + scikit-learn condition model (trained in `ml/`, exported to ONNX via `skl2onnx`) | Risk must be deterministic; the model adds ranking quality |
| **CV training** | PyTorch + `timm` (EfficientNet-B0 / MobileNetV3 transfer learning) on **Kaggle Notebooks / Google Colab** free GPUs | Free GPUs; pretrained backbones work with small datasets |
| Experiment tracking | Weights & Biases (free academic plan) | Compare runs, keep metrics per model version |
| Model registry | **Hugging Face Hub** model repo, pinned by revision | Models stay out of git; versioned and downloadable |
| **Model serving** | **ONNX Runtime (CPU)** inside the FastAPI service, INT8-quantized models | No PyTorch in production: small image, fits 512 MB RAM |
| Image handling | Pillow + NumPy, processed **in memory only** | Images are never stored (privacy, DR-06) |
| **Testing** | pytest + httpx (backend), Vitest + React Testing Library + MSW (frontend), Playwright (E2E) | Standard for each language |
| Quality | ruff (lint + format), mypy, ESLint + Prettier | Enforced in CI |
| **Hosting: frontend** | **Vercel** (Hobby) | Global CDN, PR preview URLs, zero-config Vite |
| **Backend packaging** | **Docker** image per commit, pushed to GHCR (`ghcr.io/nt1906/symptom-checker-api:<sha>`) | Build once, run the identical artifact anywhere |
| **Hosting: backend** | **Render** (image-backed web service, Singapore) by default, **or any VPS** with Docker + Caddy. Chosen per environment with `BACKEND_TARGET` ([deployment.md](deployment.md)) | Managed and free to start; a VPS gives full control, no cold starts and more RAM |
| CI / CD | GitHub Actions | One pipeline for everything, gated by the leader |
| Monitoring | Platform/Docker logs + health checks, UptimeRobot, Sentry (free tier) | Enough for a course project |

### Why the backend is not on Vercel
Vercel's Python functions have a 250 MB bundle limit, a short execution time, cold starts on every idle period, and no background jobs. The API needs ONNX Runtime, NumPy and scikit-learn in memory, scheduled clean-up jobs, and stable latency (NFR-01). A Docker container (on Render or a VPS) handles that. The frontend stays on Vercel.

### Why no PyTorch in production
Training uses PyTorch, but the server only runs exported ONNX models. That keeps the Docker image around 300 MB instead of 2 GB and inference fast on CPU.

---

## 2. Repository layout

```text
AI_based_Symptom_Checker/
├── client/                     React PWA → Vercel
│   ├── src/{components,pages,hooks,stores,services,types,i18n}/
│   ├── public/icons/           PWA icons
│   ├── vite.config.ts          PWA plugin + /api dev proxy
│   └── vercel.json             SPA fallback, /api rewrite, security headers
├── server/                     FastAPI → Docker image → Render or VPS
│   ├── app/
│   │   ├── main.py             app factory
│   │   ├── api/v1/             routers (HTTP only)
│   │   ├── core/               config, logging, errors, security utils
│   │   ├── middleware/         security headers, rate limits, request IDs
│   │   ├── schemas/            Pydantic API contracts
│   │   ├── services/           business logic: assessment/ ai/ prediction/ image/ privacy/
│   │   ├── repositories/       only layer that touches the DB session
│   │   ├── models/             SQLAlchemy ORM models
│   │   └── db/                 engine + session
│   ├── alembic/                migrations
│   ├── tests/{unit,integration}/
│   ├── Dockerfile
│   ├── pyproject.toml          ruff, mypy, pytest config
│   ├── requirements.txt        runtime deps (pinned)
│   └── requirements-dev.txt    test/lint deps
├── ml/                         training & evaluation, never deployed
│   ├── cv/                     skin-image model: configs/, train.py, export_onnx.py, notebooks/
│   ├── prediction/             condition model training
│   ├── nlp_eval/               extraction evaluation harness + cases
│   ├── datasets/               manifests + download scripts only, no raw data in git
│   ├── requirements.txt        full training deps (torch, timm, …)
│   └── requirements-ci.txt     light deps for CI tests
├── tests/e2e/                  Playwright
├── deploy/vps/                 VPS stack: docker-compose.prod.yml, Caddyfile, deploy.sh
├── render.yaml                 Render blueprint (image-backed services)
└── docs/
```

---

## 3. Deployment topology

```text
                      ┌──────────────────────────── Vercel ────────────────────────────┐
 User (browser / ───► │  React PWA (static)                                            │
 installed PWA)       │  /api/*  ──rewrite (same-origin proxy)──┐                      │
                      └─────────────────────────────────────────┼──────────────────────┘
                                                                ▼
                      ┌───────────── Render  or  VPS (Docker + Caddy) ─────────────────┐
                      │  FastAPI (Docker) — ONNX Runtime (CV + condition model)        │
                      │  /api/v1/health returns the deployed git SHA                   │
                      └──────────┬──────────────────────────┬──────────────────────────┘
                                 ▼                          ▼
                      Neon PostgreSQL              OpenAI API (via AiGateway)
                                 ▲
         Hugging Face Hub (model files, pinned revision) ──► downloaded at startup
```

**Same-origin API.** The frontend always calls relative `/api/...` URLs. Vercel rewrites them to the backend (Render or VPS), so there is no CORS setup and the auth cookie is first-party (cross-site cookies are blocked by Safari). Locally, the Vite dev server proxies `/api` to `http://localhost:8000`.

## 4. Environments

| Environment | Frontend | Backend | Database | Deployed when | Gate |
|---|---|---|---|---|---|
| Local | `npm run dev` :5173 | `uvicorn` :8000 | Docker Postgres | — | — |
| Preview | Vercel preview per PR (Vercel Git integration) | staging API | staging | every PR push | none |
| **Staging** | Vercel preview build of `develop` | image `:<sha>` on Render (`symptom-checker-api-staging`) or VPS | Neon `staging` branch | every merge to `develop` (after CI) | automatic |
| **Production** | Vercel production | image `:<sha>` on Render (`symptom-checker-api`) or VPS | Neon `main` branch | every merge to `main` (after CI) | **leader approves the deployment** |

Migrations run automatically at container start (`alembic upgrade head`). Migrations must be backward-compatible (add → migrate data → remove in a later release), so a rollback never breaks the database.

## 5. PWA rules (safety-critical)

- The service worker caches **only the app shell and static assets**. API responses use `NetworkOnly`, so health data is never cached on the device.
- Never store symptoms, messages or results in `localStorage`, `IndexedDB` or the Cache API. Only the assessment ID goes in `sessionStorage`.
- Offline screen: "You're offline. If this is an emergency, call **112**."
- A new version shows an "Update available" toast. No silent reloads mid-assessment.
- CI requires `dist/manifest.webmanifest` and `dist/sw.js` in the client build. Sprint 3 target: Lighthouse PWA and performance ≥ 90.

## 6. ML lifecycle (CV and condition model)

```text
datasets/ manifest + download script ──► ml/cv/train.py on Kaggle/Colab GPU (W&B logs)
     ──► evaluate on held-out test set (per-class + per-skin-tone metrics)
     ──► export_onnx.py (+ INT8 quantization) ──► parity test (PyTorch vs ONNX outputs)
     ──► push to Hugging Face Hub with model card (metrics, data, limits)
     ──► PR that bumps CV_MODEL_REVISION in server config ──► CI ──► staging ──► production
```

- **Candidate datasets:** Google SCIN (consumer phone photos of skin conditions), Fitzpatrick17k, DermNet. Check each licence before use and record it in `ml/datasets/README.md`.
- **Output classes:** a small set of common visible conditions **plus `unclear`**. The model abstains below a confidence threshold, and the chat continues with text only.
- **Size budget:** ≤ 25 MB per ONNX model, ≤ 1 s inference on a shared CPU, total RAM < 512 MB (so it fits Render's free tier; a VPS has headroom).
- Datasets, checkpoints and `.onnx` files are **never committed**. They live in Kaggle/Drive/HF Hub.
- CV output is **one more input** to the deterministic risk engine. It can raise the risk tier or add symptoms, but never lower the risk or diagnose on its own.

## 7. Environment variables (backend)

| Variable | Example | Notes |
|---|---|---|
| `APP_ENV` | `local` / `staging` / `production` | |
| `DATABASE_URL` | `postgresql+psycopg://…` | Neon connection string |
| `JWT_SECRET` | random 64 chars | Render generates it; on a VPS put it in the server `.env` |
| `AI_PROVIDER` / `AI_MODEL` / `OPENAI_API_KEY` | `openai` / (current small model) / `sk-…` | `mock` in local and CI |
| `CV_PROVIDER` / `CV_MODEL_REPO` / `CV_MODEL_REVISION` | `onnx` / `NT1906/skin-cv` / commit hash | `mock` in local and CI |
| `APP_VERSION` | git SHA, baked into the image (`--build-arg GIT_SHA`) | Returned by `/api/v1/health` so CD can confirm what was deployed, on any target |
| `PORT` | `8000` (Render sets its own) | Port Uvicorn listens on |

Frontend: nothing secret. Everything in the browser is public.
