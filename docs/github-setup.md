# GitHub Setup & Leader Playbook

What is configured on `NT1906/AI_based_Symptom_Checker`, why, and what the leader does each sprint.

## 1. Repository configuration

| Setting | Value | Why |
|---|---|---|
| Default branch | `develop` | PRs target the integration branch by default |
| Merge methods | **Merge commit only** (squash and rebase disabled) | Keeps every member's individual commits in history, so contribution stats stay accurate |
| Auto-delete head branches | On | Merged feature branches are cleaned up |
| Secret scanning + push protection | On | Blocks pushes that contain API keys |
| Dependabot security updates | On | Automatic PRs for vulnerable dependencies |

## 2. Branch rulesets

Both `develop` and `main` have a ruleset (Settings → Rules → Rulesets):

- No direct pushes. All changes go through a pull request.
- No force-pushes, no branch deletion.
- 1 approving review, **from a code owner** (`.github/CODEOWNERS` → @NT1906), so every PR needs the leader's approval.
- Approvals are dismissed when new commits are pushed.
- All review conversations must be resolved.
- Required status checks: **`CI passed`** and **`PR policy`**.
- **Restrict updates:** only bypass actors can update the branch, so **only the leader can merge** (even after approval, teammates see the merge button disabled).
- **Bypass:** repository admin (the leader) with mode **always**. The leader can do anything, including merging their own PRs (GitHub doesn't let authors approve themselves) and emergency fixes. By team agreement the leader still opens PRs like everyone else.

## 3. Workflows (`.github/workflows/`)

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` → **CI passed** | PRs (and inside CD on every push) | Hygiene (secrets, `.env`, large files), file-header docs check, then lint/typecheck/test/build for `client/`, `server/` (FastAPI) and `ml/`. Each module job switches on automatically once its folder exists. |
| `pr-policy.yml` → **PR policy** | PR opened / edited / pushed | Branch naming and ownership, Conventional Commits, linked and assigned issue in a milestone, ticked checklist, **one open PR per member**. Runs the policy from the base branch, so a PR can't weaken it. |
| `contribution-report.yml` | Mondays 09:00 IST + manual | Commits and merged PRs per member since 10 Oct, flags anyone under 75% of the median |
| `cd.yml` → **CD** | Push to develop / main | Runs CI, builds the backend Docker image (GHCR), then deploys it to Render or a VPS plus the frontend to Vercel: develop → **staging** automatically, main → **production** after the leader approves. Details in §6. |
| Dependabot (`dependabot.yml`) | Weekly | Action updates now; npm/pip once the scaffolds exist (S0) |

## 4. Labels and milestones

- **Milestones:** `Sprint 0` (due 13 Oct), `Sprint 1` (27 Oct), `Sprint 2` (10 Nov), `Sprint 3` (20 Nov). Every issue must be in one (PR policy checks this).
- **Labels:** `type:*` (feature, bug, docs, test, chore), `area:*` (frontend, backend, ai, database, image, qa, security), `priority:*`, `status:blocked`, `out-of-scope`.

## 5. Leader routine

**Sprint planning (first day of the sprint)**
1. For each task in `docs/SPRINT_PLAN.md`, create an issue with the **Feature task** form, **assign the owner**, set the **sprint milestone** and the `area:` label.
2. Members start with their first task. The branch name is `<name>/<issue-no>-<desc>`.

**Daily**
- Review open PRs within 24 hours. Tag the module owner when a PR touches their interface.
- Use **Request changes** for problems. Approve only when the acceptance criteria are met and the code follows AI_RULES.md.
- Merge with **Create a merge commit**.

**Sprint review (last day)**
1. Demo from **staging** (it always runs the latest `develop`).
2. Open a PR `develop → main` titled `chore(release): sprint N`, and merge it.
3. Actions → CD → the run for `main` → **Review deployments → Approve** to release to production.
4. Tag the release: `git switch main && git pull && git tag v0.N.0 && git push origin v0.N.0`, then create a GitHub Release from the tag.
5. Run **Actions → Contribution Report → Run workflow**, check the balance, and move tasks between members if needed.

**Adding or replacing a member:** update `.github/team.json` (lowercase login → branch name) and `docs/rules.md` in a PR.

## 6. Continuous deployment (one-time setup)

Architecture and environments are in [tech-stack.md](tech-stack.md). The pipeline (`.github/workflows/cd.yml`) skips anything that isn't configured yet, so these steps can be done during Sprint 0/1 (task S1-RUT-4, with the leader).

1. **Database (Neon):** create a project with two branches, `main` (production) and `staging`. Copy both connection strings (`postgresql+psycopg://…`).
2. **Backend (Docker → Render or VPS):** follow [deployment.md](deployment.md): GHCR package access (§2), then either Render (§3) or a VPS (§4). Each GitHub environment gets `BACKEND_TARGET` (`render` or `vps`), `API_ORIGIN`, and that target's secrets.
3. **Frontend (Vercel):** import the repo, set **Root Directory = `client`**, framework Vite. `client/vercel.json` turns off Vercel's own deploys of `main`/`develop`; Actions does those, and Vercel still builds PR previews. In **Settings → Deployment Protection**, turn **off** Vercel Authentication for previews (teammates can't log in to a Hobby account). Create a token (Account → Tokens) and note the Org ID and Project ID (`vercel link` → `.vercel/project.json`).
4. **GitHub → Settings → Secrets and variables → Actions:**
   - Repository **secrets:** `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`
   - Repository **variables:** `STAGING_API_ORIGIN` = the staging API origin (the one committed in `client/vercel.json`); optional `IMAGE_PLATFORMS` for ARM servers
5. **GitHub → Settings → Environments:**
   - `staging`: deployment branches = `develop`; backend variables/secrets from step 2.
   - `production`: **required reviewer = NT1906**, deployment branches = `main`; backend variables/secrets from step 2.
6. Merge anything to `develop` and watch **Actions → CD**. The job summary shows the deployed URLs.

**Rollback:** see [deployment.md](deployment.md) §6. A VPS rolls back automatically when the new container is unhealthy.

**Demo day:** Render's free tier sleeps after 15 minutes idle (~50 s cold start). Upgrade the production service to Starter for the demo week, switch production to a VPS, or open the app a few minutes before presenting.

## 7. Re-applying the settings

The rulesets were created with the GitHub API. To inspect them:

```bash
gh api repos/NT1906/AI_based_Symptom_Checker/rulesets
```
