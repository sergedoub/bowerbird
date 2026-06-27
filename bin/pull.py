#!/usr/bin/env python3
"""Scheduled forward-only pull: new bookmarks in allowlisted folders -> raw/bookmarks/<topic>/.

Token storage is bin/.x_tokens.json (FileTokenStorage). In CI the X_TOKENS secret is
materialized to that file before the run and the rotated value is written back after.

Other env (from GitHub secrets or bin/.env): X_CLIENT_ID, X_CLIENT_SECRET, X_BEARER_TOKEN,
optional X_USER_ID.

Idempotent and forward-only: RawWriter skips bookmarks already in raw/, so re-runs only add
genuinely new ones. Usage:  python3 bin/pull.py [--topic marketing] [--no-threads]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.config import TopicsConfig                       # noqa: E402
from kb.pull import run_pull                             # noqa: E402
from kb.raw_writer import RawWriter                      # noqa: E402
from kb.search import SearchClient                       # noqa: E402
from kb.tokens import FileTokenStorage, TokenStore       # noqa: E402
from kb.x_client import XBookmarkClient                  # noqa: E402


def load_local_env() -> None:
    """Local convenience: load bin/.env if present (CI passes real env vars instead)."""
    path = os.path.join(HERE, ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def make_storage():
    print("token storage: local file (bin/.x_tokens.json)")
    return FileTokenStorage(os.path.join(HERE, ".x_tokens.json"))


def resolve_user_id(token_store: TokenStore) -> str:
    if os.environ.get("X_USER_ID"):
        return os.environ["X_USER_ID"]
    req = urllib.request.Request("https://api.x.com/2/users/me", method="GET")
    req.add_header("Authorization", f"Bearer {token_store.get_access_token()}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["data"]["id"]


def main() -> None:
    ap = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"))
    ap.add_argument("--topic", help="single topic (default: all in config)")
    ap.add_argument("--no-threads", action="store_true", help="skip thread reconstruction")
    ap.add_argument(
        "--limit-per-folder",
        type=int,
        default=0,
        help="max bookmarks to pull from each configured folder (0 = all; setup usually uses 3)",
    )
    ap.add_argument(
        "--stop-at-existing",
        action="store_true",
        help=(
            "within each folder, stop after the first already-ingested bookmark; "
            "used by scheduled pulls to avoid historical backfill"
        ),
    )
    args = ap.parse_args()
    if args.limit_per_folder < 0:
        sys.exit("--limit-per-folder must be non-negative")

    cfg = TopicsConfig.load(os.path.join(ROOT, "config", "topics.toml"))
    topics = [t for t in cfg.topics if (not args.topic or t.name == args.topic)]
    if not topics:
        if args.topic:
            sys.exit(f"topic '{args.topic}' not in config")
        print("No bookmark topics configured in config/topics.toml.")
        return

    load_local_env()
    token_store = TokenStore(
        os.environ["X_CLIENT_ID"], os.environ.get("X_CLIENT_SECRET"), make_storage(),
    )
    user_id = resolve_user_id(token_store)
    bookmarks = XBookmarkClient(user_id, token_store)
    search = SearchClient(os.environ["X_BEARER_TOKEN"])
    writer = RawWriter(os.path.join(ROOT, "raw", "bookmarks"))

    limit_per_folder = args.limit_per_folder or None
    summary = run_pull(
        topics,
        bookmarks,
        search,
        writer,
        reconstruct_threads=not args.no_threads,
        limit_per_folder=limit_per_folder,
        stop_at_existing=args.stop_at_existing,
    )
    for p in summary["written_paths"]:
        print("  wrote", os.path.relpath(p, ROOT))
    mode = summary.get("search_mode")
    print(f"--- pull: seen={summary['seen']} written={summary['written']} "
          f"skipped={summary['skipped']} threads={summary['threads']}"
          f" stopped_at_existing={summary['stopped_at_existing']}"
          f"{f' limit_per_folder={limit_per_folder}' if limit_per_folder else ''}"
          f"{f' search_mode={mode}' if mode else ''} ---")


if __name__ == "__main__":
    main()
