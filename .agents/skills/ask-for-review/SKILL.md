---
name: ask-for-review
description: Request GitHub PR reviews from mapped users, with one grouped Discord notification per PR. Use for "ask for review", "request review", or "ping <name> for review".
metadata:
  requires:
    bins: ["gh", "python3"]
---

# Ask for Review

This skill operates on **existing GitHub pull requests**. It does not create
PRs. For each PR, it assigns all mapped reviewers together, then sends one
Discord notification containing all their mentions.

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

1. Parse one or more reviewers from the request. Use the current branch's PR
   unless the user supplied PR URLs or numbers. For a multi-PR request, invoke
   the helper once per PR so each PR gets at most one Discord notification.
2. Run the bundled helper. Use `--area MOB` for `pilah-mobile` and `--area BE`
   for `pilah-be` only when repository-name detection cannot determine it:

   ```bash
   workspace_root="$(git rev-parse --show-superproject-working-tree)"
   [ -n "$workspace_root" ] || workspace_root="$(git rev-parse --show-toplevel)"
   python3 "$workspace_root/.agents/skills/ask-for-review/scripts/ask_for_review.py" \
     --reviewer <github-login-or-discord-username> \
     [--reviewer <github-login-or-discord-username> ...] \
     [--pr <url-or-number>] [--area MOB|BE]
   ```

   Use `--dry-run` to inspect the resolved PR and payload without changing
   GitHub or sending Discord.
3. The helper validates `gh`, authentication, the PR, the sender and every
   reviewer mapping, the area, and the webhook before making changes. It runs
   one `gh pr edit ... --add-reviewer login1,login2` and sends one webhook
   message for that PR, regardless of reviewer count.
4. Report each PR URL, all assigned GitHub reviewers, and the Discord result. If
   assignment succeeds but Discord fails, report the partial success and do not
   remove reviewers or retry automatically.

## Discord payload

The message content is exactly:

```text
[MOB/BE] <pr title>
PR: <pr link>
From: <sender tag>
To: <@reviewer-id-1> <@reviewer-id-2>
<random review-request sentence>
```

`MOB`/`BE` is selected from the repository (or the explicit `--area`). Sender
and all reviewer tags are real Discord mentions in the form `<@discord-id>`;
`allowed_mentions.users` includes every mentioned user. The final line is chosen
uniformly from ten unique sentences, giving each a 10% chance per message.
