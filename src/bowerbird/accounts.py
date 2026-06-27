"""Account config helpers for the `bowerbird accounts` CLI."""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

from .config import OFF_TOPIC_POLICIES, AccountsConfig, ConfigError


def slug_topic(value: str) -> str:
    cleaned = "".join(
        c if c.isalnum() or c in "-_" else "-"
        for c in value.strip().lower()
    )
    return re.sub(r"-+", "-", cleaned).strip("-") or "account"


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def load_account_rows(text: str) -> list[dict[str, str]]:
    if not text.strip():
        return []
    raw = tomllib.loads(text).get("handles", [])
    if not raw:
        return []
    if not isinstance(raw, list):
        raise ConfigError("accounts config must use [[handles]] tables")

    rows: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise ConfigError(
                f"accounts config entry must be a table with handle+topic, got {entry!r}"
            )
        row = {
            "handle": str(entry.get("handle", "")).lstrip("@").strip(),
            "topic": str(entry.get("topic", "")).strip(),
            "off_topic": str(entry.get("off_topic", "skip")).strip() or "skip",
        }
        label = str(entry.get("label", "")).strip()
        if label:
            row["label"] = label
        rows.append(row)

    AccountsConfig.from_dict({"handles": rows})
    return rows


def render_accounts_toml(rows: list[dict[str, str]]) -> str:
    lines = ["# X accounts to follow. Managed by Bowerbird.", ""]
    for row in rows:
        lines += [
            "[[handles]]",
            f"handle = {_toml_string(row['handle'])}",
            f"topic = {_toml_string(row['topic'])}",
            f"off_topic = {_toml_string(row.get('off_topic') or 'skip')}",
        ]
        if row.get("label"):
            lines.append(f"label = {_toml_string(row['label'])}")
        lines.append("")
    return "\n".join(lines)


def add_account_to_text(
    text: str,
    handle: str,
    *,
    topic: str | None = None,
    label: str | None = None,
    off_topic: str = "skip",
) -> tuple[str, bool]:
    normalized = handle.lstrip("@").strip()
    if not normalized:
        raise ConfigError("account handle is required")
    target_topic = slug_topic(topic or normalized)
    policy = off_topic.strip() or "skip"
    if policy not in OFF_TOPIC_POLICIES:
        raise ConfigError(
            f"unknown off_topic policy '{policy}' for '{normalized}' "
            f"(expected one of {OFF_TOPIC_POLICIES})"
        )

    rows = load_account_rows(text)
    for row in rows:
        if row["handle"].lower() == normalized.lower():
            return render_accounts_toml(rows), False

    row = {"handle": normalized, "topic": target_topic, "off_topic": policy}
    clean_label = (label or "").strip()
    if clean_label:
        row["label"] = clean_label
    rows.append(row)
    return render_accounts_toml(rows), True


def add_account(
    path: str | Path,
    handle: str,
    *,
    topic: str | None = None,
    label: str | None = None,
    off_topic: str = "skip",
) -> tuple[bool, str]:
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    rendered, added = add_account_to_text(
        text, handle, topic=topic, label=label, off_topic=off_topic
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(rendered, encoding="utf-8")
    normalized = handle.lstrip("@").strip()
    return added, normalized
