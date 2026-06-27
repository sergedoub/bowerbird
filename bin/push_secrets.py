#!/usr/bin/env python3
"""Push staged credentials to this repo's GitHub Actions secrets (`bowerbird push-secrets`).

Reads the gitignored bin/.env (X_CLIENT_ID, X_CLIENT_SECRET, X_BEARER_TOKEN, GH_PAT,
provider API keys, SLACK_BOT_TOKEN) and bin/.x_tokens.json (X_TOKENS), and runs `gh secret set`
for every value present. Nothing is typed and no secret value is ever printed — only
key names. Requires the gh CLI, authenticated, inside the repo clone.

Usage:  bowerbird push-secrets [--repo owner/name]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.secrets_push import (                             # noqa: E402
    LIVE_INSTANCE_SECRET_NAMES,
    LIVE_INSTANCE_VARIABLE,
    push_secrets,
)


def read_env() -> dict:
    path = os.path.join(HERE, ".env")
    env: dict = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip("'\"")
    return env


def read_tokens() -> str:
    path = os.path.join(HERE, ".x_tokens.json")
    return open(path).read() if os.path.exists(path) else ""


def origin_repo() -> str:
    proc = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return ""
    url = proc.stdout.strip()
    match = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$", url)
    return match.group(1) if match else ""


def set_secret(repo: str, name: str, value: str) -> bool:
    cmd = ["gh", "secret", "set", name]
    if repo:
        cmd += ["--repo", repo]
    proc = subprocess.run(cmd, cwd=ROOT,
                          input=value.encode(), capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(f"  gh failed for {name}: {proc.stderr.decode().strip()}\n")
    return proc.returncode == 0


def set_variable(repo: str, name: str, value: str) -> bool:
    cmd = ["gh", "variable", "set", name, "--body", value]
    if repo:
        cmd += ["--repo", repo]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(f"  gh failed for variable {name}: {proc.stderr.decode().strip()}\n")
    return proc.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=os.environ.get("BOWERBIRD_PROG", "bowerbird push-secrets"),
        description="Push staged secrets to GitHub Actions without printing values.",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="target repository as owner/name; defaults to the git origin remote",
    )
    args = parser.parse_args()
    if not shutil.which("gh"):
        sys.exit("push-secrets needs the gh CLI (https://cli.github.com), authenticated.")
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        sys.exit("gh is not authenticated — run `gh auth login` first.")

    repo = args.repo or origin_repo()
    if not repo:
        sys.exit("could not infer GitHub repo from origin; pass --repo owner/name")
    print(f"target repo: {repo}")
    result = push_secrets(read_env(), read_tokens(),
                          lambda name, value: set_secret(repo, name, value))
    for name in result["set"]:
        print(f"  set {name}")
    for name in result["skipped"]:
        print(f"  skipped {name} (not staged in bin/.env"
              f"{' / no token file — run `bowerbird auth`' if name == 'X_TOKENS' else ''})")
    if result["failed"]:
        sys.exit(f"failed: {', '.join(result['failed'])}")
    staged = read_env()
    staged["X_TOKENS"] = read_tokens().strip()
    if all(staged.get(name, "").strip() for name in LIVE_INSTANCE_SECRET_NAMES):
        if set_variable(repo, LIVE_INSTANCE_VARIABLE, "true"):
            print(f"  set variable {LIVE_INSTANCE_VARIABLE}")
        else:
            sys.exit(f"failed: variable {LIVE_INSTANCE_VARIABLE}")
    print(f"--- push-secrets: {len(result['set'])} set, {len(result['skipped'])} skipped ---")


if __name__ == "__main__":
    main()
