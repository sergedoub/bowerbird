"""Repository identity guardrails for source-vs-instance operations."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Mapping

SOURCE_REPOSITORY = "sergedoub/bowerbird"


class BoundaryError(RuntimeError):
    """Raised when an operation would cross the source/instance boundary."""


def normalize_repository(value: str) -> str:
    """Return owner/name for GitHub repo names or URLs, lower-cased."""
    text = value.strip()
    if not text:
        return ""
    match = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$", text)
    repo = match.group(1) if match else text
    repo = repo.removesuffix(".git")
    return repo.lower()


def repository_from_origin(repo_root: str | Path) -> str:
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc.returncode != 0:
        return ""
    return normalize_repository(proc.stdout)


def repository_identity(
    repo_root: str | Path,
    *,
    env: Mapping[str, str] | None = None,
    explicit_repo: str = "",
) -> str:
    """Resolve the repository as owner/name from explicit input, CI env, or origin."""
    source = explicit_repo or (env or os.environ).get("GITHUB_REPOSITORY", "")
    return normalize_repository(source) or repository_from_origin(repo_root)


def is_source_repository(repo: str) -> bool:
    return normalize_repository(repo) == SOURCE_REPOSITORY


def require_instance_repository(
    repo_root: str | Path,
    operation: str,
    *,
    env: Mapping[str, str] | None = None,
    explicit_repo: str = "",
) -> str:
    """Fail closed unless the operation targets a non-source instance repository."""
    repo = repository_identity(repo_root, env=env, explicit_repo=explicit_repo)
    if not repo:
        raise BoundaryError(
            f"refusing to {operation}: could not resolve GitHub repository identity"
        )
    if is_source_repository(repo):
        raise BoundaryError(
            f"refusing to {operation} in public source repo {SOURCE_REPOSITORY}; "
            "use a personal instance repo such as sergedoub/bowerbird-serge"
        )
    return repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bowerbird.repo_boundary")
    parser.add_argument("operation", help="mutating operation being guarded")
    parser.add_argument("--repo-root", default=".", help="repository checkout root")
    parser.add_argument("--repo", default="", help="explicit GitHub owner/name target")
    args = parser.parse_args(argv)
    try:
        repo = require_instance_repository(args.repo_root, args.operation, explicit_repo=args.repo)
    except BoundaryError as exc:
        print(f"repo boundary: {exc}", file=sys.stderr)
        return 78
    print(f"repo boundary: {args.operation} allowed for {repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
