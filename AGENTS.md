# PILAH Workspace Instructions

## Repositories

- `be`, `backend`, and `pilah-be` mean `pilah-be`.
- `mobile`, `app`, and `pilah-mobile` mean `pilah-mobile`.
- `pilah-be` and `pilah-mobile` are Git submodules. Keep application changes
  inside the corresponding submodule; use this root repository for workspace
  wiring and shared agent configuration.
- Both application repositories use `main` as their baseline and PR target.

## Multi-repository delivery

- When a request begins with literal `ship` and names both repositories, load
  `dingsglobal-multi-ship` together with the global `ship` skill.
- Derive one change kind and kebab-case branch name, then use the same branch
  in sibling worktrees for both submodules.
- Validate, push, and open one PR per selected repository. Do not commit
  application changes to the root checkout or either canonical submodule
  checkout.

## Multi-repository merge

- When `LGTM`, merge, approve-and-merge, or cleanup names both repositories,
  load `dingsglobal-multi-lgtm` together with the global `lgtm` skill.
- Preflight every PR before merging any of them. Never remove a dirty worktree
  or undo a successful merge to compensate for another repository failing.

## Local validation

- Backend: follow `pilah-be/AGENTS.md` and its documented Django checks.
- Mobile: follow `pilah-mobile/AGENTS.md` and its documented Flutter checks.
- Do not commit credentials, generated runtime files, or local databases.
