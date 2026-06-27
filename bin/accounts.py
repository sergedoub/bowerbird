#!/usr/bin/env python3
"""Manage followed X accounts in config/accounts.toml."""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bowerbird.accounts import add_account, load_account_rows, slug_topic  # noqa: E402
from bowerbird.config import ConfigError  # noqa: E402


def _config_path() -> str:
    return os.path.join(ROOT, "config", "accounts.toml")


def add(args: argparse.Namespace) -> int:
    try:
        added, handle = add_account(
            _config_path(),
            args.handle,
            topic=args.topic,
            label=args.label,
            off_topic=args.off_topic,
        )
    except ConfigError as e:
        print(f"accounts: {e}", file=sys.stderr)
        return 2

    topic = slug_topic(args.topic or handle)
    if added:
        print(f"added @{handle} to {topic}")
    else:
        print(f"@{handle} is already followed")
    return 0


def list_accounts(_args: argparse.Namespace) -> int:
    path = _config_path()
    if not os.path.exists(path):
        return 0
    for row in load_account_rows(open(path, encoding="utf-8").read()):
        label = f" ({row['label']})" if row.get("label") else ""
        print(f"@{row['handle']} -> {row['topic']}{label}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"))
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="follow an X account")
    add_parser.add_argument("handle", help="X handle, with or without @")
    add_parser.add_argument(
        "--topic",
        help="wiki topic for this account (default: slug of handle)",
    )
    add_parser.add_argument("--label", help="display label for recap profiles")
    add_parser.add_argument(
        "--off-topic",
        choices=("skip", "quarantine"),
        default="skip",
        help="policy for posts outside the configured topic",
    )
    add_parser.set_defaults(func=add)

    list_parser = sub.add_parser("list", help="show followed accounts")
    list_parser.set_defaults(func=list_accounts)

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
