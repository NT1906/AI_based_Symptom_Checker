# Security verification for #208

Owner: Harsh · S2-HAR-5 · NFR-03

The application factory installs the existing security headers and one app-owned
SlowAPI store. Auth POST routes (register, login, refresh and logout) share the
existing 10-per-minute client budget. Assessment routes share 60 per minute.
OPTIONS and health probes are excluded. Invalid payloads also consume quota.
The peer address determines quota; user-supplied forwarding headers do not.
Excess traffic returns 429 with Retry-After and no-store.

The store is per process. Use one worker until deployment configures shared
storage. Trusted reverse-proxy forwarding must be configured by deployment so
the app receives the intended peer address. Avoid shared client buckets at an
unconfigured proxy.

Security headers cover success, application errors and the generic 500 handler.
HSTS is enabled for HTTPS staging/production middleware responses. The existing
general 500 handler returns the baseline browser security headers.

## Local evidence

Tests use create_app and registered routes to verify separate shared quotas,
quota exhaustion before handler execution, app-instance isolation, forwarded
header spoofing, success/error headers and HTTPS staging HSTS.

From server, run:
python -m pytest tests/unit/middleware tests/unit/core -q

## Staging evidence still required

Record the actual staging API origin, deployed commit, effective worker/proxy
setup and measured response headers. Perform a controlled quota check with a
fictional request body and confirm 429 plus Retry-After. Tune the budgets only
after reviewing intended load and measured staging behaviour.

No staging verification or load-based tuning is claimed by this branch.
