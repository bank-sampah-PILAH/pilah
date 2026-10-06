---
name: ask-for-review
description: Request review on an existing GitHub pull request, assign a mapped GitHub reviewer, and post an exact Discord webhook notification with real Discord mentions. Use when the user says "ask for review", "request review", "ping <name> for review", or asks to notify Discord about a PR review.
metadata:
  requires:
    bins: ["gh", "python3"]
---

# Ask for Review

This skill operates on an **existing GitHub pull request**. It does not create a
PR. It assigns one mapped reviewer first, then sends the Discord notification.

## Preconditions

- Run in the repository containing the PR, or pass the PR URL with `--pr`.
- Before doing anything, verify `gh` exists (`command -v gh`), print
  `gh --version`, and run `gh auth status`. If it is missing, stop and tell the
  user to install GitHub CLI from <https://cli.github.com/>. If it is not
  authenticated, stop and ask the user to run `gh auth login`.
- Require `DISCORD_REVIEW_WEBHOOK_URL` in the environment or the nearest
  repository `.env` file. The workspace root `.env` is gitignored. Never print
  the webhook URL or copy it into logs, messages, or project files.

## Known identities

Match the requested reviewer by GitHub login (case-insensitive). The Discord
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

If the reviewer is missing or not in this table, ask for a supported GitHub
login. Do not guess or assign an unmapped person. The authenticated GitHub
user must also be in the table because they are the message sender.

## Workflow

1. Parse exactly one reviewer from the request. Use the current branch's PR
   unless the user supplied a PR URL or number.
2. Run the bundled helper. Use `--area MOB` for `pilah-mobile` and `--area BE`
   for `pilah-be` only when repository-name detection cannot determine it:

   ```bash
   workspace_root="$(git rev-parse --show-superproject-working-tree)"
   [ -n "$workspace_root" ] || workspace_root="$(git rev-parse --show-toplevel)"
   python3 "$workspace_root/.agents/skills/ask-for-review/scripts/ask_for_review.py" \
     --reviewer <github-login-or-discord-username> [--pr <url-or-number>] [--area MOB|BE]
   ```

   Use `--dry-run` to inspect the resolved PR and payload without changing
   GitHub or sending Discord.
3. The helper validates `gh`, authentication, the PR, the sender mapping, the
   reviewer mapping, the area, and the webhook before making changes. It then
   runs `gh pr edit ... --add-reviewer <github-login>` and posts the webhook.
4. Report the PR URL, assigned GitHub reviewer, and Discord result. If GitHub
   assignment succeeds but Discord fails, report the partial success and do
   not remove the reviewer or retry automatically.

## Discord payload

The message content is exactly:

```text
[MOB/BE] <pr title>
PR: <pr link>
From: <sender tag>
To: <reviewer tag>
PLease help to review this pr
```

`MOB`/`BE` is selected from the repository (or the explicit `--area`). Sender
and reviewer tags are real Discord mentions in the form `<@discord-id>`.
