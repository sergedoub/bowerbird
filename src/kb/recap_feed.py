"""Recap feed builder — the day's new wiki source notes, grouped into recap lanes.

This is the contract between the pipeline and every recap consumer (Slack agent, web
app, anything else): compile/recap-feed.json. Lanes:

- accounts: notes whose frontmatter says `mirror: accounts/<handle>` (account mirrors)
- topics:   every other new source note, grouped by wiki topic directory

"New" means ADDED to the wiki in the window (a git fact computed by the caller), not
the original post date — a note's filename carries its post date, which lags its
wiki-add date when the compile catches up on a backlog.

Pure core over injected file reading; bin/recap_feed.py wires git and the filesystem.
Account display labels come from config/accounts.toml (optional `label` per handle).
"""
from __future__ import annotations

from collections import OrderedDict, defaultdict
from collections.abc import Callable

from .raw_sources import parse_raw_path

MAX_NOTES_PER_LANE = 8   # cap so the feed (and a recap agent's single read) stays small
MAX_BODY_CHARS = 1200    # truncate any one note body


def parse_frontmatter(text: str) -> dict:
    """Top-level scalar keys of a leading --- YAML block (good enough for our notes)."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}
    out = {}
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


def origin_from_frontmatter(fm: dict) -> str | None:
    origin = fm.get("origin", "").strip()
    if origin:
        return origin
    raw_path = fm.get("raw_path", "").strip()
    info = parse_raw_path(raw_path) if raw_path else None
    if info is not None:
        return info.namespace
    mirror = fm.get("mirror", "")
    if mirror.startswith("accounts/"):
        return "accounts"
    if fm.get("source_type") == "book-chapter":
        return "books"
    return "bookmarks"


def build_note(date: str, path: str, body: str, fm: dict) -> dict:
    note = {"date": date, "file": path, "text": body}
    origin = origin_from_frontmatter(fm)
    if origin:
        note["origin"] = origin
    for key in ("source_type", "raw_path"):
        if fm.get(key):
            note[key] = fm[key]
    return note


def build_feed(
    added_paths: list[str],
    read_text: Callable[[str], str],
    *,
    today: str,
    labels: dict[str, str] | None = None,
    window_hours: int = 24,
    max_notes: int = MAX_NOTES_PER_LANE,
    max_body: int = MAX_BODY_CHARS,
) -> dict:
    """Build the recap feed dict from the paths added in the window.

    `added_paths` are repo-relative `wiki/<topic>/sources/*.md` paths; unreadable paths
    are skipped (deleted between git log and read). `labels` maps handle -> display name.
    """
    labels = labels or {}
    lanes: dict[str, dict[str, list]] = {
        "accounts": defaultdict(list),
        "topics": defaultdict(list),
    }
    for p in added_paths:
        try:
            text = read_text(p)
        except OSError:
            continue
        fm = parse_frontmatter(text)
        parts = p.split("/")
        topic = parts[1] if len(parts) > 1 else "unknown"
        date = fm.get("date") or p.rsplit("/", 1)[-1][:10]
        mirror = fm.get("mirror", "")
        item = build_note(date, p, strip_frontmatter(text)[:max_body], fm)
        if mirror.startswith("accounts/"):
            handle = mirror.removeprefix("accounts/").strip("/")
            lanes["accounts"][handle].append(item)
        else:
            lanes["topics"][topic].append(item)

    # Inline note CONTENT into the feed so a recap consumer reads ONE file.
    feed_lanes: dict[str, OrderedDict] = {}
    for group, grouped in lanes.items():
        out: OrderedDict = OrderedDict()
        for key, items in sorted(grouped.items(),
                                 key=lambda kv: max(item["date"] for item in kv[1]), reverse=True):
            items.sort(key=lambda item: (item["date"], item["file"]), reverse=True)
            notes = items[:max_notes]
            label = labels.get(key) or label_slug(key)
            out[key] = {"label": label, "total_new": len(items), "notes": notes}
        feed_lanes[group] = out

    total = sum(v["total_new"] for group in feed_lanes.values() for v in group.values())
    return {
        "generated": today,
        "window_hours": window_hours,
        "accounts": feed_lanes["accounts"],
        "topics": feed_lanes["topics"],
        "summary": {
            "total_new": total,
            "account_lanes": len(feed_lanes["accounts"]),
            "topic_lanes": len(feed_lanes["topics"]),
        },
    }
