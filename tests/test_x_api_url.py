import pytest

from bin import x_auth_spike
from bowerbird.x_api_url import build_x_api_url


def test_x_api_url_accepts_relative_v2_path():
    assert build_x_api_url("users/me") == "https://api.x.com/2/users/me"


@pytest.mark.parametrize(
    "url",
    (
        "https://example.com/collect",
        "http://api.x.com/2/users/me",
        "https://api.x.com.evil.test/2/users/me",
        "https://api.x.com@evil.test/2/users/me",
    ),
)
def test_x_api_url_rejects_destinations_that_could_receive_the_saved_token(url):
    with pytest.raises(ValueError, match="https://api.x.com/2/"):
        build_x_api_url(url)


def test_auth_get_rejects_untrusted_url_before_loading_saved_token(monkeypatch):
    def fail_if_tokens_are_loaded():
        raise AssertionError("saved token was loaded for an untrusted destination")

    monkeypatch.setattr(x_auth_spike, "load_tokens", fail_if_tokens_are_loaded)
    args = type("Args", (), {"path": "https://example.com/collect", "query": None})()

    with pytest.raises(SystemExit, match="https://api.x.com/2/"):
        x_auth_spike.cmd_get(args)
