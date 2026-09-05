---
name: dingsglobal-ship
description: Backend-specific delivery rules for PILAH. Use with the global ship skill when shipping changes from pilah-be.
---

# PILAH Backend Ship Overlay

Use this overlay together with the global `ship` skill for `pilah-be`.

- Treat the canonical `pilah-be` checkout as the `main` baseline.
- Before creating a worktree, require the canonical checkout to be clean and on
  `main`.
- Fetch `origin/main` and create the new backend worktree from `origin/main`.
- Open the backend pull request with `main` as its base branch.
- Keep the derived feature or fix branch separate from `main`; never commit
  implementation work directly to the main checkout.
- Run the backend repository's documented validation before opening the PR.

Expected backend worktree creation shape:

```bash
git fetch origin main
git worktree add -b <kind>/<name> \
  ../pilah-be-worktrees/<kind>-<name> origin/main
```
