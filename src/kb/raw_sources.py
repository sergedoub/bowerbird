"""Declared raw-source namespaces.

The directory shape under raw/ is storage, not semantics. This registry is the
contract that tells compile/lint code which namespaces exist, what their bucket
means, and whether they are eligible for unattended compile.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BUCKET_TOPIC = "topic"
BUCKET_ACCOUNT = "account"
BUCKET_MAPPED = "mapped"

COMPILE_AUTO = "auto"
COMPILE_REVIEW = "review"
COMPILE_SNAPSHOT_ONLY = "snapshot_only"

LOCATOR_NONE = "none"
LOCATOR_PAGE = "page"


@dataclass(frozen=True)
class RawNamespace:
    name: str
    bucket_kind: str
    compile_state: str
    default_source_type: str
    default_provenance: str
    locator_required: str = LOCATOR_NONE

    @property
    def auto_compile(self) -> bool:
        return self.compile_state == COMPILE_AUTO


@dataclass(frozen=True)
class RawPathInfo:
    namespace: str
    bucket: str
    filename: str


RAW_NAMESPACES: dict[str, RawNamespace] = {
    "bookmarks": RawNamespace(
        name="bookmarks",
        bucket_kind=BUCKET_TOPIC,
        compile_state=COMPILE_AUTO,
        default_source_type="x-post",
        default_provenance="external-expert",
    ),
    "accounts": RawNamespace(
        name="accounts",
        bucket_kind=BUCKET_ACCOUNT,
        compile_state=COMPILE_AUTO,
        default_source_type="x-post",
        default_provenance="first-party",
    ),
    "books": RawNamespace(
        name="books",
        bucket_kind=BUCKET_TOPIC,
        compile_state=COMPILE_AUTO,
        default_source_type="book-chapter",
        default_provenance="external-expert",
    ),
    "notes": RawNamespace(
        name="notes",
        bucket_kind=BUCKET_TOPIC,
        compile_state=COMPILE_AUTO,
        default_source_type="markdown-note",
        default_provenance="first-party",
    ),
    "clips": RawNamespace(
        name="clips",
        bucket_kind=BUCKET_TOPIC,
        compile_state=COMPILE_AUTO,
        default_source_type="web-clip",
        default_provenance="external-expert",
    ),
    "pdfs": RawNamespace(
        name="pdfs",
        bucket_kind=BUCKET_TOPIC,
        compile_state=COMPILE_REVIEW,
        default_source_type="pdf-extract",
        default_provenance="external-expert",
        locator_required=LOCATOR_PAGE,
    ),
    "chats": RawNamespace(
        name="chats",
        bucket_kind=BUCKET_MAPPED,
        compile_state=COMPILE_SNAPSHOT_ONLY,
        default_source_type="chat-export",
        default_provenance="community",
    ),
}


def namespace_for(name: str) -> RawNamespace | None:
    return RAW_NAMESPACES.get(name)


def parse_raw_path(raw_path: str) -> RawPathInfo | None:
    """Parse repo-relative raw/<namespace>/<bucket>/<filename>.md paths."""
    p = Path(raw_path)
    parts = p.parts
    if p.is_absolute() or ".." in parts or len(parts) != 4:
        return None
    if parts[0] != "raw" or not parts[3].endswith(".md"):
        return None
    return RawPathInfo(namespace=parts[1], bucket=parts[2], filename=parts[3])


def reviewed_for_compile(value: str | None) -> bool:
    return (value or "").strip().lower() in {"true", "yes", "1"}


def is_compile_eligible(namespace: RawNamespace, *, reviewed: bool = False) -> bool:
    if namespace.compile_state == COMPILE_AUTO:
        return True
    if namespace.compile_state == COMPILE_REVIEW:
        return reviewed
    return False
