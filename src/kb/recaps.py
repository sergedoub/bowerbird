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
    start: dt.date
    end: dt.date
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


def window_for(profile: RecapProfile, run_date: dt.date) -> RecapWindow | None:
    """Return the calendar window this run should generate for a profile.

    `run_date` is the exclusive window end in UTC calendar terms. A daily run on
    2026-06-24 summarizes 2026-06-23. A weekly run due Monday summarizes the
    previous Monday-through-Sunday window.
    """
    if profile.frequency == "daily":
        start = run_date - dt.timedelta(days=1)
        return RecapWindow(start=start, end=run_date, label=start.isoformat())
    due_day = WEEKDAYS[profile.weekly_due_day]
    if run_date.weekday() != due_day:
        return None
    start = run_date - dt.timedelta(days=7)
    end_label = run_date - dt.timedelta(days=1)
    return RecapWindow(start=start, end=run_date, label=end_label.isoformat())


def added_source_paths(repo_root: str | Path, window: RecapWindow) -> list[str]:
    since = f"{window.start.isoformat()} 00:00:00 +0000"
    until = f"{window.end.isoformat()} 00:00:00 +0000"
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
        )
    return SourceNote(
        path=path,
        topic=topic,
        lane_kind="topic",
        lane_key=topic,
        label=label_slug(topic),
        date=date,
        text=body,
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
    for lane in lanes.values():
        note_lines = [
            f"- [{note.date}] {note.text}"
            for note in lane["notes"]
        ]
        digest_parts.append(
            f"### {lane['kind']}: {lane['label']} ({lane['key']}, "
            f"total_new={lane['total_new']})\n" + "\n".join(note_lines)
        )
    user = (
        f"Recap profile: {profile.name}\n"
        f"Frequency: {profile.frequency}\n"
        f"Output format: {profile.output_format}\n"
        f"Window: {window.start.isoformat()} through {window.end.isoformat()} "
        f"(end exclusive)\n\n"
        "Compiled wiki lanes with new source notes:\n\n"
        + "\n\n".join(digest_parts)
        + "\n\nWrite only the recap body. Do not include source citations or frontmatter."
    )
    return prompt_text, user


def deterministic_body(profile: RecapProfile, _prompt_text: str,
                       lanes: OrderedDict[str, dict[str, Any]],
                       window: RecapWindow) -> str:
    """Test/local fallback body generator with no model call."""
    lines = [f"{profile.name} recap - {window.label}"]
    for lane in lanes.values():
        lines.append("")
        lines.append(f"*{lane['label']}*")
        lines.append(f"{lane['total_new']} new source note(s).")
        for note in lane["notes"][:2]:
            first = next((line.strip() for line in note.text.splitlines() if line.strip()), "")
            if first:
                lines.append(f"- {first[:180]}")
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


def manifest_for(artifacts: list[RecapArtifact], *, run_date: dt.date, generated_at: str) -> dict[str, Any]:
    return {
        "type": "RecapManifest",
        "run_date": run_date.isoformat(),
        "generated_at": generated_at,
        "recaps": [artifact.manifest_entry for artifact in artifacts],
    }


def manifest_path(run_date: dt.date) -> str:
    return f"recaps/manifests/{run_date.isoformat()}.json"


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
