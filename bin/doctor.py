#!/usr/bin/env python3
"""Text-first health check for a Bowerbird checkout."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.health import HealthCheck, LintStatus, report_to_text  # noqa: E402


def run_lint() -> LintStatus:
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "lint.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return LintStatus(proc.returncode, (proc.stdout + proc.stderr).strip())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog=os.environ.get("BOWERBIRD_PROG", "bowerbird doctor"),
        description="Check config, recap feed freshness, and provenance lint status.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--stale-after-days",
        type=int,
        default=14,
        help="warn when compile/recap-feed.json is older than this many days",
    )
    ns = parser.parse_args(argv)

    report = HealthCheck(stale_after_days=ns.stale_after_days).check(
        ROOT,
        lint_status=run_lint(),
    )
    if ns.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(report_to_text(report))
    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
