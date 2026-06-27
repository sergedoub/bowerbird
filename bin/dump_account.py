#!/usr/bin/env python3
"""Daily account dump: posts + replies from configured accounts -> raw/accounts/<handle>/.

A sibling to bin/pull.py, but for whole accounts rather than your bookmarks. It reads
config/accounts.toml, walks each account's timeline (GET /2/users/:id/tweets, retweets
excluded, replies kept), and writes one markdown file per post. Idempotent: already-stored
posts are skipped. Each run is scoped to a trailing window (--days, default 3), so it captures
the last few days and accrues forward; the daily overlap self-heals a skipped run.

Auth is the app-only Bearer only — set X_BEARER_TOKEN (GitHub secret, or bin/.env locally).
No user-context token / rotation needed for this pipeline.

Usage:  python3 bin/dump_account.py [--handle account_one] [--days 3 | --full]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bowerbird.account_dump import run_dump                      # noqa: E402
from bowerbird.config import AccountsConfig                      # noqa: E402
from bowerbird.raw_writer import RawWriter                       # noqa: E402
from bowerbird.timeline import TimelineClient                    # noqa: E402


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


def main() -> None:
    ap = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"))
    ap.add_argument("--handle", help="single account (default: all in config)")
    ap.add_argument("--days", type=int, default=3,
                    help="trailing window in days to fetch (default: 3)")
    ap.add_argument("--full", action="store_true",
                    help="ignore the window and grab the full available timeline (~3,200 max)")
    ap.add_argument("--max-posts", type=int, default=None,
                    help="cap posts processed per account (newest-first); also caps paid reads")
    args = ap.parse_args()

    load_local_env()
    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        sys.exit("X_BEARER_TOKEN not set (GitHub secret, or bin/.env locally).")

    cfg = AccountsConfig.load(os.path.join(ROOT, "config", "accounts.toml"))
    accounts = [a for a in cfg.accounts if (not args.handle or a.handle == args.handle.lstrip("@"))]
    if not accounts:
        if args.handle:
            sys.exit(f"account '{args.handle}' not in config/accounts.toml")
        print("No accounts configured in config/accounts.toml.")
        return

    start_time = None
    if not args.full:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        start_time = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    client = TimelineClient(bearer)
    writer = RawWriter(os.path.join(ROOT, "raw", "accounts"))

    summary = run_dump(accounts, client, writer, start_time=start_time,
                       max_posts=args.max_posts)
    for p in summary["written_paths"]:
        print("  wrote", os.path.relpath(p, ROOT))
    window = "full history" if args.full else f"last {args.days}d (since {start_time})"
    print(f"--- dump: accounts={len(accounts)} window={window} seen={summary['seen']} "
          f"written={summary['written']} skipped={summary['skipped']} "
          f"early_stops={summary['early_stops']} ---")
    print(f"approx X API cost: ${summary['seen'] * 0.001:.3f} (timeline reads)")


if __name__ == "__main__":
    main()
