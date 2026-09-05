---
name: dingsglobal-multi-ship
description: Coordinates one PILAH feature or fix across pilah-be and pilah-mobile with the same branch name, isolated sibling worktrees, parallel validation, pushes, and pull requests. Use with the global ship skill when a request starts with `ship` and names both repositories.
argument-hint: "<feature or fix prompt> in <pilah-be|pilah-mobile> and <pilah-be|pilah-mobile>"
compatibility: Requires git, gh, and task delegation; run from the PILAH workspace root.
metadata:
  author: CommandCode
  version: "1.0"
---

# Ship Across PILAH Repositories

Follow the global `ship` skill for each selected repository. This skill owns
cross-repository coordination and overrides only repository selection, shared
naming, preflight ordering, and parallel delegation.

Example: `ship update the auth contract in pilah-be and pilah-mobile` creates
the same derived branch in both repositories, with a separate worktree and PR
for each repository.

## 1. Resolve the request once

- Map aliases: `be|backend` -> `pilah-be` and `mobile|app` -> `pilah-mobile`.
- Require at least two repositories to be explicit. Ask one short question if
  the selection or repository-specific responsibility is ambiguous.
- Derive one `feature` or `fix` kind and one kebab-case `<name>` from the full
  request. Set the exact shared branch to `<kind>/<name>`.
- Split the request into repository-specific responsibilities. Establish any
  shared endpoint, payload, validation, authentication, or error contract before
  delegation so workers do not invent incompatible interfaces.

## 2. Preflight all repositories

Inspect all selected repositories concurrently before creating any worktree:

- resolve repository root, baseline branch, remote, and hosting provider;
- require a clean baseline checkout;
- fetch `origin/main` for both repositories;
- require both canonical checkouts to be on `main`, create each worktree from
  `origin/main`, and target `main` for each PR;
- require the exact shared branch and worktree path not to exist locally or
  remotely;
- read `AGENTS.md` and identify the documented setup and validation
  commands.

If any repository fails preflight, create no worktrees and report every
blocker. Never clean, stash, reset, delete, or rename existing work.

## 3. Delegate in parallel

Launch one general worker per repository in the same parallel tool call. Give
each worker:

- its absolute repository path and repository-specific responsibility;
- the full user request and agreed cross-repository contract;
- exact kind, name, branch, and expected worktree path;
- instructions to follow the global `ship` skill from worktree creation through
  PR creation without deriving a different name;
- instructions to copy the source repository's `.agents/` directory into
  the new worktree immediately after `git worktree add`, when it exists, before
  reading local instructions or starting implementation;
- instructions to read its project `AGENTS.md` and return PR URL,
  commits, checks, worktree path, and blockers.
- instructions to load the selected repository's local `ship` and `lgtm` skills.

The explicit multi-project request authorizes all named workers. Do not request
separate permission per repository. Do not let one worker modify another
repository.

The backend worker must use the documented Django test command. The mobile
worker must use the documented Flutter analyze and test commands. Do not
invent checks or report commands that could not run.

## 4. Coordinate outcomes

- Keep workers independent after the contract is fixed; do not serialize work
  merely because repositories share a branch name.
- If a worker discovers a contract change, pause affected work, reconcile it
  once, then resume with the same decision.
- Never claim all repositories shipped when one is blocked. Preserve successful
  PRs and worktrees; do not roll them back automatically.

## 5. Start The Integrated Runtime

Only after every selected repository has opened its PR, run any shared manual
verification requested by the repositories. No shared runtime coordinator is
defined for this workspace; use each repository's documented manual checks.

Workers must return worktree paths and manual verification results without
starting unrelated partial runtimes.

## 6. Report

Return one compact section per repository with branch, worktree, commits, PR,
validation, and manual verification. Finish with a combined status and clearly
identify partial completion or blockers.
