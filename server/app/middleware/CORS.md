# CORS policy (S1-HAR-1, issue #47)

`CorsPolicy` validates an exact list of HTTP(S) origins. `configure_cors(app,
policy)` wraps the complete application so generated error responses receive
CORS headers too. No environment variables are read in this module.

The default origin list is empty. Vite and Vercel proxy `/api` on the same
origin, so the standard project architecture does not need cross-origin
permissions. If direct browser access is needed, Vivek supplies exact origins
from shared configuration and explicitly opts into credentials if required.
Wildcards, origin regexes, URL credentials and paths are not accepted.

Integration order, outside to inside:

```python
app = SecurityHeadersMiddleware(configure_cors(fastapi_app, policy))
```

Vivek owns changes to `main.py` and `core/config.py`. This module introduces no
new environment variable names or changes to those files. Configuration and
application integration still require coordination with him.

Allowed methods are GET, HEAD, POST, PUT, PATCH, DELETE and OPTIONS. In addition
to CORS-safelisted headers, Content-Type, X-CSRF-Token and X-Request-ID are
allowed; X-Request-ID and Retry-After are exposed to trusted browsers. Reconcile
these names with the API owner before integration. Preflights cache for 600 s.

CORS controls browser response access; it is not authentication or CSRF
protection. An unapproved simple request can still reach a route, but the
browser cannot read its response. Route authorization and CSRF remain separate.

Run from `server/`: `python -m pytest tests/unit/middleware -q`.
Rate-limit controls are documented in `INTEGRATION.md`. App integration
remains pending; issue #47 is not complete.
