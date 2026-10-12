# Security middleware

Owner: Harsh · Issue #47 · Task S1-HAR-1 · NFR-03.

`SecurityHeadersMiddleware(app, enable_hsts=False)` wraps an ASGI app and sets
nosniff, frame-denial, no-referrer and restricted browser permissions headers.
It preserves bodies, streaming and non-HTTP events. It does not inspect or log
request content. These headers belong to the API, not the frontend application.

Wrap the complete FastAPI app so generated 500 responses are covered too.
Vivek owns this app-factory integration. HSTS is opt-in and only emitted for an
HTTPS ASGI scope; trusted proxy configuration is a deployment responsibility.
The middleware does not trust forwarded headers itself or enable subdomain HSTS.

From `server/`, run `python -m pytest tests/unit/middleware -q`.

CORS policy is in `CORS.md`. Rate-limit decorators and the app-owner handoff
are in `INTEGRATION.md`. App integration is still pending under #47; isolated
tests do not establish that the deployed routes are protected.
