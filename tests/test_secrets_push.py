"""push-secrets core: staged values pushed, absent keys skipped, failures reported —
and only key NAMES ever surface."""
from bowerbird.secrets_push import push_secrets


def test_pushes_staged_values_and_skips_missing():
    calls = {}
    result = push_secrets(
        {
            "X_CLIENT_ID": "cid",
            "X_BEARER_TOKEN": "bearer",
            "GH_PAT": "pat",
            "SLACK_BOT_TOKEN": "xoxb-token",
        },
        '{"access_token": "at"}',
        lambda n, v: calls.__setitem__(n, v) or True,
    )
    assert calls == {
        "X_CLIENT_ID": "cid",
        "X_BEARER_TOKEN": "bearer",
        "GH_PAT": "pat",
        "SLACK_BOT_TOKEN": "xoxb-token",
        "X_TOKENS": '{"access_token": "at"}',
    }
    assert sorted(result["set"]) == [
        "GH_PAT",
        "SLACK_BOT_TOKEN",
        "X_BEARER_TOKEN",
        "X_CLIENT_ID",
        "X_TOKENS",
    ]
    assert sorted(result["skipped"]) == [
        "ANTHROPIC_API_KEY",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "CODEX_ACCESS_TOKEN",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "X_CLIENT_SECRET",
    ]
    assert result["failed"] == []


def test_failed_pushes_are_reported_not_silently_dropped():
    result = push_secrets({"X_CLIENT_ID": "cid"}, "", lambda n, v: False)
    assert result["failed"] == ["X_CLIENT_ID"]
    assert "X_TOKENS" in result["skipped"]


def test_empty_staging_is_all_skipped():
    result = push_secrets({}, "", lambda n, v: True)
    assert result["set"] == [] and len(result["skipped"]) == 11
