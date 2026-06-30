#!/usr/bin/env python3
"""X Recent Search monitors -> raw/searches/<monitor>/."""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bowerbird.config import ConfigError, SearchesConfig  # noqa: E402
from bowerbird.raw_writer import RawWriter  # noqa: E402
from bowerbird.search_dump import RecentSearchClient, run_dump  # noqa: E402


def load_local_env() -> None:
    """Local convenience: load bin/.env if present (CI passes real env vars instead)."""
    path = os.path.join(HERE, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def main() -> None:
    parser = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"))
    parser.add_argument("--name", help="single search monitor (default: all in config)")
    parser.add_argument("--max-results", type=int, help="override configured max_results")
    parser.add_argument("--max-pages", type=int, help="override configured max_pages")
    parser.add_argument("--lookback-hours", type=int, help="override first-run lookback")
    args = parser.parse_args()

    load_local_env()
    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        sys.exit("X_BEARER_TOKEN not set (GitHub secret, or bin/.env locally).")

    try:
        cfg = SearchesConfig.load(os.path.join(ROOT, "config", "searches.toml"))
    except (FileNotFoundError, ConfigError) as exc:
        sys.exit(f"search config error: {exc}")
    monitors = [m for m in cfg.searches if (not args.name or m.name == args.name)]
    if not monitors:
        if args.name:
            sys.exit(f"search monitor '{args.name}' not in config/searches.toml")
        print("No searches configured in config/searches.toml.")
        return

    client = RecentSearchClient(bearer)
    writer = RawWriter(os.path.join(ROOT, "raw"))
    summary = run_dump(
        monitors,
        client,
        writer,
        raw_root=os.path.join(ROOT, "raw"),
        now_utc=dt.datetime.now(dt.UTC),
        max_results=args.max_results,
        max_pages=args.max_pages,
        lookback_hours=args.lookback_hours,
    )
    for path in summary["written_paths"]:
        print("  wrote", os.path.relpath(path, ROOT))
    print(
        f"--- dump-search: monitors={len(monitors)} seen={summary['seen']} "
        f"written={summary['written']} skipped={summary['skipped']} ---"
    )
    if summary["saturated"]:
        print("warning: saturated search monitors: " + ", ".join(summary["saturated"]))


if __name__ == "__main__":
    main()
