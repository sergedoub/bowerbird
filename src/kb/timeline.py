"""TimelineClient — every post + reply from one account (OAuth2 APP-ONLY Bearer).

A different read shape from bookmarks: instead of "things the user filed", this walks an
account's own timeline via GET /2/users/:id/tweets. Reposts are excluded (exclude=retweets)
so only the account's own words land; replies are KEPT (they're the point).

Auth is the app-only Bearer (same credential as full-archive search, see search.py) — the
timeline endpoint accepts it, so this pipeline needs no rotating user-context token.

The timeline endpoint returns newest-first and caps at ~the 3,200 most recent posts. A
`start_time` bounds each run to a trailing window (e.g. the last 3 days): cheap, and because
daily runs overlap it self-heals if a run is skipped. Dedup (RawWriter) keeps it append-only.

Like search.py, retries HTTP 429 with backoff for the unattended scheduled run.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator

from .models import TWEET_FIELDS

API_BASE = "https://api.x.com/2/"
MAX_RETRIES = 5


class TimelineClient:
    def __init__(self, bearer_token: str, *, sleep=time.sleep) -> None:
        self._bearer = bearer_token
        self._sleep = sleep

    def _get(self, url: str) -> dict:
        for attempt in range(MAX_RETRIES):
            req = urllib.request.Request(url, method="GET")
            req.add_header("Authorization", f"Bearer {self._bearer}")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < MAX_RETRIES - 1:
                    retry_after = e.headers.get("Retry-After")
                    wait = int(retry_after) if (retry_after and retry_after.isdigit()) else 5 * (2 ** attempt)
                    self._sleep(min(wait, 60))
                    continue
                raise
        raise RuntimeError("unreachable")

    def resolve_user_id(self, handle: str) -> str:
        path = f"users/by/username/{urllib.parse.quote(handle)}"
        data = self._get(API_BASE + path).get("data")
        if not data:
            raise ValueError(f"no such X account: @{handle}")
        return data["id"]

    def user_tweet_pages(
        self, handle: str, *, start_time: str | None = None, page_size: int = 100
    ) -> Iterator[list[dict]]:
        """Yield pages of raw v2 tweet objects (posts + replies, no retweets), newest-first.

        Page boundaries are exposed so callers can stop paging early (each page is a paid
        API read under pay-as-you-go; see run_dump's stop-at-seen rule). `page_size` lets
        capped runs (--max-posts) avoid paying for a full 100-post page; the API accepts
        5..100.

        `start_time` (RFC 3339, e.g. "2026-05-21T00:00:00Z") returns only posts at/after that
        instant; pass None to grab the available history (capped by the endpoint at ~3,200).
        """
        user_id = self.resolve_user_id(handle)
        params: dict = {
            "max_results": min(100, max(5, page_size)),
            "exclude": "retweets",  # drop reposts; KEEP replies
            "tweet.fields": TWEET_FIELDS,
        }
        if start_time:
            params["start_time"] = start_time
        while True:
            page = self._get(f"{API_BASE}users/{user_id}/tweets?" + urllib.parse.urlencode(params))
            yield page.get("data", [])
            nxt = page.get("meta", {}).get("next_token")
            if not nxt:
                break
            params["pagination_token"] = nxt
            self._sleep(1)  # be gentle between pages on the scheduled run

    def user_tweets(self, handle: str, *, start_time: str | None = None) -> Iterator[dict]:
        """Flattened view of user_tweet_pages (kept for callers that don't page)."""
        for page in self.user_tweet_pages(handle, start_time=start_time):
            yield from page
