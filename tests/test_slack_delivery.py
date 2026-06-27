import json

import pytest

from kb.slack_delivery import (
    SlackDeliveryError,
    deliver_slack_recaps,
    latest_manifest_path,
    post_to_slack,
)


def test_post_to_slack_uses_bot_token_json(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b'{"ok": true, "channel": "C123", "ts": "123.456"}'

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["auth"] = req.headers["Authorization"]
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("kb.slack_delivery.urllib.request.urlopen", fake_urlopen)

    result = post_to_slack("xoxb-token", "C123", "hello")

    assert captured == {
        "url": "https://slack.com/api/chat.postMessage",
        "body": {"channel": "C123", "text": "hello"},
        "auth": "Bearer xoxb-token",
        "timeout": 30,
    }
    assert result.channel == "C123"
    assert result.ts == "123.456"


def test_post_to_slack_surfaces_not_in_channel_hint(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b'{"ok": false, "error": "not_in_channel"}'

    monkeypatch.setattr("kb.slack_delivery.urllib.request.urlopen", lambda req, timeout: FakeResponse())

    with pytest.raises(SlackDeliveryError, match="invite the Bowerbird bot"):
        post_to_slack("xoxb-token", "C123", "hello")


def test_deliver_slack_recaps_posts_existing_recap_body(tmp_path):
    recap = tmp_path / "recaps" / "daily" / "2026-06-26.md"
    recap.parent.mkdir(parents=True)
    recap.write_text("---\ntype: Recap\nprofile: daily\n---\n\nExisting recap body.\n", encoding="utf-8")
    manifest = tmp_path / "recaps" / "manifests" / "2026-06-27.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "type": "RecapManifest",
                "recaps": [
                    {
                        "profile": "daily",
                        "file": "recaps/daily/2026-06-26.md",
                        "deliveries": [
                            {"type": "slack", "destination": "C123"},
                            {"type": "email", "destination": "team@example.com"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_post(token, destination, text):
        calls.append((token, destination, text))
        return type("Result", (), {"channel": destination, "ts": "123.456"})()

    results = deliver_slack_recaps(tmp_path, manifest, "xoxb-token", post=fake_post)

    assert calls == [("xoxb-token", "C123", "Existing recap body.")]
    assert results[0].profile == "daily"
    assert results[0].recap_file == "recaps/daily/2026-06-26.md"
    assert results[0].ts == "123.456"


def test_deliver_slack_recaps_requires_recap_frontmatter(tmp_path):
    recap = tmp_path / "recaps" / "daily" / "2026-06-26.md"
    recap.parent.mkdir(parents=True)
    recap.write_text("---\ntype: Note\n---\n\nWrong.\n", encoding="utf-8")
    manifest = tmp_path / "recaps" / "manifests" / "2026-06-27.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "type": "RecapManifest",
                "recaps": [
                    {
                        "profile": "daily",
                        "file": "recaps/daily/2026-06-26.md",
                        "deliveries": [{"type": "slack", "destination": "C123"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SlackDeliveryError, match="type: Recap"):
        deliver_slack_recaps(tmp_path, manifest, "xoxb-token", post=lambda *_: None)


def test_latest_manifest_path_returns_newest_manifest(tmp_path):
    manifest_dir = tmp_path / "recaps" / "manifests"
    manifest_dir.mkdir(parents=True)
    older = manifest_dir / "2026-06-26.json"
    newer = manifest_dir / "2026-06-27.json"
    older.write_text('{"type": "RecapManifest", "recaps": []}', encoding="utf-8")
    newer.write_text('{"type": "RecapManifest", "recaps": []}', encoding="utf-8")

    assert latest_manifest_path(tmp_path) == newer
