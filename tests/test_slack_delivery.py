import json
from urllib.error import HTTPError

import pytest

from kb.slack_delivery import mechanical_recap, post_to_slack, quiet_message, should_deliver


def feed(generated="2026-06-21", total_new=1):
    return {
        "generated": generated,
        "window_hours": 24,
        "accounts": {
            "dkundel": {
                "label": "Dkundel",
                "total_new": total_new,
                "notes": [{"date": "2026-06-20", "text": "Codex can inspect a video.\nMore."}],
            }
        },
        "topics": {},
        "summary": {"total_new": total_new, "account_lanes": 1, "topic_lanes": 0},
    }


def test_should_deliver_rejects_stale_feed():
    decision = should_deliver(feed("2026-06-20"), "2026-06-21", quiet_message_on_empty=False)
    assert not decision.deliver
    assert "stale feed" in decision.reason


def test_should_deliver_allows_configured_quiet_message():
    decision = should_deliver(feed(total_new=0), "2026-06-21", quiet_message_on_empty=True)
    assert decision.deliver
    assert decision.quiet
    assert "quiet day" in quiet_message(feed(total_new=0)).lower()


def test_mechanical_recap_keeps_lanes_and_first_lines():
    text = mechanical_recap(feed())
    assert "Daily Knowledge Base Recap" in text
    assert "*Accounts*" in text
    assert "Dkundel: 1 new note" in text
    assert "Codex can inspect a video." in text


def test_post_to_slack_uses_incoming_webhook_json(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("kb.slack_delivery.urllib.request.urlopen", fake_urlopen)

    post_to_slack("https://hooks.slack.com/services/T/B/C", "hello")

    assert captured == {
        "url": "https://hooks.slack.com/services/T/B/C",
        "body": {"text": "hello"},
        "timeout": 30,
    }


def test_post_to_slack_surfaces_http_errors(monkeypatch):
    def fake_urlopen(req, timeout):
        raise HTTPError(req.full_url, 404, "not found", hdrs=None, fp=None)

    monkeypatch.setattr("kb.slack_delivery.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(HTTPError):
        post_to_slack("https://hooks.slack.com/services/T/B/C", "hello")
