#!/usr/bin/env python3
"""Copy ignored local PILAH config from canonical checkouts to sibling worktrees."""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def workspace_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".gitmodules").is_file() and (parent / "pilah-be").is_dir():
            return parent
    raise RuntimeError("could not locate PILAH workspace root")


def git_root(path: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def target_repo(root: Path, target: Path) -> str:
    target = target.resolve()
    for repo in ("pilah-be", "pilah-mobile"):
        worktrees = (root / f"{repo}-worktrees").resolve()
        if target.is_relative_to(worktrees) and target != worktrees:
            if git_root(target) != target:
                raise RuntimeError("target must be the worktree root")
            marker = "manage.py" if repo == "pilah-be" else "pubspec.yaml"
            if not (target / marker).is_file():
                raise RuntimeError(f"target is not a {repo} worktree")
            return repo
    raise RuntimeError("target must be under pilah-be-worktrees or pilah-mobile-worktrees")


def copy_one(root: Path, target: Path, relative: str, *, replace: bool) -> None:
    source_repo = "pilah-be" if target_repo(root, target) == "pilah-be" else "pilah-mobile"
    source = root / source_repo / relative
    destination = target / relative
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f"canonical source is missing or not a regular file: {source_repo}/{relative}")
    if destination.is_symlink():
        raise RuntimeError(f"refusing to write through a symlink: {destination}")

    ignored = subprocess.run(
        ["git", "-C", str(target), "check-ignore", "-q", relative],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if ignored.returncode != 0:
        raise RuntimeError(f"destination is not git-ignored: {relative}")

    if destination.is_file():
        if filecmp.cmp(source, destination, shallow=False):
            destination.chmod(0o600)
            print(f"unchanged: {target_repo(root, target)}/{relative}")
            return
        if not replace:
            raise RuntimeError(f"destination differs; preserved it (pass --replace to overwrite): {relative}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
        temp_path = Path(temporary.name)
        with source.open("rb") as source_file:
            shutil.copyfileobj(source_file, temporary)
    try:
        temp_path.chmod(0o600)
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)
    print(f"copied: {target_repo(root, target)}/{relative} (mode 600)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, help="explicit sibling worktree; defaults to the current worktree")
    parser.add_argument("--replace", action="store_true", help="overwrite differing ignored destination files")
    args = parser.parse_args()

    try:
        root = workspace_root()
        target = args.target.resolve() if args.target else git_root(Path.cwd())
        repo = target_repo(root, target)
        files = [".env"]
        if repo == "pilah-mobile":
            files.append("android/app/google-services.json")
        for relative in files:
            copy_one(root, target, relative, replace=args.replace)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"localhost: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
