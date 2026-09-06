---
name: dingsglobal-ship
description: Backend-specific delivery rules for PILAH. Use with the global ship skill when shipping changes from pilah-be.
---

# PILAH Backend Ship Overlay

Use this overlay together with the global `ship` skill for `pilah-be`.

- Treat `staging` as the default backend worktree baseline and pull request
  target. Honor an explicitly named checkout/base or target branch instead.
- Keep the canonical `pilah-be` checkout clean and on `main`.
- Before creating a worktree, require the canonical checkout to be clean and on
  `main`.
- Fetch `origin/<baseline_branch>` and create the new backend worktree from
  `origin/<baseline_branch>`.
- Open the backend pull request with `<target_branch>` as its base branch.
- Keep the derived feature or fix branch separate from `main`; never commit
  implementation work directly to the main checkout.
- Run the backend repository's documented validation before opening the PR.

Expected backend worktree creation shape:

```bash
git fetch origin <baseline_branch>
git worktree add -b <kind>/<name> \
  ../pilah-be-worktrees/<kind>-<name> origin/<baseline_branch>
```
