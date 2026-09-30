# Backend Deployment: Docker on a Platform or a VPS

The backend ships as **one Docker image per commit**. CD builds it once, pushes it to the GitHub Container Registry (GHCR), and then deploys that **same image** to whichever target the environment uses:

| Target | `BACKEND_TARGET` | Good for | Cost |
|---|---|---|---|
| **Render** (managed platform) | `render` (default) | Zero server maintenance, HTTPS and logs included | Free tier (sleeps when idle); Starter for demo week |
| **VPS** (any Linux server with Docker) | `vps` | Full control, no cold starts, more RAM for ML models, self-hosted Postgres possible | ~₹400–1000/month (Hetzner, DigitalOcean, Lightsail, Oracle Cloud free ARM) |

Staging and production choose independently. For example, staging on Render and production on a VPS. Switching is a one-variable change (§5). No code changes needed.

```text
push ─► CI ─► build image ghcr.io/nt1906/symptom-checker-api:<sha>  (+ :develop / :main)
                 │
                 ├─ BACKEND_TARGET=render ─► Render deploy hook (imgURL=<sha image>)
                 └─ BACKEND_TARGET=vps    ─► scp deploy/vps/* + ssh deploy.sh <sha image>
                 │
                 ▼
        wait until GET /api/v1/health → {"version": "<sha>"}  ─► tag image :staging / :production
```

---

## 1. Image contract (what `server/Dockerfile` must satisfy)

`server/Dockerfile` is written in task **S0-RUT-1**. Whatever it looks like, it must:

1. Accept build arg `GIT_SHA` and expose it as env `APP_VERSION`. `GET /api/v1/health` returns `{"status": "ok", "version": APP_VERSION}`. CD uses this to confirm the new version is live on **any** target.
2. Listen on `${PORT:-8000}` (Render sets `PORT`; the VPS uses 8000).
3. Run as a non-root user, with no build tools or dev dependencies in the final image, and **no PyTorch** (only ONNX Runtime).
4. Run `alembic upgrade head` before starting Uvicorn. Migrations must be backward-compatible (expand → migrate → contract) so a rollback never breaks the DB.
5. Stay small (target < 500 MB) and start in < 40 s. Read all config from env vars, bake no secrets in.
6. Have a `.dockerignore` (`.venv`, `tests`, `__pycache__`, `.env*`, `*.onnx`, …).

Reference implementation:

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim
ARG GIT_SHA=dev
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_VERSION=${GIT_SHA} PORT=8000
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY --chown=app:app . .
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/api/v1/health', timeout=4)"
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
```

Test locally:

```bash
cd server
docker build --build-arg GIT_SHA=$(git rev-parse HEAD) -t symptom-checker-api:local .
docker run --rm -p 8000:8000 --env-file ../.env symptom-checker-api:local
curl localhost:8000/api/v1/health
```

CI runs `docker build` on every PR (the "Server" job), so a broken Dockerfile never reaches `develop`.

---

## 2. Image registry (GHCR), one-time

After the first CD run that finds `server/Dockerfile`, the package `symptom-checker-api` appears under **github.com/NT1906 → Packages**.
- Package settings → **Manage Actions access** → add this repository with **Write** (lets CD retag images).
- Choose one:
  - **Public package** (simplest; the image contains no secrets), or
  - keep it private and give Render/VPS a GitHub **PAT with only `read:packages`**.

Tags: `:<sha>` is immutable and is what gets deployed. `:develop` / `:main` are the latest builds. `:staging` / `:production` are the last **verified** deploys, and serve as rollback reference points.

---

## 3. Target A: Render (default)

1. Create the Neon database (branches `main` and `staging`).
2. Render → **Settings → Registry Credentials**: add `ghcr` (username `NT1906`, the `read:packages` PAT). Skip if the package is public.
3. Render → **New → Blueprint** → this repo. `render.yaml` creates `symptom-checker-api-staging` and `symptom-checker-api` as **image-backed** services. Fill the `sync: false` env vars.
4. For each service, copy **Settings → Deploy Hook** and the service URL.
5. GitHub → **Settings → Environments** → `staging` / `production`:
   - variable `BACKEND_TARGET` = `render`
   - variable `API_ORIGIN` = the service URL (e.g. `https://symptom-checker-api-staging.onrender.com`)
   - secret `RENDER_DEPLOY_HOOK_URL` = the deploy hook

CD calls the hook with `imgURL=<exact sha image>`, so Render runs exactly the commit that passed CI.

---

## 4. Target B: VPS

Any Ubuntu 22.04/24.04 server with ≥ 1 vCPU / 2 GB RAM (4 GB if you self-host Postgres). Files in [`deploy/vps/`](../deploy/vps/):

| File | Purpose |
|---|---|
| `docker-compose.prod.yml` | `api` (the image) + `caddy` (HTTPS reverse proxy) + optional `db` (Postgres, profile `local-db`) |
| `Caddyfile` | Automatic Let's Encrypt certificate for `API_DOMAIN`, gzip, security headers |
| `deploy.sh` | Pull image → restart → wait for health → **automatic rollback** to the last healthy image on failure |
| `.env.example` | Template for the server-side `.env` (secrets live only on the server) |

### 4.1 One-time server setup (leader or Rutva)

```bash
# On the VPS as root
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh                     # Docker Engine + compose plugin
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
mkdir -p /opt/symptom-checker && chown deploy:deploy /opt/symptom-checker
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
# Harden SSH: in /etc/ssh/sshd_config set PasswordAuthentication no, PermitRootLogin no; then: systemctl restart ssh
```

```bash
# On your laptop: create a deploy-only key pair and install it for the deploy user
ssh-keygen -t ed25519 -f ./vps_deploy_key -C "github-actions-deploy" -N ""
ssh-copy-id -i ./vps_deploy_key.pub deploy@<VPS_IP>
ssh-keyscan -t ed25519 <VPS_IP>          # output = VPS_KNOWN_HOSTS secret
```

```bash
# On the VPS as deploy
cd /opt/symptom-checker
nano .env                                  # fill in from deploy/vps/.env.example
chmod 600 .env
echo <read:packages PAT> | docker login ghcr.io -u NT1906 --password-stdin   # only if the package is private
```

**Domain:** point an A record (e.g. `api.yourdomain.com`) at the VPS IP. With no domain, use `<ip-with-dashes>.sslip.io` (e.g. `203-0-113-7.sslip.io`), which Let's Encrypt accepts. Put it in `.env` as `API_DOMAIN`.

**Database:** keep Neon (`DATABASE_URL` → Neon), or self-host: set `POSTGRES_PASSWORD`, point `DATABASE_URL` at `postgresql+psycopg://symptom_checker:<pw>@db:5432/symptom_checker`, and run `docker compose -f docker-compose.prod.yml --profile local-db up -d db` once. Self-hosted DB means **you** own backups (task S3-HAR-2).

### 4.2 Connect CD

GitHub → **Settings → Environments** → `staging` or `production`:

| Kind | Name | Value |
|---|---|---|
| variable | `BACKEND_TARGET` | `vps` |
| variable | `API_ORIGIN` | `https://<API_DOMAIN>` |
| variable | `VPS_APP_DIR` | `/opt/symptom-checker` (default, optional) |
| secret | `VPS_HOST` | server IP or hostname |
| secret | `VPS_USER` | `deploy` |
| secret | `VPS_SSH_KEY` | contents of `vps_deploy_key` (private key) |
| secret | `VPS_KNOWN_HOSTS` | output of `ssh-keyscan` (pins the host key) |

Using an ARM server (e.g. Oracle free tier, Hetzner CAX)? Set the **repository** variable `IMAGE_PLATFORMS` = `linux/amd64,linux/arm64`.

One VPS can host both environments: use two folders (`/opt/symptom-checker-staging`, `/opt/symptom-checker`), different `API_DOMAIN`s, and a different compose project name per folder (`COMPOSE_PROJECT_NAME` in each `.env`). Change `container_name` in a copy of the compose file, or keep one environment per VPS (simpler).

---

## 5. Switching targets

1. Set up the new target (§3 or §4) while the old one keeps serving traffic.
2. Change the environment variables `BACKEND_TARGET` and `API_ORIGIN` (and add that target's secrets).
3. Re-run the latest CD run for that branch (Actions → CD → **Re-run all jobs**). It deploys the same image to the new target and repoints the Vercel `/api` proxy.
4. Once it's healthy, stop the old target.

---

## 6. Rollback

| Target | How |
|---|---|
| Render | Service → Events → previous deploy → **Rollback** |
| VPS | Automatic if the new container is unhealthy. Manual: `ssh deploy@host '/opt/symptom-checker/deploy.sh ghcr.io/nt1906/symptom-checker-api:<older-sha>'` |
| Either | Revert the bad commit with a PR. CD redeploys the fixed version. |
| Frontend | Vercel → Deployments → previous production deployment → **Promote to Production** |

## 7. Operations checklist (VPS)

- `docker compose -f docker-compose.prod.yml ps` / `logs -f api`: status and logs
- Security updates: `unattended-upgrades` enabled; reboot monthly
- Disk: `docker system df`; `deploy.sh` prunes old images after each successful deploy
- Monitoring: UptimeRobot on `https://<API_DOMAIN>/api/v1/health` (task S3-RUT-1)
