"""Slack delivery for generated recap artifacts.

The delivery boundary is deliberately narrow: read an existing recap manifest,
open the listed recap files, verify they are Recap notes, and post their body to
Slack as a dedicated bot. Recap knowledge is generated elsewhere.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .recaps import parse_frontmatter, strip_frontmatter


class SlackDeliveryError(RuntimeError):
    """Raised when a recap cannot be delivered to Slack."""


@dataclass(frozen=True)
class SlackDeliveryEntry:
    profile: str
    recap_file: str
    destination: str


@dataclass(frozen=True)
class SlackPostResult:
    channel: str
    ts: str


@dataclass(frozen=True)
class SlackDeliveryResult:
    profile: str
    recap_file: str
    destination: str
    channel: str
    ts: str


PostFn = Callable[[str, str, str], SlackPostResult]


def latest_manifest_path(repo_root: str | Path) -> Path | None:
    manifest_dir = Path(repo_root) / "recaps" / "manifests"
    manifests = sorted(manifest_dir.glob("*.json")) if manifest_dir.exists() else []
    return manifests[-1] if manifests else None


def load_manifest(path: str | Path) -> dict[str, Any]:
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SlackDeliveryError(f"recap manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SlackDeliveryError(f"recap manifest is invalid JSON: {exc}") from exc
    if manifest.get("type") != "RecapManifest" or not isinstance(manifest.get("recaps"), list):
        raise SlackDeliveryError("recap manifest must be a RecapManifest with recaps[]")
    return manifest


def slack_entries(manifest: dict[str, Any]) -> list[SlackDeliveryEntry]:
    entries: list[SlackDeliveryEntry] = []
    for recap in manifest.get("recaps", []):
        if not isinstance(recap, dict):
            continue
        profile = str(recap.get("profile", "")).strip()
        recap_file = str(recap.get("file", "")).strip()
        for delivery in recap.get("deliveries", []):
            if not isinstance(delivery, dict):
                continue
            if str(delivery.get("type", "")).strip().lower() != "slack":
                continue
            destination = str(delivery.get("destination", "")).strip()
            if not profile or not recap_file or not destination:
                raise SlackDeliveryError("slack delivery entry missing profile, file, or destination")
            entries.append(SlackDeliveryEntry(profile, recap_file, destination))
    return entries


def recap_body(repo_root: str | Path, recap_file: str) -> str:
    path = Path(repo_root) / recap_file
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SlackDeliveryError(f"recap file not found: {recap_file}") from exc
    frontmatter = parse_frontmatter(text)
    if frontmatter.get("type") != "Recap":
        raise SlackDeliveryError(f"{recap_file} must have frontmatter type: Recap")
    body = strip_frontmatter(text).strip()
    if not body:
        raise SlackDeliveryError(f"{recap_file} has no recap body to deliver")
    return body


def post_to_slack(bot_token: str, destination: str, text: str) -> SlackPostResult:
    payload = json.dumps({"channel": destination, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status < 200 or response.status >= 300:
            raise SlackDeliveryError(f"Slack API responded HTTP {response.status}")
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        error = str(result.get("error") or "unknown_error")
        hint = ""
        if error == "not_in_channel":
            hint = "; invite the Bowerbird bot to the channel or grant chat:write.public"
        raise SlackDeliveryError(f"Slack API error: {error}{hint}")
    return SlackPostResult(channel=str(result.get("channel", "")), ts=str(result.get("ts", "")))


def deliver_slack_recaps(
    repo_root: str | Path,
    manifest_path: str | Path,
    bot_token: str,
    *,
    post: PostFn = post_to_slack,
) -> list[SlackDeliveryResult]:
    manifest = load_manifest(manifest_path)
    entries = slack_entries(manifest)
    results: list[SlackDeliveryResult] = []
    for entry in entries:
        result = post(bot_token, entry.destination, recap_body(repo_root, entry.recap_file))
        results.append(
            SlackDeliveryResult(
                profile=entry.profile,
                recap_file=entry.recap_file,
                destination=entry.destination,
                channel=result.channel,
                ts=result.ts,
            )
        )
    return results
