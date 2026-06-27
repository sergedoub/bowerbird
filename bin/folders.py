#!/usr/bin/env python3
"""List your X bookmark folders (names + ids) for config/topics.toml.

Uses the OAuth2 user-context token (run `bowerbird auth` once first). Copy the ids of the
folders you want to ingest into config/topics.toml, or run `bowerbird init` to do this
interactively.

Usage:  bowerbird folders   (or python3 bin/folders.py)
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bowerbird.folders import run_folders                        # noqa: E402
from bowerbird.local import load_env_file, make_token_store, resolve_user_id  # noqa: E402
from bowerbird.x_client import XBookmarkClient                   # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"))
    ap.add_argument(
        "--counts",
        action="store_true",
        help=(
            "walk each folder's ID pages and print counts/cost estimates "
            "(may consume billable X reads)"
        ),
    )
    args = ap.parse_args()

    load_env_file(os.path.join(HERE, ".env"))
    tokens = make_token_store(HERE)
    client = XBookmarkClient(resolve_user_id(tokens), tokens)
    run_folders(client, counts=args.counts)


if __name__ == "__main__":
    main()
