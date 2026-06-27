"""RawWriter — append-only, idempotent writes into a raw namespace.

`raw/` is the sacred ground-truth layer: never mutated, never deleted. Filenames are
deterministic (date + stable id), so re-running the pull over already-seen bookmarks
is a no-op (write() returns None) rather than producing duplicates.
"""
from __future__ import annotations

from pathlib import Path

from .models import RawDoc


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
        date = doc.created_at[:10]  # YYYY-MM-DD
        if doc.address is not None:
            return self._root / doc.address.namespace / doc.address.bucket / f"{date}__{doc.id}.md"
        return self._root / doc.topic / f"{date}__{doc.id}.md"

    def write(self, doc: RawDoc) -> Path | None:
        """Write the doc; return its path, or None if it already exists (dedup)."""
        path = self.path_for(doc)
        if path.exists():
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(doc))
        return path
