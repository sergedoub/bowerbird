#!/usr/bin/env python3
"""Print the deterministic manifest for the next bounded wiki compile."""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bowerbird.compile_plan import build_compile_manifest, manifest_prompt  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=os.environ.get("BOWERBIRD_PROG", "bowerbird compile-manifest"),
        description="Build the bounded compile manifest used before invoking an LLM runner.",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="emit the manifest as an instruction block suitable for appending to compile/PROMPT.md",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="print only the number of uncompiled raw items",
    )
    args = parser.parse_args()

    manifest = build_compile_manifest(ROOT)
    if args.count:
        print(manifest["total_new"])
    elif args.prompt:
        print(manifest_prompt(manifest))
    else:
        print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
