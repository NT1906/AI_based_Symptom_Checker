# Security integration handoff — issue #47

Owner: Harsh · S1-HAR-1 · NFR-03.

## Current scope

Security headers, explicit CORS policy, and SlowAPI route decorators are tested
with a fictional FastAPI app. They are not yet attached to production routes.
Vivek owns `app/main.py`, `app/core/`, routers and the shared dependency files.
Those files are deliberately unchanged; obtain his agreement in issue #47 or
have him integrate the interfaces below. Do not mark #47 complete until the
real app and route integration is verified.

## Application construction

Create the FastAPI app, install one limiter, register decorated routes, then
wrap the completed app in CORS and security headers:

```python
from fastapi import FastAPI, Request, Response
from app.middleware.cors import CorsPolicy, configure_cors
from app.middleware.rate_limits import RateLimitPolicy, configure_rate_limits
from app.middleware.security_headers import SecurityHeadersMiddleware

api = FastAPI()
controls = configure_rate_limits(api, RateLimitPolicy())


# Illustrative route only. Vivek adds the decorator to each actual route.
@api.post("/api/v1/assessments")
@controls.assessment
async def example(request: Request, response: Response) -> dict[str, str]:
    return {"status": "ok"}


app = SecurityHeadersMiddleware(configure_cors(api, CorsPolicy()))
```

For router factories, pass the same `controls` object into each factory. Route
decorators must be above `@controls.assessment` / `@controls.auth`. Explicit
`request: Request` is required; include `response: Response` when returning a
dict or model so SlowAPI can add headers. Direct Response returns are supported.
All assessment routes share the assessment scope; all auth routes share auth.
Do not decorate health checks. CORS handles preflights before route execution.
No SlowAPI global middleware is necessary for these endpoint decorators.

Do not share the controls object across separately constructed app instances.
The tests use both sync and async handlers and verify budgets across different
assessment IDs and endpoint names. Real route coverage must be checked again
when Vivek's scaffold and routes are available.

## Defaults and limitations

- Proposed initial budgets: 60 assessment requests/minute and 10 auth
  requests/minute per ASGI client address, each shared across its route group.
  These are implementation defaults, not leader-approved deployment thresholds.
  Vivek should inject agreed values through the shared configuration.
- Fixed-window, in-memory storage: quotas reset on restart and are independent
  per worker/replica. Use one process for this initial setup; agree shared
  storage with deployment owners before scaling. No Redis dependency is added.
- Clients behind the same NAT share a budget. This is abuse mitigation, not
  account lockout or an authorization mechanism.
- Client identity comes from ASGI `request.client`, not forwarded HTTP headers.
  Deployment owners must restrict which proxies Uvicorn trusts. Otherwise all
  users may share a proxy address, or forged headers may affect the ASGI peer.
- SlowAPI's documented handler returns 429 JSON with an `error` string and
  `Retry-After`. Coordinate the final error schema with Vivek/Darshil; no shared
  API schema is introduced or changed here.
- SlowAPI normally reads .env/environment and logs raw client keys. The local
  adapter bypasses its config hook, supplies an empty packaged config file,
  and disables its dedicated logger. Operational exceptions still propagate;
  the API owner's central handler must return a safe error without traceback.
- CORS is empty by default for the Vite/Vercel same-origin proxy architecture.
  Only explicit origins may be enabled. See `CORS.md` for permitted headers.
- HSTS is opt-in on HTTPS scopes. The headers here protect API responses;
  frontend headers remain the frontend/deployment team's responsibility.

## Dependencies and verification

`requirements-local.txt` records the standalone Python 3.12 test environment.
Vivek should merge required runtime dependencies into the shared requirements;
this temporary file does not enable the currently skipped backend CI job.
The adapter is verified with SlowAPI 0.1.10. Re-run these tests on upgrades.

From `server/`:

```text
python -m pip install -r app/middleware/requirements-local.txt
python -m pytest tests/unit/middleware -q
python -m ruff check app/middleware tests/unit/middleware
python -m ruff format --check app/middleware tests/unit/middleware
python -m mypy --explicit-package-bases app/middleware
```

The namespace flag remains temporary until backend packaging is configured.
Shared CI commands (`mypy app`, `pytest`, migrations and Docker build) must also
pass after integration. Passing isolated tests does not verify deployment.
