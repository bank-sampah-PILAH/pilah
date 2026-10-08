---
name: sonarqube-cli
description: Use SonarQube CLI to inspect project issues and analyze local files. Use when a single- or multi-repository ship workflow detects `sonar`, or when the user requests Sonar CLI checks.
---

# SonarQube CLI

## Availability and project

- In the repository worktree, check `command -v sonar`. If it is missing, skip this optional check; never install or update the CLI.
- If present, run `sonar auth status --format json`. Continue only when `status` is `connected`. Never start an interactive login or request credentials; report unavailable auth and continue the ship workflow.
- Resolve the project key from local Sonar configuration (`.sonar-config.json`, `sonar-project.properties`, or `.sonarlint/`). If needed, query `sonar list projects --query <repo-name> --format toon` and choose an exact, unambiguous match. Do not guess a key. If unresolved, report the skipped check.

## Ship check

1. Record the current server-side issue inventory with `sonar list issues --project "$project_key" --format toon`. The default list contains `OPEN` and `CONFIRMED` issues. Use `--file <path>` to inspect issues on changed files and fix any that remain in the changed code. This inventory reflects the last project analysis, not uncommitted edits; it may remain unchanged until the project's normal Sonar scan.
2. Run `sonar analyze --file <path>` for each changed source file. This runs local secrets analysis and, when enabled for the account/project, Sonar's server-side Vortex analysis. Do not claim code-quality coverage if Vortex is unavailable.
3. Fix actionable findings in changed code, then rerun analysis on the affected files. Repeat until local analysis reports no findings. Treat Sonar's issue exit code (currently `51`) as findings to remediate. On other command errors, stop Sonar checks, report the unavailable check, and continue other ship validation.
4. Keep unrelated existing project issues out of scope. Report their presence, but do not expand the change to clear the project backlog. If a finding in changed code cannot be resolved safely, report it as a blocker rather than suppressing it.

Do not change issue statuses or project settings through the CLI. Report the project key, local analysis result, Vortex coverage (if any), and any skipped checks or unrelated existing issues.

Command reference: https://docs.sonarsource.com/sonarqube-cli/using-sonarqube-cli/commands/
