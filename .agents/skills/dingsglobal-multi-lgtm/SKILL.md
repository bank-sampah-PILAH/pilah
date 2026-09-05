---
name: dingsglobal-multi-lgtm
description: Preflights, merges, and cleans up matching PILAH pull requests across pilah-be and pilah-mobile using parallel phases. Use when LGTM, merge, approve-and-merge, or cleanup targets the same branch in both repositories.
argument-hint: "<branch, PRs, or feature name> in <pilah-be|pilah-mobile> and <pilah-be|pilah-mobile>"
compatibility: Requires git, gh, and task delegation; intended for worktrees created by dingsglobal-multi-ship.
metadata:
  author: CommandCode
  version: "1.0"
---

# Merge Across PILAH Repositories

Follow the global `lgtm` safety rules for every selected pull request. This skill
coordinates readiness, parallel merge, and cleanup.

Example: `LGTM feature/update-auth in pilah-be and pilah-mobile` preflights
both PRs, then merges and cleans them up only after both are ready.

## 1. Resolve exact targets

- Use the workspace aliases from `AGENTS.md` and require both repositories to
  be explicit.
- Resolve one exact shared head branch plus one open PR and linked worktree in
  every selected repository. Ask if any target is ambiguous; never infer among
  multiple candidate PRs.
- Treat an explicit multi-project `LGTM` as authorization to merge and clean up
  all uniquely resolved targets.

## 2. Preflight every PR in parallel

Launch one read-only preflight worker per repository in one parallel tool call.
Each worker must perform the global `lgtm` checks and return the resolved PR
number, URL, head SHA, head branch, base branch, worktree path, and readiness:

- PR is open, not draft, approved, and mergeable;
- required checks are successful, not pending;
- current worktree is clean and matches the PR head branch;
- worktree path is inside that repository's `<repo>-worktrees` directory;
- primary checkout and repository baseline branch are identified; both
  repositories use `main`.
- Before removing a worktree, ensure any repository-specific runtime is stopped
  if one was started. Never remove a dirty worktree.

If any preflight fails, merge none. Report all blockers so readiness remains an
all-repository gate.

## 3. Merge and clean up in parallel

Only after every preflight passes, launch one merge worker per repository in a
single parallel tool call. Pin each worker to the preflighted PR number and head
SHA. Each worker must follow global `lgtm`: merge with repository policy,
confirm `MERGED`, delete and verify the remote branch, then remove the clean
linked worktree without force.

## 4. Handle partial runtime failure

The all-ready gate reduces partial merges but cannot make separate repositories
transactional. If a merge or cleanup command fails after execution begins:

- stop further commands for that repository;
- do not revert, close, force-push, or otherwise undo successful merges;
- collect the actual state of every PR, remote branch, and worktree;
- report exact manual follow-up required.

## 5. Report

Return one line per repository with PR URL, merge method and result, remote
branch deletion, and removed worktree path. Finish with an overall `complete`,
`blocked`, or `partial` status.
