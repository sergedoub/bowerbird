"""Search-dump orchestration: X Recent Search -> raw/searches/<monitor>/."""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from pathlib import Path

from .config import SearchMonitor
from .models import RawAddress, RawDoc, TWEET_FIELDS

SEARCH_RECENT = "https://api.x.com/2/tweets/search/recent"
MAX_RETRIES = 5
SEARCH_TWEET_FIELDS = TWEET_FIELDS + ",lang"


class RecentSearchClient:
    """Minimal app-only client for X Recent Search."""

    def __init__(self, bearer_token: str, *, sleep=time.sleep) -> None:
        self._bearer = bearer_token
        self._sleep = sleep

    def _get(self, params: dict[str, str | int]) -> dict:
        url = SEARCH_RECENT + "?" + urllib.parse.urlencode(params)
        for attempt in range(MAX_RETRIES):
            req = urllib.request.Request(url, method="GET")
            req.add_header("Authorization", f"Bearer {self._bearer}")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < MAX_RETRIES - 1:
                    retry_after = exc.headers.get("Retry-After")
                    wait = int(retry_after) if (retry_after and retry_after.isdigit()) else 5 * (2 ** attempt)
                    self._sleep(min(wait, 60))
                    continue
                raise
        raise RuntimeError("unreachable")

    def search_pages(
        self,
        monitor: SearchMonitor,
        *,
        since_id: str | None = None,
        start_time: str | None = None,
        max_results: int | None = None,
        max_pages: int | None = None,
    ) -> Iterable[dict]:
        params: dict[str, str | int] = {
            "query": monitor.query,
            "max_results": max_results or monitor.max_results,
            "tweet.fields": SEARCH_TWEET_FIELDS,
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        if since_id:
            params["since_id"] = since_id
        elif start_time:
            params["start_time"] = start_time

        pages = max_pages or monitor.max_pages
        for index in range(pages):
            page = self._get(params)
            yield page
            nxt = page.get("meta", {}).get("next_token")
            if not nxt:
                return
            if index >= pages - 1:
                return
            params["next_token"] = str(nxt)
            self._sleep(1)


def newest_raw_id(raw_root: str | Path, monitor_name: str) -> str | None:
    """Return the largest tweet id already present for one search monitor."""
    root = Path(raw_root) / "searches" / monitor_name
    if not root.exists():
        return None
    ids: list[int] = []
    for path in root.glob("*__*.md"):
        stem = path.stem
        _, _, raw_id = stem.partition("__")
        if raw_id.isdigit():
            ids.append(int(raw_id))
    return str(max(ids)) if ids else None


def _users_by_id(page: dict) -> dict[str, dict]:
    users = page.get("includes", {}).get("users", [])
    return {str(user.get("id")): user for user in users if user.get("id")}


def _source_url(tweet_id: str, user: dict | None) -> str:
    username = str((user or {}).get("username") or "").strip()
    if username:
        return f"https://x.com/{username}/status/{tweet_id}"
    return f"https://x.com/i/web/status/{tweet_id}"


def build_raw_doc(t: dict, monitor: SearchMonitor, user: dict | None) -> RawDoc:
    """Turn one Recent Search post into a RawDoc under raw/searches/<monitor>/."""
    text = (t.get("note_tweet") or {}).get("text") or t.get("text", "")
    article = t.get("article") or {}
    parts = [text]
    if article.get("plain_text") or article.get("title"):
        parts.append(f"## Article: {article.get('title', '')}\n\n{article.get('plain_text', '')}")
    author = str((user or {}).get("username") or t.get("author_id", "")).strip()
    fm = {
        "author": f"@{author}" if author and not author.isdigit() else author,
        "author_id": t.get("author_id", ""),
        "conversation_id": t.get("conversation_id", t["id"]),
        "created_at": t.get("created_at", ""),
        "monitor": monitor.name,
        "query": monitor.query,
        "source_url": _source_url(t["id"], user),
        "topic": monitor.topic,
    }
    if (user or {}).get("name"):
        fm["author_name"] = user["name"]
    if t.get("lang"):
        fm["lang"] = t["lang"]
    if article.get("title"):
        fm["article_title"] = article["title"]
    return RawDoc(
        topic=monitor.name,
        id=t["id"],
        created_at=t.get("created_at", ""),
        frontmatter=fm,
        body="\n\n".join(p for p in parts if p),
        address=RawAddress(namespace="searches", bucket=monitor.name),
    )


def run_dump(
    monitors: Iterable[SearchMonitor],
    client,
    writer,
    *,
    raw_root: str | Path,
    now_utc,
    max_results: int | None = None,
    max_pages: int | None = None,
    lookback_hours: int | None = None,
) -> dict:
    """Dump configured Recent Search monitors into raw/. Returns a summary dict."""
    summary = {
        "seen": 0,
        "written": 0,
        "skipped": 0,
        "written_paths": [],
        "saturated": [],
    }
    for monitor in monitors:
        since_id = newest_raw_id(raw_root, monitor.name)
        hours = lookback_hours or monitor.lookback_hours
        start_time = None
        if since_id is None:
            start = now_utc - dt.timedelta(hours=hours)
            start_time = start.strftime("%Y-%m-%dT%H:%M:%SZ")

        last_page: dict | None = None
        for page in client.search_pages(
            monitor,
            since_id=since_id,
            start_time=start_time,
            max_results=max_results,
            max_pages=max_pages,
        ):
            last_page = page
            users = _users_by_id(page)
            for t in page.get("data", []):
                summary["seen"] += 1
                path = writer.write(build_raw_doc(t, monitor, users.get(str(t.get("author_id", "")))))
                if path:
                    summary["written"] += 1
                    summary["written_paths"].append(str(path))
                else:
                    summary["skipped"] += 1
        if last_page and last_page.get("meta", {}).get("next_token"):
            summary["saturated"].append(monitor.name)
    return summary
