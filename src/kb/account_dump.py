"""Account-dump orchestration: an account's output -> raw/accounts/<handle>/.

Idempotent by the same construction as the bookmark pull: RawWriter dedups by file existence,
so a run only writes posts not already on disk. The runner scopes each fetch to a trailing
window via `start_time` (e.g. the last 3 days); dedup makes the overlap between daily runs a
no-op, so the net effect is "capture the window, then accrue forward".

Stop-at-seen: file-level dedup keeps the data append-only, but every fetched page is still a
paid API read under pay-as-you-go. On windowed runs the walk therefore stops at the first page
that contains posts but writes none of them — everything below is older and already on disk.
Full-history runs (`start_time=None`) never stop early: a previously-windowed instance may
hold recent posts while missing older ones, so the walk must reach the end.

The client is injected, so run_dump() is unit-testable with fakes (no network).
"""
from __future__ import annotations

from collections.abc import Iterable

from .config import Account
from .models import RawDoc


def _reply_parent(t: dict) -> str | None:
    for ref in t.get("referenced_tweets") or []:
        if ref.get("type") == "replied_to":
            return ref.get("id")
    return None


def build_raw_doc(t: dict, handle: str) -> RawDoc:
    """Turn one raw v2 tweet object into a RawDoc filed under raw/accounts/<handle>/."""
    text = (t.get("note_tweet") or {}).get("text") or t.get("text", "")
    article = t.get("article") or {}
    parts = [text]
    if article.get("plain_text") or article.get("title"):
        parts.append(f"## Article: {article.get('title', '')}\n\n{article.get('plain_text', '')}")
    parent = _reply_parent(t)
    fm = {
        "account": f"@{handle}",
        "author_id": t.get("author_id", ""),
        "conversation_id": t.get("conversation_id", t["id"]),
        "created_at": t.get("created_at", ""),
        "source_url": f"https://x.com/i/web/status/{t['id']}",
        "is_reply": parent is not None,
    }
    if parent:
        fm["in_reply_to"] = parent
    if article.get("title"):
        fm["article_title"] = article["title"]
    return RawDoc(
        topic=handle,  # RawWriter routes on `topic`; here that is the account raw namespace
        id=t["id"],
        created_at=t.get("created_at", ""),
        frontmatter=fm,
        body="\n\n".join(p for p in parts if p),
    )


def run_dump(
    accounts: Iterable[Account],
    client,
    writer,
    *,
    start_time: str | None = None,
    stop_at_seen: bool | None = None,
    max_posts: int | None = None,
) -> dict:
    """Dump each account's posts + replies into raw/. Returns a summary dict.

    `start_time` (RFC 3339) scopes the fetch to a trailing window; None grabs the full
    available timeline. Already-stored posts are skipped, so re-runs over the window are no-ops.

    `stop_at_seen` halts an account's walk at the first non-empty page that writes nothing
    (newest-first order means everything below it is already on disk). Defaults to on for
    windowed runs and off for full-history runs — see the module docstring for why.

    `max_posts` caps how many posts are processed per account (newest-first), and shrinks
    the requested page size to match so the cap also caps paid API reads — used for cheap
    setup smoke imports.
    """
    if stop_at_seen is None:
        stop_at_seen = start_time is not None
    page_size = min(100, max_posts) if max_posts else 100
    summary = {"seen": 0, "written": 0, "skipped": 0, "written_paths": [], "early_stops": 0}
    for account in accounts:
        taken = 0
        for page in client.user_tweet_pages(account.handle, start_time=start_time,
                                            page_size=page_size):
            wrote_any = False
            if max_posts is not None:
                page = page[: max_posts - taken]
            for t in page:
                taken += 1
                summary["seen"] += 1
                path = writer.write(build_raw_doc(t, account.handle))
                if path:
                    summary["written"] += 1
                    summary["written_paths"].append(str(path))
                    wrote_any = True
                else:
                    summary["skipped"] += 1
            if max_posts is not None and taken >= max_posts:
                break
            if stop_at_seen and page and not wrote_any:
                summary["early_stops"] += 1
                break
    return summary
