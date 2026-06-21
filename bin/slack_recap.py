#!/usr/bin/env python3
"""Post compile/recap-feed.json to Slack via SLACK_WEBHOOK_URL."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.slack_delivery import mechanical_recap, post_to_slack, quiet_message, should_deliver  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", default=os.path.join(ROOT, "compile", "recap-feed.json"))
    parser.add_argument("--today", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("slack recap skipped: SLACK_WEBHOOK_URL not set")
        return

    try:
        with open(args.feed) as f:
            feed = json.load(f)
    except FileNotFoundError:
        print("slack recap skipped: no recap feed in the repo yet")
        return

    decision = should_deliver(
        feed,
        args.today,
        quiet_message_on_empty=os.environ.get("RECAP_QUIET_MESSAGE") == "true",
    )
    if not decision.deliver:
        print(f"slack recap skipped: {decision.reason}")
        return

    text = quiet_message(feed) if decision.quiet else mechanical_recap(feed)
    post_to_slack(webhook_url, text)
    print(
        f"slack recap delivered: total_new={feed.get('summary', {}).get('total_new', 0)} "
        f"quiet={str(decision.quiet).lower()}"
    )


if __name__ == "__main__":
    main()
