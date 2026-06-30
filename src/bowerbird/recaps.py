"""File-first recap generation over compiled wiki source notes.

Recaps are generated files, not delivery events. A recap profile selects compiled
wiki source-note lanes, a prompt turns those notes into a human-readable body,
and delivery connectors consume the resulting files and manifest.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from collections import OrderedDict, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RecapProfile
from .model_config import ModelConfig

MAX_NOTES_PER_LANE = 8
MAX_BODY_CHARS = 1200
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(frozen=True)
class RecapWindow:
    start: dt.date | dt.datetime
    end: dt.date | dt.datetime
    label: str


@dataclass(frozen=True)
class SourceNote:
    path: str
    topic: str
    lane_kind: str
    lane_key: str
    label: str
    date: str
    text: str
    url: str = ""


@dataclass(frozen=True)
class RecapArtifact:
    profile: RecapProfile
    path: str
    content: str
    manifest_entry: dict[str, Any]


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse top-level scalar frontmatter keys from a markdown note."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}
    out: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line.strip() or line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip("\"'")
    return out


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text.strip()


def label_slug(slug: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in slug.split("-"))


def _as_utc_datetime(value: dt.date | dt.datetime) -> dt.datetime:
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)
    return dt.datetime.combine(value, dt.time.min, tzinfo=dt.UTC)


def _as_date(value: dt.date | dt.datetime) -> dt.date:
    if isinstance(value, dt.datetime):
        return _as_utc_datetime(value).date()
    return value


def _hourly_label(start: dt.datetime) -> str:
    return start.strftime("%Y-%m-%dT%H-00Z")


def window_for(profile: RecapProfile, run_date: dt.date | dt.datetime) -> RecapWindow | None:
    """Return the calendar window this run should generate for a profile.

    `run_date` is the exclusive window end in UTC calendar terms. A daily run on
    2026-06-24 summarizes 2026-06-23. A weekly run due Monday summarizes the
    previous Monday-through-Sunday window.
    """
    if profile.frequency == "hourly":
        moment = _as_utc_datetime(run_date)
        interval = profile.interval_hours
        hour = (moment.hour // interval) * interval
        start_dt = moment.replace(hour=hour, minute=0, second=0, microsecond=0)
        end_dt = start_dt + dt.timedelta(hours=interval)
        return RecapWindow(start=start_dt, end=end_dt, label=_hourly_label(start_dt))

    run_day = _as_date(run_date)
    if profile.frequency == "daily":
        start = run_day - dt.timedelta(days=1)
        return RecapWindow(start=start, end=run_day, label=start.isoformat())
    due_day = WEEKDAYS[profile.weekly_due_day]
    if run_day.weekday() != due_day:
        return None
    start = run_day - dt.timedelta(days=7)
    end_label = run_day - dt.timedelta(days=1)
    return RecapWindow(start=start, end=run_day, label=end_label.isoformat())


def _git_time(value: dt.date | dt.datetime) -> str:
    if isinstance(value, dt.datetime):
        return _as_utc_datetime(value).strftime("%Y-%m-%d %H:%M:%S +0000")
    return f"{value.isoformat()} 00:00:00 +0000"


def added_source_paths(repo_root: str | Path, window: RecapWindow) -> list[str]:
    since = _git_time(window.start)
    until = _git_time(window.end)
    out = subprocess.run(
        [
            "git",
            "log",
            f"--since={since}",
            f"--until={until}",
            "--diff-filter=A",
            "--name-only",
            "--pretty=format:",
            "--",
            "wiki/*/sources/*.md",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted({line.strip() for line in out.splitlines() if line.strip().endswith(".md")})


def _note_from_path(path: str, text: str, account_labels: dict[str, str]) -> SourceNote:
    fm = parse_frontmatter(text)
    parts = path.split("/")
    topic = parts[1] if len(parts) > 1 else "unknown"
    mirror = fm.get("mirror", "")
    date = fm.get("date") or Path(path).name[:10]
    body = strip_frontmatter(text)[:MAX_BODY_CHARS]
    url = fm.get("url") or fm.get("source_url") or ""
    if mirror.startswith("accounts/"):
        key = mirror.removeprefix("accounts/").strip("/")
        return SourceNote(
            path=path,
            topic=topic,
            lane_kind="account",
            lane_key=key,
            label=account_labels.get(key) or label_slug(key),
            date=date,
            text=body,
            url=url,
        )
    return SourceNote(
        path=path,
        topic=topic,
        lane_kind="topic",
        lane_key=topic,
        label=label_slug(topic),
        date=date,
        text=body,
        url=url,
    )


def load_source_notes(
    paths: list[str],
    read_text: Callable[[str], str],
    *,
    account_labels: dict[str, str] | None = None,
) -> list[SourceNote]:
    labels = account_labels or {}
    notes: list[SourceNote] = []
    for path in paths:
        try:
            notes.append(_note_from_path(path, read_text(path), labels))
        except OSError:
            continue
    return notes


def select_notes(profile: RecapProfile, notes: list[SourceNote]) -> list[SourceNote]:
    accounts = {item.lower() for item in profile.accounts}
    topics = set(profile.topics)
    selected = []
    for note in notes:
        if note.lane_kind == "account" and note.lane_key.lower() in accounts:
            selected.append(note)
        elif note.lane_kind == "topic" and note.lane_key in topics:
            selected.append(note)
    return selected


def group_notes(notes: list[SourceNote]) -> OrderedDict[str, dict[str, Any]]:
    grouped: dict[str, list[SourceNote]] = defaultdict(list)
    labels: dict[str, str] = {}
    kinds: dict[str, str] = {}
    for note in notes:
        lane_id = f"{note.lane_kind}:{note.lane_key}"
        grouped[lane_id].append(note)
        labels[lane_id] = note.label
        kinds[lane_id] = note.lane_kind

    ordered: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for lane_id, lane_notes in sorted(
        grouped.items(),
        key=lambda item: max((n.date, n.path) for n in item[1]),
        reverse=True,
    ):
        lane_notes.sort(key=lambda n: (n.date, n.path), reverse=True)
        ordered[lane_id] = {
            "kind": kinds[lane_id],
            "key": lane_id.split(":", 1)[1],
            "label": labels[lane_id],
            "total_new": len(lane_notes),
            "notes": lane_notes[:MAX_NOTES_PER_LANE],
        }
    return ordered


def build_model_prompt(profile: RecapProfile, prompt_text: str, lanes: OrderedDict[str, dict[str, Any]],
                       window: RecapWindow) -> tuple[str, str]:
    digest_parts = []
    total_new = 0
    account_lanes = 0
    topic_lanes = 0
    for lane in lanes.values():
        total_new += lane["total_new"]
        if lane["kind"] == "account":
            account_lanes += 1
        elif lane["kind"] == "topic":
            topic_lanes += 1
        note_lines = []
        for note in lane["notes"]:
            url = f" url={note.url}" if profile.include_urls and note.url else ""
            note_lines.append(f"- [{note.date}]{url} {note.text}")
        digest_parts.append(
            f"### {lane['kind']}: {lane['label']} ({lane['key']}, "
            f"total_new={lane['total_new']})\n" + "\n".join(note_lines)
        )
    user = (
        f"Recap profile: {profile.name}\n"
        f"Frequency: {profile.frequency}\n"
        f"Output format: {profile.output_format}\n"
        f"Window: {window.start.isoformat()} through {window.end.isoformat()} "
        f"(end exclusive)\n"
        f"Date label: {window.label}\n"
        f"Total new source notes: {total_new}\n"
        f"Account lanes: {account_lanes}\n"
        f"Topic lanes: {topic_lanes}\n\n"
        "Compiled wiki lanes with new source notes:\n\n"
        + "\n\n".join(digest_parts)
        + "\n\nWrite the single recap now. Output only the recap body. "
        "Use one tight line per lane, plus a compact footer with total counts "
        "and 3-5 keywords or commands. Do not include source citations or frontmatter."
    )
    return prompt_text, user


def _first_signal(text: str) -> str:
    first = next((line.strip(" -") for line in text.splitlines() if line.strip()), "")
    return first[:220].rstrip()


def _footer_counts(total_new: int, account_lanes: int, topic_lanes: int) -> str:
    parts = [f"{total_new} new note{'s' if total_new != 1 else ''}"]
    if account_lanes:
        parts.append(f"{account_lanes} account lane{'s' if account_lanes != 1 else ''}")
    if topic_lanes:
        parts.append(f"{topic_lanes} topic lane{'s' if topic_lanes != 1 else ''}")
    return " | ".join(parts)


def deterministic_body(profile: RecapProfile, _prompt_text: str,
                       lanes: OrderedDict[str, dict[str, Any]],
                       window: RecapWindow) -> str:
    """Test/local fallback body generator with no model call."""
    slack = profile.output_format == "slack_mrkdwn"
    title = f"Knowledge Base - {profile.frequency} recap - {window.label}"
    lines = [f"*{title}*" if slack else f"# {title}"]
    total_new = 0
    account_lanes = 0
    topic_lanes = 0
    for lane in lanes.values():
        total_new += lane["total_new"]
        if lane["kind"] == "account":
            account_lanes += 1
        elif lane["kind"] == "topic":
            topic_lanes += 1
        shown = [_first_signal(note.text) for note in lane["notes"][:2]]
        signals = [value for value in shown if value]
        signal = " ".join(signals) if signals else "New source notes were added."
        if profile.include_urls:
            urls = [note.url for note in lane["notes"][:2] if note.url]
            if urls:
                signal = f"{signal} " + " ".join(urls)
        lines.append("")
        if slack:
            lines.append(f"*{lane['label']}:* {signal}")
        else:
            lines.append(f"**{lane['label']}:** {signal}")
    lines.append("")
    lines.append(f"_{_footer_counts(total_new, account_lanes, topic_lanes)}_")
    return "\n".join(lines).strip()


def _yaml_value(value: str | int | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(value)


def _frontmatter(profile: RecapProfile, window: RecapWindow, lanes: OrderedDict[str, dict[str, Any]],
                 source_paths: list[str], model: ModelConfig, generated_at: str) -> str:
    account_lanes = [lane["key"] for lane in lanes.values() if lane["kind"] == "account"]
    topic_lanes = [lane["key"] for lane in lanes.values() if lane["kind"] == "topic"]
    lines = [
        "---",
        "type: Recap",
        f"profile: {_yaml_value(profile.name)}",
        f"frequency: {_yaml_value(profile.frequency)}",
        f"format: {_yaml_value(profile.output_format)}",
        f"window_start: {_yaml_value(window.start.isoformat())}",
        f"window_end: {_yaml_value(window.end.isoformat())}",
        f"generated_at: {_yaml_value(generated_at)}",
        f"model_provider: {_yaml_value(model.provider)}",
        f"model: {_yaml_value(model.recap_model_effective)}",
        f"prompt_path: {_yaml_value(profile.prompt_path)}",
        f"include_urls: {_yaml_value(profile.include_urls)}",
        "totals:",
        f"  source_notes: {len(source_paths)}",
        f"  account_lanes: {len(account_lanes)}",
        f"  topic_lanes: {len(topic_lanes)}",
        "selected:",
        "  accounts:",
        *[f"    - {_yaml_value(value)}" for value in account_lanes],
        "  topics:",
        *[f"    - {_yaml_value(value)}" for value in topic_lanes],
        "source_notes:",
        *[f"  - {_yaml_value(path)}" for path in source_paths],
        "deliveries:",
    ]
    for delivery in profile.deliveries:
        lines += [
            f"  - type: {_yaml_value(delivery.kind)}",
            f"    destination: {_yaml_value(delivery.destination)}",
        ]
    lines.append("---")
    return "\n".join(lines)


def build_recap_artifact(
    profile: RecapProfile,
    notes: list[SourceNote],
    *,
    window: RecapWindow,
    read_prompt: Callable[[str], str],
    synthesize: Callable[[RecapProfile, str, OrderedDict[str, dict[str, Any]], RecapWindow], str],
    model: ModelConfig,
    generated_at: str,
) -> RecapArtifact | None:
    selected = select_notes(profile, notes)
    if not selected:
        return None
    lanes = group_notes(selected)
    source_paths = [note.path for note in sorted(selected, key=lambda n: n.path)]
    prompt_text = read_prompt(profile.prompt_path)
    body = synthesize(profile, prompt_text, lanes, window).strip()
    if not body:
        return None
    path = f"recaps/{profile.name}/{window.label}.md"
    content = (
        _frontmatter(profile, window, lanes, source_paths, model, generated_at)
        + "\n\n"
        + body
        + "\n"
    )
    return RecapArtifact(
        profile=profile,
        path=path,
        content=content,
        manifest_entry={
            "profile": profile.name,
            "file": path,
            "format": profile.output_format,
            "frequency": profile.frequency,
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
            "totals": {
                "source_notes": len(source_paths),
                "account_lanes": sum(1 for lane in lanes.values() if lane["kind"] == "account"),
                "topic_lanes": sum(1 for lane in lanes.values() if lane["kind"] == "topic"),
            },
            "deliveries": [
                {"type": delivery.kind, "destination": delivery.destination}
                for delivery in profile.deliveries
            ],
        },
    )


def build_recap_artifacts(
    profiles: list[RecapProfile],
    notes: list[SourceNote],
    *,
    run_date: dt.date,
    read_prompt: Callable[[str], str],
    synthesize: Callable[[RecapProfile, str, OrderedDict[str, dict[str, Any]], RecapWindow], str],
    model: ModelConfig,
    generated_at: str,
) -> list[RecapArtifact]:
    artifacts: list[RecapArtifact] = []
    for profile in profiles:
        window = window_for(profile, run_date)
        if window is None:
            continue
        artifact = build_recap_artifact(
            profile,
            notes,
            window=window,
            read_prompt=read_prompt,
            synthesize=synthesize,
            model=model,
            generated_at=generated_at,
        )
        if artifact is not None:
            artifacts.append(artifact)
    return artifacts


def manifest_for(artifacts: list[RecapArtifact], *, run_date: dt.date | str, generated_at: str) -> dict[str, Any]:
    run_label = run_date.isoformat() if hasattr(run_date, "isoformat") else str(run_date)
    return {
        "type": "RecapManifest",
        "run_date": run_label,
        "generated_at": generated_at,
        "recaps": [artifact.manifest_entry for artifact in artifacts],
    }


def manifest_path(run_date: dt.date | str) -> str:
    run_label = run_date.isoformat() if hasattr(run_date, "isoformat") else str(run_date)
    return f"recaps/manifests/{run_label}.json"


REQUIRED_RECAP_KEYS = {
    "type",
    "profile",
    "frequency",
    "format",
    "window_start",
    "window_end",
    "generated_at",
    "model_provider",
    "model",
    "prompt_path",
}


def validate_recap_files(repo_root: str | Path) -> list[str]:
    root = Path(repo_root)
    issues: list[str] = []
    recaps_dir = root / "recaps"
    if not recaps_dir.exists():
        return issues
    for path in sorted(recaps_dir.glob("*/*.md")):
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        missing = sorted(REQUIRED_RECAP_KEYS - set(fm))
        if missing:
            issues.append(f"{path.relative_to(root)} missing frontmatter: {', '.join(missing)}")
        elif fm.get("type") != "Recap":
            issues.append(f"{path.relative_to(root)} has type {fm.get('type')!r}, expected 'Recap'")
    for path in sorted((recaps_dir / "manifests").glob("*.json")) if (recaps_dir / "manifests").exists() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(f"{path.relative_to(root)} invalid JSON: {exc}")
            continue
        if data.get("type") != "RecapManifest" or not isinstance(data.get("recaps"), list):
            issues.append(f"{path.relative_to(root)} must be a RecapManifest with recaps[]")
    return issues


def profile_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]*", value))
