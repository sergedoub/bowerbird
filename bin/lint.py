#!/usr/bin/env python3
"""Run ProvenanceLinter over every topic's wiki. Exit nonzero if any violations.

Used by the compile workflow as the guardrail: the compile agent must make this pass
before its output ships.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.linter import lint, okf_conformance  # noqa: E402
from kb.recaps import validate_recap_files  # noqa: E402


def main() -> None:
    topics_dir = os.path.join(ROOT, "wiki")
    violations = []
    if os.path.isdir(topics_dir):
        for topic in sorted(os.listdir(topics_dir)):
            wiki = os.path.join(topics_dir, topic)
            if not os.path.isdir(wiki):
                continue
            for v in lint(wiki, repo_root=ROOT):
                print(f"[{topic}] {v.kind}: {os.path.relpath(v.path, ROOT)} :: {v.message}")
                violations.append(v)
            for v in okf_conformance(wiki):
                print(f"[{topic}] {v.kind}: {os.path.relpath(v.path, ROOT)} :: {v.message}")
                violations.append(v)
    for issue in validate_recap_files(ROOT):
        print(f"[recaps] recap: {issue}")
        violations.append(issue)
    if violations:
        print(f"\n{len(violations)} provenance/recap violation(s) — fix before shipping.")
        sys.exit(1)
    print("provenance and recaps OK")


if __name__ == "__main__":
    main()
