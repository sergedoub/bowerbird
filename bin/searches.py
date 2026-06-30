#!/usr/bin/env python3
"""Manage X Recent Search monitors in config/searches.toml."""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bowerbird.config import ConfigError  # noqa: E402
from bowerbird.searches import add_search, load_search_rows  # noqa: E402


def _config_path() -> str:
    return os.path.join(ROOT, "config", "searches.toml")


def add(args: argparse.Namespace) -> int:
    try:
        added, name = add_search(
            _config_path(),
            args.name,
            topic=args.topic,
            query=args.query,
            label=args.label,
            lookback_hours=args.lookback_hours,
            max_results=args.max_results,
            max_pages=args.max_pages,
        )
    except ConfigError as exc:
        print(f"searches: {exc}", file=sys.stderr)
        return 2

    if added:
        print(f"added search monitor {name} -> {args.topic}")
    else:
        print(f"search monitor {name} already exists")
    return 0


def list_searches(_args: argparse.Namespace) -> int:
    path = _config_path()
    if not os.path.exists(path):
        return 0
    for row in load_search_rows(open(path, encoding="utf-8").read()):
        label = f" ({row['label']})" if row.get("label") else ""
        print(
            f"{row['name']} -> {row['topic']}{label} "
            f"max_results={row['max_results']} max_pages={row['max_pages']}"
        )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"))
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="add an X Recent Search monitor")
    add_parser.add_argument("name", help="monitor slug; becomes raw/searches/<name>/")
    add_parser.add_argument("--topic", required=True, help="wiki topic for compiled source notes")
    add_parser.add_argument("--query", required=True, help="literal X Recent Search query")
    add_parser.add_argument("--label", help="display label")
    add_parser.add_argument("--lookback-hours", type=int, default=24)
    add_parser.add_argument("--max-results", type=int, default=10)
    add_parser.add_argument("--max-pages", type=int, default=1)
    add_parser.set_defaults(func=add)

    list_parser = sub.add_parser("list", help="show configured search monitors")
    list_parser.set_defaults(func=list_searches)

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
