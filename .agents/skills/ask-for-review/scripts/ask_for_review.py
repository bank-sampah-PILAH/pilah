#!/usr/bin/env python3
"""Assign a known GitHub reviewer and notify a Discord webhook."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


WEBHOOK_ENV = "DISCORD_REVIEW_WEBHOOK_URL"


@dataclass(frozen=True)
class Member:
    github: str
    discord_id: str
    discord_username: str


MEMBERS = (
    Member("TrayMachi", "336112760255414284", "traymachi"),
    Member("alghani46", "710341591910580226", "baller3839"),
    Member("HeraldoArman", "539004236441190401", "dooo78"),
    Member("Twentism", "764158279957348432", "twentism_"),
    Member("Scallss", "376340393480159232", "scalss"),
    Member("mvfi0", "467854943068356608", "vegardthemagicalcheesewizard"),
)


class UserError(Exception):
    """An actionable validation or external-command error."""


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise UserError(f"could not run {command[0]}: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        if len(detail) > 600:
            detail = f"{detail[:600]}…"
        raise UserError(
            f"{' '.join(command)} failed"
            + (f": {detail}" if detail else f" (exit {result.returncode})")
        )
    return result


def run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return run_command(["gh", *args])


def verify_gh() -> str:
    gh_path = shutil.which("gh")
    if gh_path is None:
        raise UserError(
            "GitHub CLI (gh) is required. Install it from https://cli.github.com/ "
            "and rerun this skill."
        )

    version = run_command(["gh", "--version"]).stdout.splitlines()
    try:
        run_gh(["auth", "status"])
    except UserError as exc:
        raise UserError(
            "GitHub CLI is not authenticated; run `gh auth login` and rerun this skill"
        ) from exc
    if version:
        print(version[0])
    return gh_path


def resolve_member(value: str) -> Member:
    query = value.strip().lstrip("@").casefold()
    matches = [
        member
        for member in MEMBERS
        if query
        and query
        in {
            member.github.casefold(),
            member.discord_username.casefold(),
            member.discord_id.casefold(),
        }
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise UserError(f"{value!r} matches more than one known identity")
    known = ", ".join(member.github for member in MEMBERS)
    raise UserError(f"{value!r} is not a known identity; choose one of: {known}")


def current_member() -> Member:
    result = run_gh(["api", "user", "--jq", ".login"])
    login = result.stdout.strip()
    if not login:
        raise UserError("GitHub CLI returned no authenticated username")
    try:
        return resolve_member(login)
    except UserError as exc:
        raise UserError(
            f"authenticated GitHub user {login!r} is not in the known identity table"
        ) from exc


def pr_view(pr_ref: str | None, repo: str | None) -> dict[str, Any]:
    args = ["pr", "view"]
    if pr_ref:
        args.append(pr_ref)
    if repo:
        args.extend(["--repo", repo])
    args.extend(["--json", "number,title,url"])
    result = run_gh(args)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise UserError("gh returned invalid pull-request JSON") from exc

    required = ("number", "title", "url")
    if any(key not in data for key in required):
        raise UserError("gh did not return the PR number, title, and URL")
    return data


def repo_from_pr_url(pr_url: str) -> str | None:
    parsed = urlparse(pr_url)
    pieces = [piece for piece in parsed.path.split("/") if piece]
    if len(pieces) >= 4 and pieces[2].lower() == "pull":
        return f"{pieces[0]}/{pieces[1]}"
    return None


def current_repo(repo: str | None) -> str:
    args = ["repo", "view"]
    if repo:
        args.extend(["--repo", repo])
    args.extend(["--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    result = run_gh(args)
    name = result.stdout.strip()
    if not name:
        raise UserError("could not determine the GitHub repository")
    return name


def detect_area(repo: str, requested_area: str | None) -> str:
    if requested_area:
        area = requested_area.upper()
        if area not in {"MOB", "BE"}:
            raise UserError("area must be MOB or BE")
        return area

    slug = repo.rsplit("/", 1)[-1].casefold()
    if slug == "pilah-mobile" or slug.endswith("-mobile"):
        return "MOB"
    if slug in {"pilah-be", "be", "backend"} or slug.endswith(("-be", "-backend")):
        return "BE"
    raise UserError(
        f"could not map repository {repo!r} to MOB or BE; rerun with --area MOB or --area BE"
    )


def dotenv_value(key: str) -> str | None:
    """Read one value from the nearest .env without importing dependencies."""
    for directory in (Path.cwd(), *Path.cwd().parents):
        dotenv = directory / ".env"
        if not dotenv.is_file():
            continue
        try:
            lines = dotenv.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            name, separator, value = line.partition("=")
            if separator and name.strip() == key:
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                return value
    return None


def webhook_url() -> str:
    value = os.environ.get(WEBHOOK_ENV) or dotenv_value(WEBHOOK_ENV)
    if not value:
        raise UserError(
            f"{WEBHOOK_ENV} is not set; add it to the ignored .env file or environment"
        )
    value = value.strip()
    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()
    valid_host = (
        host == "discord.com"
        or host.endswith(".discord.com")
        or host == "discordapp.com"
    )
    if (
        parsed.scheme != "https"
        or not valid_host
        or not parsed.path.startswith("/api/webhooks/")
    ):
        raise UserError(
            f"{WEBHOOK_ENV} must be an HTTPS Discord webhook URL"
        )
    return value


def message_content(area: str, title: str, pr_url: str, sender: Member, reviewer: Member) -> str:
    return "\n".join(
        (
            f"[{area}] {title}",
            f"PR: {pr_url}",
            f"From: <@{sender.discord_id}>",
            f"To: <@{reviewer.discord_id}>",
            "PLease help to review this pr",
        )
    )


def send_discord(webhook: str, content: str, sender: Member, reviewer: Member) -> None:
    payload = {
        "content": content,
        "allowed_mentions": {"users": [sender.discord_id, reviewer.discord_id]},
    }
    request = Request(
        webhook,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ask-for-review-skill",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            status = response.status
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise UserError(
            f"Discord webhook failed with HTTP {exc.code}"
            + (f": {detail}" if detail else "")
        ) from exc
    except URLError as exc:
        raise UserError(f"Discord webhook request failed: {exc.reason}") from exc

    if status not in {200, 204}:
        raise UserError(f"Discord webhook returned unexpected HTTP {status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assign a known GitHub reviewer and notify Discord."
    )
    parser.add_argument("--reviewer", required=True, help="GitHub login or known Discord alias")
    parser.add_argument("--pr", help="PR URL or number; defaults to the current branch's PR")
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO form")
    parser.add_argument("--area", help="MOB or BE; otherwise detect it from the repository")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and print the notification without changing GitHub or Discord",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verify_gh()
    sender = current_member()
    reviewer = resolve_member(args.reviewer)
    webhook = webhook_url()

    pr = pr_view(args.pr, args.repo)
    pr_url = str(pr["url"])
    repo = args.repo or repo_from_pr_url(pr_url) or current_repo(None)
    area = detect_area(repo, args.area)
    content = message_content(area, str(pr["title"]), pr_url, sender, reviewer)

    print(f"PR #{pr['number']}: {pr_url}")
    print(f"Reviewer: {reviewer.github}")
    if args.dry_run:
        print("Dry run; no GitHub or Discord changes made.")
        print(content)
        return 0

    edit_target = args.pr or str(pr["number"])
    edit_args = ["pr", "edit", edit_target]
    if args.repo:
        edit_args.extend(["--repo", args.repo])
    edit_args.extend(["--add-reviewer", reviewer.github])
    run_gh(edit_args)
    print(f"Assigned GitHub reviewer {reviewer.github}.")

    try:
        send_discord(webhook, content, sender, reviewer)
    except UserError as exc:
        raise UserError(
            f"reviewer assignment succeeded, but Discord notification failed: {exc}"
        ) from exc
    print("Discord review request sent.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UserError as exc:
        print(f"ask-for-review: {exc}", file=sys.stderr)
        raise SystemExit(1)
