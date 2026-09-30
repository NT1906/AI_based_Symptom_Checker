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
- **Bypass:** repository admins (the leader), **only when merging a pull request**. This is how the leader merges their own PRs, which GitHub doesn't let the author approve. Rule for the leader: get a teammate (e.g. Rutva) to review your PR first, then merge with the bypass.

## 3. Workflows (`.github/workflows/`)

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` → **CI passed** | PRs and pushes to develop/main | Hygiene (secrets, `.env`, large files), file-header docs check, then lint/typecheck/test/build for `client/`, `server/` and `ai/`. Each module job switches on automatically once its folder exists. |
| `pr-policy.yml` → **PR policy** | PR opened / edited / pushed | Branch naming and ownership, Conventional Commits, linked and assigned issue in a milestone, ticked checklist, **one open PR per member**. Runs the policy from the base branch, so a PR can't weaken it. |
| `contribution-report.yml` | Mondays 09:00 IST + manual | Commits and merged PRs per member since 10 Oct, flags anyone under 75% of the median |
| Dependabot (`dependabot.yml`) | Weekly | Action updates now; npm/pip once the scaffolds exist (S0-RUT-1) |

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
1. Demo from `develop`.
2. Open a PR `develop → main` titled `chore(release): sprint N`, and merge it.
3. Tag the release: `git switch main && git pull && git tag v0.N.0 && git push origin v0.N.0`, then create a GitHub Release from the tag.
4. Run **Actions → Contribution Report → Run workflow**, check the balance, and move tasks between members if needed.

**Adding or replacing a member:** update `.github/team.json` (lowercase login → branch name) and `docs/rules.md` in a PR.

## 6. Re-applying the settings

The rulesets were created with the GitHub API. To inspect them:

```bash
gh api repos/NT1906/AI_based_Symptom_Checker/rulesets
```
