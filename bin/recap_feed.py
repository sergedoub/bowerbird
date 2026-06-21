#!/usr/bin/env python3
"""Write compile/recap-feed.json: the day's new wiki source notes, grouped by recap lane.

"New since last recap" is a git fact (what the compile ADDED in the window), so this
script asks git, then delegates feed construction to kb.recap_feed. Account display
labels come from the optional `label` field in config/accounts.toml.

Runs once a day in CI (kb-recap-feed.yml) -> at most one feed write -> exactly one
recap post per day. Usage:  python3 bin/recap_feed.py [--window-hours 24]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.config import AccountsConfig, ConfigError       # noqa: E402
from kb.recap_feed import build_feed                    # noqa: E402


def added_in_window(window_hours: int) -> list[str]:
    out = subprocess.run(
        ["git", "log", f"--since={window_hours} hours ago", "--diff-filter=A",
         "--name-only", "--pretty=format:", "--", "wiki/*/sources/*.md"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return sorted({line.strip() for line in out.splitlines()
                   if line.strip().endswith(".md")})


def account_labels() -> dict[str, str]:
    try:
        cfg = AccountsConfig.load(os.path.join(ROOT, "config", "accounts.toml"))
    except (FileNotFoundError, ConfigError):
        return {}
    return {a.handle: a.label for a in cfg.accounts if a.label}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=int, default=24)
    args = ap.parse_args()

    added = added_in_window(args.window_hours)
    feed = build_feed(
        added,
        lambda p: open(os.path.join(ROOT, p), encoding="utf-8").read(),
        today=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d"),
        labels=account_labels(),
        window_hours=args.window_hours,
    )
    os.makedirs(os.path.join(ROOT, "compile"), exist_ok=True)
    with open(os.path.join(ROOT, "compile", "recap-feed.json"), "w") as f:
        json.dump(feed, f, indent=2, ensure_ascii=False)
        f.write("\n")
    inlined = sum(len(v["notes"]) for group in ("accounts", "topics")
                  for v in feed[group].values())
    print(f"feed: {feed['summary']['total_new']} new note(s) across "
          f"{feed['summary']['account_lanes']} account lane(s) and "
          f"{feed['summary']['topic_lanes']} topic lane(s); inlined {inlined} bodies")


if __name__ == "__main__":
    main()
