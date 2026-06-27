#!/usr/bin/env python3
"""Deliver generated recap files to Slack with the Bowerbird bot token."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.slack_delivery import (  # noqa: E402
    SlackDeliveryError,
    deliver_slack_recaps,
    latest_manifest_path,
    load_manifest,
    slack_entries,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog=os.environ.get("BOWERBIRD_PROG", "bowerbird slack-recap"),
        description="Post generated recap files to Slack using SLACK_BOT_TOKEN.",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="recap manifest to deliver; defaults to latest recaps/manifests/*.json",
    )
    ns = parser.parse_args(argv)

    try:
        manifest_path = Path(ns.manifest) if ns.manifest else latest_manifest_path(ROOT)
        if manifest_path is None:
            print("slack recap: no recap manifest found")
            return
        if not manifest_path.is_absolute():
            manifest_path = Path(ROOT) / manifest_path
        manifest = load_manifest(manifest_path)
        entries = slack_entries(manifest)
        if not entries:
            print(f"slack recap: no Slack deliveries in {manifest_path}")
            return
        bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
        if not bot_token:
            sys.exit("slack recap not configured: set the SLACK_BOT_TOKEN secret")
        results = deliver_slack_recaps(ROOT, manifest_path, bot_token)
    except SlackDeliveryError as exc:
        sys.exit(str(exc))

    for result in results:
        print(
            "slack recap delivered: "
            f"profile={result.profile} file={result.recap_file} "
            f"destination={result.destination} channel={result.channel} ts={result.ts}"
        )


if __name__ == "__main__":
    main()
