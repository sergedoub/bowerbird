"""Build a bounded compile manifest before invoking an LLM runner.

The LLM should not rediscover compile scope by scanning the whole repo on every
scheduled run. This module does that bookkeeping deterministically: find raw
items that do not already have source notes, route them to topics, and list the
small set of existing wiki files the agent should inspect.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import AccountsConfig, SearchesConfig
from .linter import _frontmatter_pairs
from .raw_sources import BUCKET_ACCOUNT, BUCKET_MAPPED, namespace_for

REVIEW_BUCKETS = {"inbox", "misc", "unknown"}
RAW_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}__(.+)\.md$")
MAX_EXISTING_SOURCE_PATHS = 40


@dataclass(frozen=True)
class RawCompileItem:
    path: str
    namespace: str
    bucket: str
    raw_id: str
    topic: str
    source_type: str
    provenance: str


def build_compile_manifest(repo_root: str | Path) -> dict:
    root = Path(repo_root)
    compiled_paths, compiled_legacy = _compiled_raw_refs(root)
    items = [
        item
        for item in _raw_compile_items(root)
        if item.path not in compiled_paths and _legacy_key(item) not in compiled_legacy
    ]
    topics = sorted({item.topic for item in items})
    return {
        "version": 1,
        "total_new": len(items),
        "new_raw": [item.__dict__ for item in items],
        "topics": [_topic_scope(root, topic) for topic in topics],
    }


def manifest_prompt(manifest: dict) -> str:
    """Return the bounded instruction block appended to the runner prompt."""
    return (
        "\n\n## Incremental Compile Manifest\n\n"
        "Use this manifest as the compile scope. Do not rescan raw/ to discover "
        "additional work, and do not open unrelated wiki topics unless `bin/lint.py` "
        "reports a violation that requires it. Process every `new_raw` item listed "
        "below. You may inspect the listed `relevant_files` and bounded "
        "`existing_source_paths` sample for the touched topics. If `total_new` is "
        "0, make no wiki changes.\n\n"
        "```json\n"
        f"{json.dumps(manifest, indent=2, sort_keys=True)}\n"
        "```\n"
    )


def _compiled_raw_refs(root: Path) -> tuple[set[str], set[tuple[str, str, str]]]:
    paths: set[str] = set()
    legacy: set[tuple[str, str, str]] = set()
    for source in sorted((root / "wiki").glob("*/sources/*.md")):
        topic = source.parents[1].name
        fm = _frontmatter_pairs(source.read_text(encoding="utf-8"))
        raw_path = fm.get("raw_path", "").strip()
        if raw_path:
            paths.add(raw_path)
            continue
        raw_id = fm.get("raw_id", "").strip()
        if not raw_id:
            continue
        mirror = fm.get("mirror", "").strip()
        source_type = fm.get("source_type", "").strip()
        if mirror.startswith("accounts/"):
            legacy.add(("accounts", mirror.removeprefix("accounts/").strip("/"), raw_id))
        elif source_type == "book-chapter":
            legacy.add(("books", topic, raw_id))
        else:
            legacy.add(("bookmarks", topic, raw_id))
    return paths, legacy


def _raw_compile_items(root: Path) -> list[RawCompileItem]:
    accounts = _account_topics(root)
    searches = _search_topics(root)
    items: list[RawCompileItem] = []
    for raw_file in sorted((root / "raw").glob("*/*/*.md")):
        rel = raw_file.relative_to(root).as_posix()
        _, namespace_name, bucket, filename = raw_file.relative_to(root).parts
        namespace = namespace_for(namespace_name)
        if namespace is None or not namespace.auto_compile:
            continue
        raw_id = _raw_id(filename)
        if not raw_id:
            continue
        topic = _topic_for(namespace_name, bucket, accounts, searches)
        if topic is None:
            continue
        items.append(
            RawCompileItem(
                path=rel,
                namespace=namespace_name,
                bucket=bucket,
                raw_id=raw_id,
                topic=topic,
                source_type=namespace.default_source_type,
                provenance=namespace.default_provenance,
            )
        )
    return items


def _account_topics(root: Path) -> dict[str, str]:
    path = root / "config" / "accounts.toml"
    if not path.exists():
        return {}
    return {a.handle.lower(): a.topic for a in AccountsConfig.load(path).accounts}


def _search_topics(root: Path) -> dict[str, str]:
    path = root / "config" / "searches.toml"
    if not path.exists():
        return {}
    return {s.name: s.topic for s in SearchesConfig.load(path).searches}


def _topic_for(
    namespace_name: str,
    bucket: str,
    accounts: dict[str, str],
    searches: dict[str, str],
) -> str | None:
    namespace = namespace_for(namespace_name)
    if namespace is None:
        return None
    if namespace.bucket_kind == BUCKET_ACCOUNT:
        return accounts.get(bucket.lower())
    if namespace.bucket_kind == BUCKET_MAPPED:
        return searches.get(bucket)
    if bucket in REVIEW_BUCKETS:
        return None
    return bucket


def _topic_scope(root: Path, topic: str) -> dict:
    wiki_topic = root / "wiki" / topic
    relevant = []
    index = wiki_topic / "index.md"
    if index.exists():
        relevant.append(index.relative_to(root).as_posix())
    concepts = sorted((wiki_topic / "concepts").glob("*.md")) if wiki_topic.exists() else []
    relevant.extend(path.relative_to(root).as_posix() for path in concepts)
    sources = sorted((wiki_topic / "sources").glob("*.md")) if wiki_topic.exists() else []
    recent_sources = sources[-MAX_EXISTING_SOURCE_PATHS:]
    return {
        "topic": topic,
        "relevant_files": relevant,
        "existing_source_count": len(sources),
        "existing_source_paths": [path.relative_to(root).as_posix() for path in recent_sources],
    }


def _raw_id(filename: str) -> str | None:
    match = RAW_ID_RE.match(filename)
    return match.group(1) if match else None


def _legacy_key(item: RawCompileItem) -> tuple[str, str, str]:
    return (item.namespace, item.bucket, item.raw_id)
