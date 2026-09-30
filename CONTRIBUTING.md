# Contributing: Team Workflow

Every team member follows this workflow for every task. GitHub enforces most of it automatically, so if a check fails, read its message and fix what it says.

**Read first:** [AI_RULES.md](AI_RULES.md) (code rules; they apply to humans too) · [docs/rules.md](docs/rules.md) (ownership) · [docs/SPRINT_PLAN.md](docs/SPRINT_PLAN.md) (your tasks).

---

## The rules in one screen

1. **One feature at a time.** You may have **one open PR**. Finish it and get it merged before opening the next.
2. **Your own branch only:** `<your-name>/<issue-no>-<short-desc>`, created from `develop`.
3. **Every PR targets `develop`** and closes exactly one issue that is assigned to you.
4. **Only the team leader (@NT1906) approves and merges.** Nobody pushes to `develop` or `main` directly.
5. **Commits and PR titles use Conventional Commits:** `feat(chat): add typing indicator`.
6. **Commit regularly:** at least 3 meaningful commits per PR. Padding commits are rejected.
7. **Stay in your module.** Need a change in someone else's area? Ask in the issue.
8. **Document your code:** a file header in every file, and doc comments on everything you export (see AI_RULES.md §5).
9. **Using an AI assistant?** Point it at `AI_RULES.md` first. You are responsible for everything it writes.

---

## Branches

```text
main        ← stable releases only. Leader merges develop → main at the end of each sprint.
develop     ← integration branch (default). All feature PRs go here.
<name>/<issue>-<desc>   ← your working branch, e.g. vivek/12-chat-bubbles
```

Team names for branch prefixes: `nisarg` `rutva` `harsh` `kavya` `nishith` `vivek` `darshil` `mann` `mohit` `dimple`.

---

## One-time setup

```bash
# 1. Accept the collaborator invite (GitHub email / github.com/notifications)
# 2. Clone
git clone https://github.com/NT1906/AI_based_Symptom_Checker.git
cd AI_based_Symptom_Checker

# 3. Use the SAME email as your GitHub account, or your commits won't count toward your stats
git config user.name  "Your Name"
git config user.email "you@example.com"   # must be verified on github.com/settings/emails
```

---

## Doing a task, step by step

```bash
# 0. Pick your next issue: it is assigned to you, in the current sprint milestone.
#    Say "starting" in the issue so the team knows.

# 1. Start from the latest develop
git switch develop
git pull origin develop
git switch -c vivek/12-chat-bubbles

# 2. Work in small steps. Commit each logical step.
git add client/src/components/chat/MessageBubble.tsx
git commit -m "feat(chat): add MessageBubble component"
git add client/src/components/chat/MessageBubble.test.tsx
git commit -m "test(chat): cover own vs bot message alignment"

# 3. Run the checks locally (in client/ or server/)
npm run lint && npm run typecheck && npm test

# 4. Push and open a PR into develop
git push -u origin vivek/12-chat-bubbles
gh pr create --base develop --fill   # or use the GitHub web UI
```

Then fill in **every** section of the PR template and make sure it contains `Closes #12`.

**While the PR is in review:**
- Reply to every review comment, and push fixes as new commits (don't force-push).
- If `develop` moved on and you have conflicts: `git fetch origin && git merge origin/develop`, fix the conflicts, commit, push.
- When the leader merges, the branch is deleted automatically and the issue closes.

**Then start the next task:**
```bash
git switch develop && git pull origin develop
git switch -c vivek/15-typing-indicator
```

---

## Commit messages

```text
type(scope): summary in imperative mood, ≤ 72 chars, no full stop

Optional body: what and why, wrapped at 72 chars.

Refs: #12
```

| type | use for |
|---|---|
| `feat` | new functionality |
| `fix` | bug fix |
| `test` | adding or fixing tests |
| `docs` | documentation only |
| `refactor` | code change without behaviour change |
| `style` | formatting only |
| `perf` | performance |
| `build` / `ci` / `chore` | tooling, CI, housekeeping |

Scopes: `chat` `ui` `result` `assessment` `ai` `prediction` `risk` `image` `db` `api` `auth` `security` `privacy` `test` `ci` `docs`.

Fix a bad commit message on your own branch with `git commit --amend` (latest commit) or `git rebase -i origin/develop`, then `git push --force-with-lease`. This is allowed only on **your own** feature branch.

---

## Automated checks on your PR

| Check | What it verifies | How to fix |
|---|---|---|
| **PR policy** | branch name, author owns the branch, PR title and commit format, `Closes #N` matches the branch, issue is assigned to you and has a milestone, checklist fully ticked, no other open PR by you | Follow the error list in the job summary. Edit the PR title/body, or amend commits. The check re-runs automatically. |
| **CI passed** | no secrets / `.env` / large files; file headers on changed source files; lint, typecheck, tests and build for `client/`, `server/`, `ai/` | Run the same commands locally and fix them |

Both checks must be green **and** the leader must approve before the PR can merge.

If "PR policy" failed only because your previous PR was still open, re-run it after that PR is merged (Actions tab → the failed run → **Re-run jobs**), or push a commit.

---

## Required npm scripts (for the Sprint 0 scaffolds)

CI runs these, so `client/package.json` and `server/package.json` must define them:

| Script | client | server |
|---|---|---|
| `lint` | `eslint .` (with `eslint-plugin-jsdoc`, `publicOnly` for exported functions) | same |
| `typecheck` | `tsc --noEmit` | same |
| `test` | `vitest run` | `vitest run` |
| `build` | `vite build` | — |

Commit `package-lock.json`. The Python code in `ai/` needs `requirements.txt` and passes `ruff check .` and `pytest`.

---

## When you're blocked

1. Mock the missing dependency and keep going (docs/rules.md, Rule 2).
2. Comment on your issue, tag the person you're waiting on, and add the `status:blocked` label.
3. Still blocked after 4 hours? Tell the team channel and the leader.

## Reporting bugs

Open a **Bug report** issue. The leader assigns it to the module owner, and it's handled as that person's next task.
