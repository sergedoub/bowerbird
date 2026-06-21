"""SearchClient — thread reconstruction search (OAuth2 APP-ONLY Bearer).

Spike (PRD #1): search REJECTS user-context auth (HTTP 403) and requires an app-only
Bearer token. Used to reconstruct threads via conversation_id.

Endpoint fallback: full-archive search (/search/all) is not available on every X API
plan. The client tries it first and, on HTTP 403, permanently falls back to recent
search (/search/recent, last 7 days) for the rest of the run. Since bookmarks are
overwhelmingly fresh posts, recent search reconstructs most threads; only threads
older than a week lose their tail. `mode` reports which endpoint is active.

Search is rate-limited (~1 req/sec + window caps), so this client backs off and
retries on HTTP 429 — important for the unattended scheduled pull.

Provides the `fetch_conversation` that ThreadAssembler.assemble() expects.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from .models import TWEET_FIELDS, Tweet, tweet_from_api

SEARCH_ALL = "https://api.x.com/2/tweets/search/all"
SEARCH_RECENT = "https://api.x.com/2/tweets/search/recent"
MAX_RETRIES = 5


class SearchClient:
    def __init__(self, bearer_token: str, *, sleep=time.sleep) -> None:
        self._bearer = bearer_token
        self._sleep = sleep
        self._endpoint = SEARCH_ALL  # demoted to SEARCH_RECENT on the first 403

    @property
    def mode(self) -> str:
        """Which search tier this run is using: 'full-archive' or 'recent' (7-day)."""
        return "full-archive" if self._endpoint == SEARCH_ALL else "recent"

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

    def _search_page(self, params: dict) -> dict:
        """One search request against the active endpoint, demoting all -> recent on 403.

        Access is denied at the endpoint level, so a 403 can only happen on the first
        full-archive call of a run — never mid-pagination with a stale next_token.
        """
        try:
            return self._get(self._endpoint + "?" + urllib.parse.urlencode(params))
        except urllib.error.HTTPError as e:
            if e.code == 403 and self._endpoint == SEARCH_ALL:
                self._endpoint = SEARCH_RECENT
                return self._get(self._endpoint + "?" + urllib.parse.urlencode(params))
            raise

    def fetch_conversation(self, conversation_id: str, author_id: str) -> list[Tweet]:
        """Return the head author's posts in a conversation (filtered server-side with from:)."""
        params = {
            "query": f"conversation_id:{conversation_id} from:{author_id}",
            "max_results": 100,
            "tweet.fields": TWEET_FIELDS,
        }
        out: list[Tweet] = []
        while True:
            page = self._search_page(params)
            for t in page.get("data", []):
                out.append(tweet_from_api(t))
            nxt = page.get("meta", {}).get("next_token")
            if not nxt:
                break
            params["next_token"] = nxt
            self._sleep(1)  # respect the ~1 req/sec search limit between pages
        return out
