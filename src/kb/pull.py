"""Pull orchestration: bookmarked folders -> raw/ (forward-only by construction).

Forward-only falls out of the design: ingestion is folder-scoped (allowlist) and RawWriter
dedups by file existence, so a scheduled run writes only bookmarks not already in raw/ and
never re-pulls history.

The clients are injected, so run_pull() is unit-testable with fakes (no network).
"""
from __future__ import annotations

from collections.abc import Iterable

from .config import Topic
from .models import Bookmark, RawDoc, Thread
from .threads import assemble


def build_raw_doc(bm: Bookmark, thread: Thread | None) -> RawDoc:
    t = bm.tweet
    tweet_count = len(thread.tweets) if thread else 1
    parts = [thread.text if thread else t.text]
    if bm.article_text:  # X-native Article: include the full body, not just a pointer
        parts.append(f"## Article: {bm.article_title or ''}\n\n{bm.article_text}")
    elif bm.article_title:
        parts.append(f"[linked article: {bm.article_title}]")
    body = "\n\n".join(p for p in parts if p)
    fm = {
        "topic": bm.topic,
        "author": f"@{bm.author_username}" if bm.author_username else t.author_id,
        "author_id": t.author_id,
        "conversation_id": t.conversation_id,
        "created_at": t.created_at,
        "source_url": f"https://x.com/i/web/status/{t.id}",
        "folder_id": bm.folder_id,
        "tweet_count": tweet_count,
    }
    if bm.article_title:
        fm["article_title"] = bm.article_title
    return RawDoc(topic=bm.topic, id=t.id, created_at=t.created_at, frontmatter=fm, body=body)


def run_pull(
    topics: Iterable[Topic],
    bookmarks,
    search,
    writer,
    *,
    reconstruct_threads: bool = True,
    limit_per_folder: int | None = None,
    stop_at_existing: bool = False,
) -> dict:
    """Pull each topic's allowlisted folders into raw/. Returns a summary dict."""
    if limit_per_folder is not None and limit_per_folder < 1:
        raise ValueError("limit_per_folder must be positive")

    summary = {
        "seen": 0,
        "written": 0,
        "skipped": 0,
        "threads": 0,
        "stopped_at_existing": 0,
        "written_paths": [],
        "limit_per_folder": limit_per_folder,
    }
    for topic in topics:
        for folder_id in topic.folder_ids:
            for bm in bookmarks.bookmarks_in_folder(folder_id, topic.name, limit=limit_per_folder):
                summary["seen"] += 1
                single_doc = build_raw_doc(bm, None)
                if writer.path_for(single_doc).exists():
                    summary["skipped"] += 1
                    if stop_at_existing:
                        summary["stopped_at_existing"] += 1
                        break
                    continue
                thread = None
                if reconstruct_threads and bm.is_thread_head:
                    thread = assemble(bm.tweet, search.fetch_conversation)
                    summary["threads"] += 1
                path = writer.write(build_raw_doc(bm, thread))
                if path:
                    summary["written"] += 1
                    summary["written_paths"].append(str(path))
                else:
                    summary["skipped"] += 1
                    if stop_at_existing:
                        summary["stopped_at_existing"] += 1
                        break
    summary["search_mode"] = getattr(search, "mode", None)
    return summary
