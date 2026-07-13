"""Hosted recap-provider adapters, with every HTTP edge replaced by a fake."""
import io
import json
import urllib.error

import pytest

from bowerbird import recap_llm
from bowerbird.model_config import ModelConfig


@pytest.mark.parametrize(
    ("provider", "key_name", "response", "expected"),
    [
        ("openai", "OPENAI_API_KEY", {"output_text": "  OpenAI body  "}, "OpenAI body"),
        ("anthropic", "ANTHROPIC_API_KEY", {"content": [{"type": "text", "text": "Claude body"}]}, "Claude body"),
        ("gemini", "GEMINI_API_KEY", {"candidates": [{"content": {"parts": [{"text": "Gemini body"}]}}]}, "Gemini body"),
    ],
)
def test_generate_recap_body_routes_to_configured_provider(
    monkeypatch, provider, key_name, response, expected
):
    calls = []
    monkeypatch.setattr(
        recap_llm,
        "_post_json",
        lambda url, payload, headers: calls.append((url, payload, headers)) or response,
    )

    result = recap_llm.generate_recap_body(
        ModelConfig(provider=provider, recap_model="test-model"),
        "system",
        "user",
        env={key_name: " test-key "},
    )

    assert result == expected
    url, payload, headers = calls[0]
    assert "test-model" in url + json.dumps(payload)
    assert url.startswith("https://")
    assert "test-key" in json.dumps(headers) or "test-key" in url


def test_generate_recap_body_requires_provider_key():
    with pytest.raises(recap_llm.RecapModelError, match="OPENAI_API_KEY is required"):
        recap_llm.generate_recap_body(ModelConfig(), "system", "user", env={})


def test_openai_falls_back_to_nested_output_text(monkeypatch):
    monkeypatch.setattr(
        recap_llm,
        "_post_json",
        lambda *_args: {"output": [
            "ignore", {"content": [None, {"text": "first"}, {"text": "second"}]}
        ]},
    )
    assert recap_llm._openai(ModelConfig(), "key", "s", "u") == "first\nsecond"


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: recap_llm._openai(ModelConfig(), "k", "s", "u"), "OpenAI"),
        (lambda: recap_llm._anthropic(ModelConfig(provider="anthropic"), "k", "s", "u"), "Anthropic"),
        (lambda: recap_llm._gemini(ModelConfig(provider="gemini"), "k", "s", "u"), "Gemini"),
    ],
)
def test_provider_adapters_reject_empty_responses(monkeypatch, call, message):
    monkeypatch.setattr(recap_llm, "_post_json", lambda *_args: {})
    with pytest.raises(recap_llm.RecapModelError, match=message):
        call()


def test_post_json_builds_post_request_and_decodes_response(monkeypatch):
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(recap_llm.urllib.request, "urlopen", fake_urlopen)
    assert recap_llm._post_json("https://api.openai.com/v1/test", {"a": 1}, {"X-Test": "yes"}) == {"ok": True}
    assert seen["request"].method == "POST"
    assert json.loads(seen["request"].data) == {"a": 1}
    assert seen["request"].get_header("X-test") == "yes"
    assert seen["timeout"] == 120


def test_post_json_reports_http_error_detail(monkeypatch):
    error = urllib.error.HTTPError(
        "https://api.openai.com/v1/test", 401, "unauthorized", {}, io.BytesIO(b"bad key")
    )
    monkeypatch.setattr(recap_llm.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(recap_llm.RecapModelError, match="model API error 401: bad key"):
        recap_llm._post_json("https://api.openai.com/v1/test", {}, {})


@pytest.mark.parametrize(
    "error",
    [urllib.error.URLError("offline"), TimeoutError("slow"), json.JSONDecodeError("bad", "x", 0)],
)
def test_post_json_wraps_transport_and_decode_errors(monkeypatch, error):
    monkeypatch.setattr(recap_llm.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(recap_llm.RecapModelError, match="model API request failed"):
        recap_llm._post_json("https://api.openai.com/v1/test", {}, {})


@pytest.mark.parametrize(
    "url",
    [
        "http://api.openai.com/v1/responses",
        "https://evil.example/v1/responses",
        "https://api.openai.com.evil.example/v1/responses",
        "https://user@api.openai.com/v1/responses",
        "https://api.openai.com:444/v1/responses",
    ],
)
def test_post_json_rejects_unapproved_provider_url_before_sending(monkeypatch, url):
    monkeypatch.setattr(
        recap_llm.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("unapproved URL must not be opened"),
    )

    with pytest.raises(recap_llm.RecapModelError, match="approved HTTPS provider host"):
        recap_llm._post_json(url, {}, {"Authorization": "Bearer secret"})
