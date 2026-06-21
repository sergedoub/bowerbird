"""SearchClient endpoint fallback: full-archive first, recent search after a 403.

The HTTP edge (`_get`) is replaced with a fake so everything runs offline; the fallback
decision, caching, and pagination logic under test are the real implementation.
"""
import urllib.error

import pytest

from kb.search import SEARCH_ALL, SEARCH_RECENT, SearchClient


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("url", code, "err", hdrs=None, fp=None)


def _page(ids, next_token=None):
    data = [
        {"id": i, "text": f"t{i}", "author_id": "a1", "conversation_id": "c1",
         "created_at": "2026-06-01T00:00:00.000Z"}
        for i in ids
    ]
    return {"data": data, "meta": ({"next_token": next_token} if next_token else {})}


class FakeHttpSearch(SearchClient):
    """Real SearchClient with the network call swapped for canned responses per endpoint."""

    def __init__(self, *, all_responses=None, recent_responses=None):
        super().__init__("test-bearer", sleep=lambda _s: None)
        self._all = list(all_responses or [])
        self._recent = list(recent_responses or [])
        self.calls = []

    def _get(self, url):
        self.calls.append(url)
        queue = self._all if url.startswith(SEARCH_ALL) else self._recent
        if not queue:
            raise AssertionError(f"unexpected request: {url}")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_full_archive_used_when_available():
    client = FakeHttpSearch(all_responses=[_page(["1", "2"])])
    tweets = client.fetch_conversation("c1", "a1")
    assert [t.id for t in tweets] == ["1", "2"]
    assert client.mode == "full-archive"
    assert all(u.startswith(SEARCH_ALL) for u in client.calls)


def test_403_falls_back_to_recent_and_still_returns_thread():
    client = FakeHttpSearch(
        all_responses=[_http_error(403)],
        recent_responses=[_page(["1", "2"])],
    )
    tweets = client.fetch_conversation("c1", "a1")
    assert [t.id for t in tweets] == ["1", "2"]
    assert client.mode == "recent"


def test_fallback_is_cached_for_the_rest_of_the_run():
    client = FakeHttpSearch(
        all_responses=[_http_error(403)],
        recent_responses=[_page(["1"]), _page(["2"])],
    )
    client.fetch_conversation("c1", "a1")
    client.fetch_conversation("c2", "a1")  # goes straight to recent — no failing call
    all_calls = [u for u in client.calls if u.startswith(SEARCH_ALL)]
    assert len(all_calls) == 1


def test_pagination_works_after_fallback():
    client = FakeHttpSearch(
        all_responses=[_http_error(403)],
        recent_responses=[_page(["1"], next_token="n1"), _page(["2"])],
    )
    tweets = client.fetch_conversation("c1", "a1")
    assert [t.id for t in tweets] == ["1", "2"]


def test_non_403_errors_propagate():
    client = FakeHttpSearch(all_responses=[_http_error(500)])
    with pytest.raises(urllib.error.HTTPError):
        client.fetch_conversation("c1", "a1")
    assert client.mode == "full-archive"  # no demotion on unrelated failures
