"""Timeline client URL construction, paging, flattening, and retry behavior."""
import io
import json
import urllib.error
import urllib.parse

import pytest

from bowerbird import timeline


class FakeTimeline(timeline.TimelineClient):
    def __init__(self, pages):
        super().__init__("bearer", sleep=lambda seconds: self.sleeps.append(seconds))
        self.pages = list(pages)
        self.urls = []
        self.sleeps = []

    def _get(self, url):
        self.urls.append(url)
        return self.pages.pop(0)


def test_resolve_user_id_quotes_handle_and_rejects_missing_account():
    client = FakeTimeline([{"data": {"id": "42"}}])
    assert client.resolve_user_id("name/value") == "42"
    assert client.urls == [timeline.API_BASE + "users/by/username/name%2Fvalue"]

    missing = FakeTimeline([{}])
    with pytest.raises(ValueError, match="no such X account"):
        missing.resolve_user_id("nobody")


def test_user_tweet_pages_bounds_page_size_and_paginates():
    client = FakeTimeline([
        {"data": {"id": "42"}},
        {"data": [{"id": "2"}], "meta": {"next_token": "next"}},
        {"data": [{"id": "1"}]},
    ])
    pages = list(client.user_tweet_pages("builder", start_time="2026-01-01T00:00:00Z", page_size=1))
    assert pages == [[{"id": "2"}], [{"id": "1"}]]
    first = urllib.parse.parse_qs(urllib.parse.urlsplit(client.urls[1]).query)
    second = urllib.parse.parse_qs(urllib.parse.urlsplit(client.urls[2]).query)
    assert first["max_results"] == ["5"]
    assert first["exclude"] == ["retweets"]
    assert first["start_time"] == ["2026-01-01T00:00:00Z"]
    assert second["pagination_token"] == ["next"]
    assert client.sleeps == [1]


def test_user_tweets_flattens_pages_and_caps_page_size_at_100():
    client = FakeTimeline([
        {"data": {"id": "42"}},
        {"data": [{"id": "1"}, {"id": "2"}]},
    ])
    assert list(client.user_tweets("builder")) == [{"id": "1"}, {"id": "2"}]
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(client.urls[1]).query)
    assert params["max_results"] == ["100"]
    assert "start_time" not in params


def _http_error(code, retry_after=None):
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return urllib.error.HTTPError("url", code, "error", headers, io.BytesIO())


def test_get_retries_rate_limit_using_retry_after(monkeypatch):
    attempts = [_http_error(429, "7"), {"data": [{"id": "ok"}]}]
    sleeps = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(self.payload).encode()

    def fake_urlopen(request, timeout):
        item = attempts.pop(0)
        if isinstance(item, Exception):
            raise item
        assert request.get_header("Authorization") == "Bearer secret"
        assert timeout == 30
        return Response(item)

    monkeypatch.setattr(timeline.urllib.request, "urlopen", fake_urlopen)
    client = timeline.TimelineClient("secret", sleep=sleeps.append)
    assert client._get("https://example.test") == {"data": [{"id": "ok"}]}
    assert sleeps == [7]


def test_get_uses_bounded_backoff_and_propagates_final_error(monkeypatch):
    errors = [_http_error(429, "invalid") for _ in range(timeline.MAX_RETRIES)]
    sleeps = []
    monkeypatch.setattr(
        timeline.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(errors.pop(0)),
    )
    client = timeline.TimelineClient("secret", sleep=sleeps.append)
    with pytest.raises(urllib.error.HTTPError):
        client._get("https://example.test")
    assert sleeps == [5, 10, 20, 40]


def test_get_does_not_retry_unrelated_http_errors(monkeypatch):
    monkeypatch.setattr(
        timeline.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(_http_error(500)),
    )
    client = timeline.TimelineClient("secret", sleep=lambda _seconds: pytest.fail("must not sleep"))
    with pytest.raises(urllib.error.HTTPError):
        client._get("https://example.test")
