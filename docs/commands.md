# Command Cheat Sheet

Every command you need, in the order you need it. Keep this open while you work.
Replace `<name>` with your team name (`vivek`, `kavya`, …) and `<N>` with your issue number.

> The run/test commands work once the Sprint 0 scaffolds (`server/`, `client/`, `docker-compose.yml`) are merged.
> **Windows:** use Git Bash or WSL. Where a command differs, the Windows version is shown as `# Win:`.

---

## 1. One-time setup (first day only)

```bash
# Tools you need installed: Git, Python 3.12, Node.js 20, Docker Desktop, GitHub CLI (gh, optional)
git --version && python3.12 --version && node --version && docker --version

# Accept the collaborator invite first (github.com/notifications), then:
git clone https://github.com/NT1906/AI_based_Symptom_Checker.git
cd AI_based_Symptom_Checker

# Your identity. The email MUST be verified on your GitHub account, or your commits won't count.
git config user.name  "Your Name"
git config user.email "you@example.com"
git config pull.rebase false          # "git pull" merges (no surprise rebases)
git config push.autoSetupRemote true  # first push of a branch sets upstream automatically

# Optional: log in to GitHub CLI (lets you create PRs from the terminal)
gh auth login

# Environment file (local only, never committed). Defaults use mock AI/CV, so no API keys needed.
cp .env.example .env

# Backend virtual environment
cd server
python3.12 -m venv .venv
source .venv/bin/activate             # Win: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cd ..

# Frontend dependencies
cd client && npm ci && cd ..
```

---

## 2. EVERY TIME you start working

```bash
cd AI_based_Symptom_Checker

# 1. Get the latest code
git switch develop
git pull origin develop

# 2. Go to your task branch
#    New task:       create it from the fresh develop
git switch -c <name>/<N>-short-description        # e.g. vivek/12-chat-bubbles
#    Continuing:     switch to it and bring in the latest develop
git switch <name>/<N>-short-description
git merge develop                                  # fix conflicts if any (see §6)

# 3. Refresh dependencies (someone may have added packages)
cd server && source .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt && cd ..
cd client && npm ci && cd ..

# 4. Start the database and apply migrations
docker compose up -d db
cd server && alembic upgrade head && cd ..
```

**Before your first commit of the day:** check you are on your branch, not `develop`:

```bash
git branch --show-current      # must print <name>/<N>-...
```

---

## 3. Running the project locally

Use **three terminals**:

```bash
# Terminal 1: database (skip if already running)
docker compose up -d db

# Terminal 2: backend  → http://localhost:8000/docs (interactive API docs)
cd server && source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 3: frontend → http://localhost:5173 (calls /api, proxied to :8000)
cd client
npm run dev
```

**Or run the whole backend in Docker** (the same image that gets deployed):

```bash
docker compose up --build          # db + api; Ctrl+C to stop
docker compose down                # stop and remove containers (data is kept)
docker compose down -v             # also DELETE the local database. Careful.
```

Useful extras:

```bash
cd client && npm run gen:api               # regenerate TS types after backend API changes (backend must be running)
cd server && python -m app.scripts.seed    # load demo data (exact command defined in S0-HAR-1)
docker compose logs -f db                  # database logs
cd client && npm run build && npm run preview   # test the PWA build (install prompt, offline) at :4173
```

---

## 4. Before you commit / push: run the same checks as CI

```bash
# Backend (from server/, venv active)
ruff check . --fix         # lint and auto-fix
ruff format .              # format
mypy app                   # type check
pytest                     # tests
pytest tests/unit/prediction -k risk -v    # run only some tests

# Frontend (from client/)
npm run lint
npm run typecheck
npm test
npm run build

# ML code (from ml/)
ruff check . && pytest

# Backend Docker image builds? (from server/)
docker build -t symptom-checker-api:local .
```

If CI fails on your PR, run these locally, fix, commit, push.

---

## 5. Git: the full task cycle

```bash
# See what changed
git status
git diff                         # unstaged changes
git diff --staged                # what you're about to commit

# Commit in small logical steps (3+ commits per task)
git add server/app/services/prediction/risk_engine.py
git commit -m "feat(risk): add red-flag override to risk engine"
git add server/tests/unit/prediction/test_risk_engine.py
git commit -m "test(risk): cover every red-flag rule"

# Push (first push creates the branch on GitHub)
git push

# Open the PR into develop (or use the GitHub website)
gh pr create --base develop --fill
#   → fill in the template, keep "Closes #<N>", tick the checklist

# Check PR status and CI
gh pr status
gh pr checks

# Address review comments: edit, commit, push. The PR updates automatically.
git add . && git commit -m "fix(risk): handle empty symptom list" && git push

# After the leader merges: clean up and start the next task
git switch develop
git pull origin develop
git branch -d <name>/<N>-short-description     # delete local branch (remote is auto-deleted)
git fetch --prune                              # forget deleted remote branches
```

**Commit message format:** `type(scope): what you did`
Types: `feat` `fix` `test` `docs` `refactor` `style` `perf` `build` `ci` `chore`. Details in [CONTRIBUTING.md](../CONTRIBUTING.md#commit-messages).

---

## 6. Git: fixing common situations

```bash
# Merge conflict after "git merge develop"
git status                       # lists conflicted files
#   open each file, keep the right code, delete the <<<<<<< ======= >>>>>>> markers
git add <file>
git commit                       # completes the merge
git push

# Wrong last commit message (not pushed yet)
git commit --amend -m "feat(chat): correct message"

# Wrong commit message ALREADY pushed (only on YOUR branch)
git commit --amend -m "feat(chat): correct message"
git push --force-with-lease      # never on develop/main

# Fix several bad commit messages on your branch
git rebase -i develop            # change "pick" to "reword", save, edit messages
git push --force-with-lease

# Forgot a file in the last commit (not pushed)
git add forgotten_file.py
git commit --amend --no-edit

# Made changes on develop by mistake (not committed)
git stash
git switch -c <name>/<N>-short-description
git stash pop

# Committed on develop by mistake (not pushed)
git branch <name>/<N>-short-description   # save the commit on a new branch
git reset --hard origin/develop           # put local develop back
git switch <name>/<N>-short-description

# Put work aside to switch tasks or pull
git stash push -m "wip chat bubbles"
git stash list
git stash pop

# Throw away uncommitted changes to one file
git restore path/to/file

# Undo the last commit but keep the changes (not pushed)
git reset --soft HEAD~1

# Undo a commit that is already pushed (safe: adds a new "revert" commit)
git revert <commit-sha>

# See history
git log --oneline --graph -15
git log --oneline develop..HEAD           # commits on your branch not yet in develop

# Accidentally committed a secret / .env
#   STOP. Tell the leader immediately, rotate the key. Do not just delete it in a new commit.
```

---

## 7. When you stop for the day

```bash
git status                       # nothing important left uncommitted?
git add <files> && git commit -m "feat(scope): work in progress on X"   # only if it's a real step
git push                         # your work is backed up on GitHub
docker compose stop              # stop the database (data is kept)
deactivate                       # leave the Python venv
```

---

## 8. ML work (Mann, Nisarg, Mohit)

```bash
cd ml
python3.12 -m venv .venv && source .venv/bin/activate      # separate venv, heavy deps
pip install -r requirements.txt
python cv/train.py --config cv/configs/baseline.yaml        # local smoke run; real training on Kaggle/Colab GPU
python cv/export_onnx.py --checkpoint <path> --out artifacts/model.onnx
python nlp_eval/evaluate.py                                  # NLP extraction evaluation
```

Never commit datasets, checkpoints or `.onnx` files. They are git-ignored. Models go to Hugging Face Hub.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `port 5432 already in use` | Another Postgres is running: `docker ps`, stop it, or stop your local Postgres service |
| `port 8000 / 5173 already in use` | `lsof -i :8000` then `kill <pid>` (Win: `netstat -ano \| findstr :8000`, `taskkill /PID <pid> /F`) |
| `ModuleNotFoundError` in backend | venv not active (`source server/.venv/bin/activate`) or run `pip install -r requirements.txt -r requirements-dev.txt` |
| DB errors after pulling | `cd server && alembic upgrade head` |
| Frontend API types out of date | Backend running, then `cd client && npm run gen:api` |
| Weird frontend errors after pulling | `cd client && rm -rf node_modules && npm ci` |
| PWA shows old version | DevTools → Application → Service Workers → Unregister, then hard reload |
| PR check "PR policy" failed | Open the check → Summary lists exactly what to fix |
| Push rejected on `develop`/`main` | Correct: nobody pushes there. Push your branch and open a PR |
| `Permission denied (publickey)` | Use the HTTPS clone URL, or add your SSH key on GitHub |
