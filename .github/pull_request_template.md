<!--
  PR title : type(scope): short summary        e.g.  feat(chat): render message bubbles
  Branch   : <your-name>/<issue-no>-<short-desc> e.g.  vivek/12-chat-bubbles
  Base     : develop   (only the leader opens develop -> main release PRs)
  The "PR policy" check enforces all of this. See CONTRIBUTING.md.
-->

Closes #<issue-number>

## What changed
<!-- Bullet list of the concrete changes. -->

## Why
<!-- Which requirement / acceptance criterion this satisfies (e.g. FR-16, DR-02). -->

## How to test
<!-- Exact steps or commands a reviewer can run. -->

## Screenshots / API samples
<!-- Required for UI or API changes. Write "N/A" otherwise. -->

## Interface changes
<!-- Shared types, API routes, DB schema, env vars, prompts. Write "None" if nothing changed. -->

## Checklist
- [ ] This PR implements exactly one task (the linked issue) and nothing else
- [ ] I only changed files in my own module, or the owner agreed in the issue thread
- [ ] Every new or changed source file has a file header, and every exported function/class has a doc comment
- [ ] I added or updated tests, and lint, type-check and tests pass locally
- [ ] No secrets, `.env` files, real patient data or large binaries are committed
- [ ] User-facing text follows the medical-safety rules in AI_RULES.md §2 (or this PR has no user-facing text)
