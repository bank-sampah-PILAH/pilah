---
name: ask-for-qa
description: Request QA on an existing GitHub pull request, assign a mapped QA reviewer, and post an exact Discord webhook notification with change and verification bullets. Use when the user says "ask for QA", "request QA", "ping <name> for QA", or asks to notify Discord about PR testing.
metadata:
  requires:
    bins: ["gh", "python3"]
---

# Ask for QA

This skill operates on an **existing GitHub pull request**. It assigns one
mapped QA reviewer, then sends the Discord notification with concise changes and
verification steps. It does not create a PR.

## Preconditions

- Run in the repository containing the PR, or pass the PR URL with `--pr`.
- Before doing anything, verify `gh` exists (`command -v gh`), print
  `gh --version`, and run `gh auth status`. If it is missing, stop and tell the
  user to install GitHub CLI from <https://cli.github.com/>. If it is not
  authenticated, stop and ask the user to run `gh auth login`.
- Require `DISCORD_QA_WEBHOOK_URL` in the environment or the nearest
  repository `.env` file. The workspace root `.env` is gitignored. Never print
  the webhook URL or copy it into logs, messages, or project files.

## Known identities

Match the requested QA person by GitHub login (case-insensitive). The Discord
username is accepted as an alias, but GitHub assignment always uses the GitHub
login.

| GitHub | Discord ID | Discord username |
| --- | --- | --- |
| `TrayMachi` | `336112760255414284` | `traymachi` |
| `alghani46` | `710341591910580226` | `baller3839` |
| `HeraldoArman` | `539004236441190401` | `dooo78` |
| `Twentism` | `764158279957348432` | `twentism_` |
| `Scallss` | `376340393480159232` | `scalss` |
| `mvfi0` | `467854943068356608` | `vegardthemagicalcheesewizard` |

If the QA person is missing or not in this table, ask for a supported GitHub
login. Do not guess or assign an unmapped person. The authenticated GitHub user
must also be in the table because they are the message sender.

## Workflow

1. Parse exactly one QA person from the request. Use the current branch's PR
   unless the user supplied a PR URL or number.
2. Inspect the PR description, commits, changed files, and documented testing.
   Write concise, factual bullets: one or more `--change` bullets describing
   what changed, and one or more `--step` bullets describing how QA can verify
   it. Do not invent behavior or verification steps.
3. Run the bundled helper. Use `--area MOB` for `pilah-mobile` and `--area BE`
   for `pilah-be` only when repository-name detection cannot determine it:

   ```bash
   workspace_root="$(git rev-parse --show-superproject-working-tree)"
   [ -n "$workspace_root" ] || workspace_root="$(git rev-parse --show-toplevel)"
   python3 "$workspace_root/.agents/skills/ask-for-qa/scripts/ask_for_qa.py" \
     --qa <github-login-or-discord-username> \
     --change "<what changed>" --step "<how to verify>" \
     [--change "<another change>"] [--step "<another step>"] \
     [--pr <url-or-number>] [--area MOB|BE]
   ```

   Use `--dry-run` to inspect the payload without changing GitHub or sending
   Discord.
4. The helper validates `gh`, authentication, the PR, the sender mapping, the
   QA mapping, the area, the webhook, and both bullet sections. It then runs
   `gh pr edit ... --add-reviewer <github-login>` and posts the webhook.
5. Report the PR URL, assigned QA person, and Discord result. If GitHub
   assignment succeeds but Discord fails, report the partial success and do not
   remove the reviewer or retry automatically.

## Discord payload

```text
[MOB/BE] <pr title>
PR: <pr link>
From: <sender tag>
To: <QA tag>
PLease help to QA this pr

Changes:
- <change bullet>

Steps to verify:
- <verification-step bullet>
```

`MOB`/`BE` is selected from the repository (or explicit `--area`). Sender and
QA tags are real Discord mentions in the form `<@discord-id>`.
