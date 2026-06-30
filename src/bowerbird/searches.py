"""Search monitor config helpers for the `bowerbird searches` CLI."""
from __future__ import annotations

import tomllib
from pathlib import Path

from .config import ConfigError, SearchesConfig


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def load_search_rows(text: str) -> list[dict[str, str | int]]:
    if not text.strip():
        return []
    raw = tomllib.loads(text).get("searches", [])
    if not raw:
        return []
    if not isinstance(raw, list):
        raise ConfigError("searches config must use [[searches]] tables")

    rows: list[dict[str, str | int]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise ConfigError(f"search config entry must be a table, got {entry!r}")
        row: dict[str, str | int] = {
            "name": str(entry.get("name", "")).strip(),
            "topic": str(entry.get("topic", "")).strip(),
            "query": str(entry.get("query", "")).strip(),
            "lookback_hours": int(entry.get("lookback_hours", 24)),
            "max_results": int(entry.get("max_results", 10)),
            "max_pages": int(entry.get("max_pages", 1)),
        }
        label = str(entry.get("label", "")).strip()
        if label:
            row["label"] = label
        rows.append(row)

    SearchesConfig.from_dict({"searches": rows})
    return rows


def render_searches_toml(rows: list[dict[str, str | int]]) -> str:
    lines = ["# X Recent Search monitors. Managed by Bowerbird.", ""]
    for row in rows:
        lines += [
            "[[searches]]",
            f"name = {_toml_string(str(row['name']))}",
            f"topic = {_toml_string(str(row['topic']))}",
            f"query = {_toml_string(str(row['query']))}",
        ]
        if row.get("label"):
            lines.append(f"label = {_toml_string(str(row['label']))}")
        lines += [
            f"lookback_hours = {int(row.get('lookback_hours', 24))}",
            f"max_results = {int(row.get('max_results', 10))}",
            f"max_pages = {int(row.get('max_pages', 1))}",
            "",
        ]
    return "\n".join(lines)


def add_search_to_text(
    text: str,
    name: str,
    *,
    topic: str,
    query: str,
    label: str | None = None,
    lookback_hours: int = 24,
    max_results: int = 10,
    max_pages: int = 1,
) -> tuple[str, bool]:
    row = {
        "name": name.strip(),
        "topic": topic.strip(),
        "query": query.strip(),
        "lookback_hours": lookback_hours,
        "max_results": max_results,
        "max_pages": max_pages,
    }
    clean_label = (label or "").strip()
    if clean_label:
        row["label"] = clean_label
    SearchesConfig.from_dict({"searches": [row]})

    rows = load_search_rows(text)
    for existing in rows:
        if str(existing["name"]) == str(row["name"]):
            return render_searches_toml(rows), False

    rows.append(row)
    return render_searches_toml(rows), True


def add_search(
    path: str | Path,
    name: str,
    *,
    topic: str,
    query: str,
    label: str | None = None,
    lookback_hours: int = 24,
    max_results: int = 10,
    max_pages: int = 1,
) -> tuple[bool, str]:
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    rendered, added = add_search_to_text(
        text,
        name,
        topic=topic,
        query=query,
        label=label,
        lookback_hours=lookback_hours,
        max_results=max_results,
        max_pages=max_pages,
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(rendered, encoding="utf-8")
    return added, name.strip()
