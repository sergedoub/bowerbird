"""XBookmarkClient — read bookmarks + folders (OAuth2 USER-CONTEXT).

Auth split (spike, PRD #1): bookmarks use a user-context access token (via TokenStore);
full-archive search uses an app-only Bearer (see search.py). Different credentials.

Endpoints (verified):
  GET /2/users/:id/bookmarks/folders
  GET /2/users/:id/bookmarks                  (paginated, 100/page, expansions for media/refs)

NOTE: live-call client — covered by integration tests later, not the unit suite.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Iterator

from .models import TWEET_FIELDS, Bookmark, tweet_from_api
from .tokens import TokenStore

API_BASE = "https://api.x.com/2/"


class XBookmarkClient:
    def __init__(self, user_id: str, tokens: TokenStore) -> None:
        self._user_id = user_id
        self._tokens = tokens

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = API_BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {self._tokens.get_access_token()}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def folders(self) -> list[dict]:
        """[{'id': ..., 'name': ...}, ...]"""
        return self._get(f"users/{self._user_id}/bookmarks/folders").get("data", [])

    def _folder_tweet_id_pages(
        self, folder_id: str, *, limit: int | None = None,
    ) -> Iterator[list[str]]:
        """Yield folder-content tweet IDs page by page.

        The endpoint returns only tweet IDs; content hydration is a separate
        `/2/tweets` request. Streaming pages lets scheduled pulls stop as soon
        as they reach already-ingested content instead of walking old history.
        """
        seen = 0
        params: dict = {}
        path = f"users/{self._user_id}/bookmarks/folders/{folder_id}"
        while True:
            page = self._get(path, params or None)
            ids = [item["id"] for item in page.get("data", [])]
            if limit is not None:
                remaining = limit - seen
                if remaining <= 0:
                    return
                ids = ids[:remaining]
            if ids:
                seen += len(ids)
                yield ids
            if limit is not None and seen >= limit:
                return
            nxt = page.get("meta", {}).get("next_token")
            if not nxt:
                break
            params["pagination_token"] = nxt

    def _folder_tweet_ids(self, folder_id: str, *, limit: int | None = None) -> list[str]:
        """The folder-contents endpoint returns ONLY tweet ids ([id, folder_id])."""
        ids: list[str] = []
        for page_ids in self._folder_tweet_id_pages(folder_id, limit=limit):
            ids.extend(page_ids)
        return ids

    def _hydrate(self, ids: list[str]) -> tuple[dict[str, dict], dict[str, str]]:
        """Fetch tweet objects + author usernames via GET /2/tweets (batches of 100).

        Returns (tweets_by_id, username_by_author_id). Requests the `article` field so
        X-native Article bodies (article.plain_text) come back, and expands author_id ->
        username for proper attribution.
        """
        tweets: dict[str, dict] = {}
        users: dict[str, str] = {}
        for i in range(0, len(ids), 100):
            batch = ids[i : i + 100]
            page = self._get(
                "tweets",
                {
                    "ids": ",".join(batch),
                    "tweet.fields": TWEET_FIELDS,
                    "expansions": "author_id",
                    "user.fields": "username",
                },
            )
            for t in page.get("data", []):
                tweets[t["id"]] = t
            for u in page.get("includes", {}).get("users", []):
                if u.get("username"):
                    users[u["id"]] = u["username"]
        return tweets, users

    def bookmarks_in_folder(
        self, folder_id: str, topic: str, *, limit: int | None = None,
    ) -> Iterator[Bookmark]:
        """Yield hydrated bookmarks for a folder (folder gives ids; /2/tweets gives content)."""
        for ids in self._folder_tweet_id_pages(folder_id, limit=limit):
            tweets, users = self._hydrate(ids)
            for tid in ids:
                t = tweets.get(tid)
                if not t:  # deleted/unavailable tweet
                    continue
                article = t.get("article") or {}
                yield Bookmark(
                    tweet=tweet_from_api(t),
                    folder_id=folder_id,
                    topic=topic,
                    article_title=article.get("title"),
                    article_text=article.get("plain_text"),
                    author_username=users.get(t.get("author_id", "")),
                )

    def bookmark_count_in_folder(self, folder_id: str) -> int:
        """Count folder items by walking ID pages without hydrating post content."""
        return len(self._folder_tweet_ids(folder_id))
