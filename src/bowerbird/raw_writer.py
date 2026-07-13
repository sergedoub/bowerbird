"""RawWriter — append-only, idempotent writes into a raw namespace.

`raw/` is the sacred ground-truth layer: never mutated, never deleted. Filenames are
deterministic (date + stable id), so re-running the pull over already-seen bookmarks
is a no-op (write() returns None) rather than producing duplicates.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .models import RawDoc
from .raw_sources import namespace_for


_RAW_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _validate_component(label: str, value: str) -> None:
    if not _RAW_COMPONENT.fullmatch(value):
        raise ValueError(
            f"raw {label} must start with a letter or number and contain only "
            "letters, numbers, dots, underscores, and hyphens"
        )


def _topic_components(value: str) -> tuple[str, ...]:
    """Accept a topic slug or the legacy <namespace>/<bucket> address form."""
    if "\\" in value:
        raise ValueError("raw topic must be a topic slug or namespace/bucket path")
    parts = tuple(value.split("/"))
    if len(parts) not in {1, 2}:
        raise ValueError("raw topic must be a topic slug or namespace/bucket path")
    if len(parts) == 2 and namespace_for(parts[0]) is None:
        raise ValueError("raw topic namespace must be declared")
    for part in parts:
        _validate_component("topic", part)
    return parts


def _date_prefix(created_at: str) -> str:
    value = created_at[:10]
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("raw created_at must begin with a valid YYYY-MM-DD date") from exc
    if value != parsed.isoformat():
        raise ValueError("raw created_at must begin with a valid YYYY-MM-DD date")
    return value


def _fm_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    s = str(v)
    # Quote values that could confuse a YAML frontmatter parser.
    if s == "" or s[0] in "@`" or any(c in s for c in ":#\n") or s.strip() != s:
        return '"' + s.replace('"', '\\"') + '"'
    return s


def render(doc: RawDoc) -> str:
    """Markdown with a YAML frontmatter block. Deterministic key order."""
    lines = ["---"]
    for key in sorted(doc.frontmatter):
        lines.append(f"{key}: {_fm_value(doc.frontmatter[key])}")
    lines.append("---")
    lines.append("")
    lines.append(doc.body.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


class RawWriter:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def path_for(self, doc: RawDoc) -> Path:
        date = _date_prefix(doc.created_at)
        if doc.address is not None:
            _validate_component("namespace", doc.address.namespace)
            if namespace_for(doc.address.namespace) is None:
                raise ValueError(f"raw namespace '{doc.address.namespace}' is not declared")
            _validate_component("bucket", doc.address.bucket)
            components = (doc.address.namespace, doc.address.bucket)
        else:
            components = _topic_components(doc.topic)
        _validate_component("id", doc.id)

        root = self._root.resolve()
        candidate = root.joinpath(*components, f"{date}__{doc.id}.md").resolve()
        if candidate == root or not candidate.is_relative_to(root):
            raise ValueError("raw output path resolves outside the configured raw root")
        return candidate

    def write(self, doc: RawDoc) -> Path | None:
        """Write the doc; return its path, or None if it already exists (dedup)."""
        path = self.path_for(doc)
        if path.exists():
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(doc))
        return path
