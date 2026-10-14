#!/usr/bin/env python3
"""Assign known GitHub reviewers and notify a Discord webhook."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from http.client import HTTPException, HTTPSConnection
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


WEBHOOK_ENV = "DISCORD_REVIEW_WEBHOOK_URL"
REVIEW_REQUESTS = (
    "Please review these changes when you have a moment.",
    "Could you take a look at these changes and share your feedback?",
    "I'd appreciate your review of these changes.",
    "When you have time, please review these changes.",
    "Could you review these pull requests and leave any feedback?",
    "Please take a look at the changes and let me know what you think.",
    "Your review would be appreciated.",
    "Would you mind reviewing these changes?",
    "Please share your thoughts after reviewing these changes.",
    "Could you review these changes when convenient?",
)
LINEAR_ISSUE_KEY = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*-\d+)(?![A-Za-z0-9])"
)


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
    args.extend(["--json", "number,title,url,headRefName,body"])
    result = run_gh(args)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise UserError("gh returned invalid pull-request JSON") from exc

    required = ("number", "title", "url")
    if any(key not in data for key in required):
        raise UserError("gh did not return the PR number, title, and URL")
    return data


def linear_issue_key(pr: dict[str, Any]) -> str | None:
    for field in ("headRefName", "title", "body"):
        matches = {
            match.upper()
            for match in LINEAR_ISSUE_KEY.findall(str(pr.get(field) or ""))
        }
        if len(matches) > 1:
            raise UserError(
                f"PR #{pr['number']} has multiple possible Linear issue IDs in {field}"
            )
        if matches:
            return next(iter(matches))
    return None


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
    try:
        port = parsed.port
    except ValueError as exc:
        raise UserError(f"{WEBHOOK_ENV} must be an HTTPS Discord webhook URL") from exc
    valid_host = (
        host == "discord.com"
        or host.endswith(".discord.com")
        or host == "discordapp.com"
    )
    if (
        parsed.scheme != "https"
        or port not in (None, 443)
        or not valid_host
        or not parsed.path.startswith("/api/webhooks/")
    ):
        raise UserError(
            f"{WEBHOOK_ENV} must be an HTTPS Discord webhook URL"
        )
    return value


def group_pull_requests(
    pull_requests: list[dict[str, Any]],
) -> list[tuple[str | None, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    issue_keys: dict[str, str | None] = {}
    for pr in pull_requests:
        issue_key = pr["issue_key"]
        group_key = issue_key or str(pr["url"])
        grouped.setdefault(group_key, []).append(pr)
        issue_keys[group_key] = issue_key
    return [(issue_keys[key], prs) for key, prs in grouped.items()]


def message_content(
    issue_key: str | None,
    pull_requests: list[dict[str, Any]],
    sender: Member,
    reviewers: list[Member],
) -> str:
    reviewer_tags = " ".join(f"<@{reviewer.discord_id}>" for reviewer in reviewers)
    areas = sorted(
        {str(pr["area"]) for pr in pull_requests},
        key=lambda area: {"MOB": 0, "BE": 1}.get(area, 2),
    )
    area_tags = " ".join(f"[{area}]" for area in areas)
    if len(pull_requests) == 1:
        header = f"{area_tags} {pull_requests[0]['title']}"
        pr_lines = [f"PR: {pull_requests[0]['url']}"]
    else:
        header = f"{area_tags} changes for {issue_key}"
        pr_lines = [
            f"{pr['area']} PR: {pr['url']}"
            for pr in sorted(
                pull_requests,
                key=lambda pr: {"MOB": 0, "BE": 1}.get(str(pr["area"]), 2),
            )
        ]
    return "\n".join(
        (
            header,
            *pr_lines,
            f"From: <@{sender.discord_id}>",
            f"To: {reviewer_tags}",
            secrets.choice(REVIEW_REQUESTS),
        )
    )


def send_discord(
    webhook: str, content: str, sender: Member, reviewers: list[Member]
) -> None:
    payload = {
        "content": content,
        "allowed_mentions": {
            "users": [
                sender.discord_id,
                *(reviewer.discord_id for reviewer in reviewers),
            ]
        },
    }
    parsed = urlparse(webhook)
    host = parsed.hostname
    if parsed.scheme != "https" or host is None:
        raise UserError("Discord webhook URL must be HTTPS and include a hostname")
    try:
        connection = HTTPSConnection(host, parsed.port or 443, timeout=20)
    except (OSError, ValueError) as exc:
        raise UserError(f"Discord webhook request failed: {exc}") from exc

    try:
        connection.request(
            "POST",
            parsed.path + (f"?{parsed.query}" if parsed.query else ""),
            body=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ask-for-review-skill",
            },
        )
        response = connection.getresponse()
        status = response.status
        detail = response.read().decode("utf-8", errors="replace")[:300]
    except (HTTPException, OSError, ValueError) as exc:
        raise UserError(f"Discord webhook request failed: {exc}") from exc
    finally:
        connection.close()

    if status not in {200, 204}:
        raise UserError(
            f"Discord webhook failed with HTTP {status}" + (f": {detail}" if detail else "")
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assign known GitHub reviewers and notify Discord."
    )
    parser.add_argument(
        "--reviewer",
        action="append",
        required=True,
        help="GitHub login or known Discord alias; repeat for multiple reviewers",
    )
    parser.add_argument(
        "--pr",
        action="append",
        help="PR URL or number; repeat to request reviews for multiple PRs",
    )
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO form")
    parser.add_argument(
        "--area", help="MOB or BE; otherwise detect it from the repository"
    )
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
    reviewers = list(dict.fromkeys(resolve_member(value) for value in args.reviewer))
    webhook = webhook_url()

    pull_requests = []
    seen_urls = set()
    for pr_ref in args.pr or [None]:
        pr = pr_view(pr_ref, args.repo)
        pr_url = str(pr["url"])
        if pr_url in seen_urls:
            continue
        seen_urls.add(pr_url)
        repo = args.repo or repo_from_pr_url(pr_url) or current_repo(None)
        pr["area"] = detect_area(repo, args.area)
        pr["issue_key"] = linear_issue_key(pr)
        pr["ref"] = pr_ref
        pull_requests.append(pr)

    groups = group_pull_requests(pull_requests)
    reviewer_logins = ",".join(reviewer.github for reviewer in reviewers)
    for issue_key, grouped_prs in groups:
        content = message_content(issue_key, grouped_prs, sender, reviewers)
        for pr in grouped_prs:
            print(f"PR #{pr['number']}: {pr['url']}")
        print(f"Reviewers: {', '.join(reviewer.github for reviewer in reviewers)}")
        if args.dry_run:
            print("Dry run; no GitHub or Discord changes made.")
            print(content)
            continue

        assigned_urls = []
        for pr in grouped_prs:
            edit_target = pr["ref"] or str(pr["number"])
            edit_args = ["pr", "edit", edit_target]
            if args.repo:
                edit_args.extend(["--repo", args.repo])
            edit_args.extend(["--add-reviewer", reviewer_logins])
            try:
                run_gh(edit_args)
            except UserError as exc:
                assigned = ", ".join(assigned_urls)
                partial = (
                    f"reviewers already assigned to {assigned}; " if assigned else ""
                )
                raise UserError(
                    f"{partial}could not assign reviewers to {pr['url']}: {exc}"
                ) from exc
            assigned_urls.append(pr["url"])
            print(f"Assigned GitHub reviewers to {pr['url']}: {reviewer_logins}.")

        try:
            send_discord(webhook, content, sender, reviewers)
        except UserError as exc:
            raise UserError(
                f"reviewer assignments succeeded for {', '.join(assigned_urls)}, "
                f"but Discord notification failed: {exc}"
            ) from exc
        print("Discord review request sent.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UserError as exc:
        print(f"ask-for-review: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
