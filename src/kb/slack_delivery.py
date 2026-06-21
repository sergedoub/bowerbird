"""Slack recap delivery over the recap-feed contract."""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryDecision:
    deliver: bool
    quiet: bool = False
    reason: str = ""


def should_deliver(feed: dict | None, today: str, *, quiet_message_on_empty: bool) -> DeliveryDecision:
    if not feed:
        return DeliveryDecision(False, reason="no recap feed in the repo yet")
    generated = str(feed.get("generated", ""))
    if generated != today:
        return DeliveryDecision(False, reason=f"stale feed: generated {generated}, today is {today}")
    total_new = int(feed.get("summary", {}).get("total_new", 0))
    if total_new == 0:
        if quiet_message_on_empty:
            return DeliveryDecision(True, quiet=True)
        return DeliveryDecision(False, reason="no new notes in the window")
    return DeliveryDecision(True)


def quiet_message(feed: dict) -> str:
    return (
        f"Daily Knowledge Base Recap — {feed['generated']}\n\n"
        f"A quiet day: no new source notes in the last {feed.get('window_hours', 24)}h."
    )


def mechanical_recap(feed: dict) -> str:
    lines = [f"Daily Knowledge Base Recap — {feed['generated']}"]
    for group, heading in (("accounts", "Accounts"), ("topics", "Topics")):
        lanes = list(feed.get(group, {}).values())
        if not lanes:
            continue
        lines.extend(["", f"*{heading}*"])
        for lane in lanes:
            lines.append(f"- {lane['label']}: {lane['total_new']} new note(s)")
            for note in lane.get("notes", [])[:3]:
                lines.append(f"  - ({note['date']}) {_first_line(note.get('text', ''))}")
    return "\n".join(lines)


def post_to_slack(webhook_url: str, text: str) -> None:
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"Slack webhook responded {response.status}")


def _first_line(text: str) -> str:
    line = next((item.strip() for item in text.splitlines() if item.strip()), "")
    return f"{line[:157]}..." if len(line) > 160 else line
