#!/usr/bin/env bash
# @file Repository hygiene gate, run by .github/workflows/ci.yml.
# Fails the build when the tracked tree contains things that must never be committed:
# .env files, node_modules, files over 5 MB, or strings that look like API keys / private keys.
set -euo pipefail

fail=0
MAX_BYTES=$((5 * 1024 * 1024))

# 1. Environment files (only .env.example templates are allowed).
envs=$(git ls-files | grep -E '(^|/)\.env($|\.)' | grep -vE '\.env\.example$' || true)
if [[ -n "$envs" ]]; then
  echo "::error::Committed .env file(s). Remove them and rotate any secrets inside:"; echo "$envs"; fail=1
fi

# 2. Dependency folders.
if git ls-files | grep -qE '(^|/)(node_modules|\.venv|venv|__pycache__)/'; then
  echo "::error::node_modules / virtualenv / __pycache__ is committed. Add it to .gitignore and git rm -r --cached it."; fail=1
fi

# 3. Large files.
while IFS= read -r f; do
  [[ -f "$f" ]] || continue
  size=$(wc -c < "$f")
  if (( size > MAX_BYTES )); then
    echo "::error file=$f::File is $((size / 1024 / 1024)) MB (limit 5 MB). Keep datasets/models out of git."; fail=1
  fi
done < <(git ls-files)

# 4. Secret-looking strings (OpenAI, Google, AWS, GitHub tokens, private keys).
pattern='((^|[^A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'
hits=$(git ls-files | grep -v '^.github/scripts/check-hygiene.sh$' | xargs -r grep -EIn "$pattern" 2>/dev/null || true)
if [[ -n "$hits" ]]; then
  echo "::error::Possible secret(s) committed. Remove them, rotate the key, and tell the leader:"
  echo "$hits" | cut -c1-160; fail=1
fi

if (( fail )); then exit 1; fi
echo "Repository hygiene OK."
