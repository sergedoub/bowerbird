#!/usr/bin/env python3
"""One-shot book ingest: configured Markdown book -> raw/books/<topic>/."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.books import run_ingest  # noqa: E402
from kb.config import BooksConfig, ConfigError  # noqa: E402
from kb.raw_writer import RawWriter  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"))
    ap.add_argument("--book", required=True, help="book_id from config/books.toml")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "books.toml"))
    ap.add_argument("--raw-root", default=os.path.join(ROOT, "raw", "books"))
    args = ap.parse_args()

    try:
        book = BooksConfig.load(args.config).get(args.book)
    except ConfigError as exc:
        sys.exit(str(exc))

    summary = run_ingest(book, RawWriter(args.raw_root))
    print(
        f"book={book.book_id} topic={book.topic} "
        f"seen={summary['seen']} written={summary['written']} skipped={summary['skipped']}"
    )
    for path in summary["written_paths"]:
        print(path)


if __name__ == "__main__":
    main()
