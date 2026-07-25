"""Offline tests for local environment and authenticated-user wiring."""
import json

import pytest

from bowerbird import local
from bowerbird.tokens import FileTokenStorage, TokenStore


def test_load_env_file_parses_values_without_overwriting_environment(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nX_CLIENT_ID='file-id'\n X_CLIENT_SECRET = \"secret\" \nIGNORED\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("X_CLIENT_ID", "real-id")
    monkeypatch.delenv("X_CLIENT_SECRET", raising=False)

    local.load_env_file(str(env_file))

    assert local.os.environ["X_CLIENT_ID"] == "real-id"
    assert local.os.environ["X_CLIENT_SECRET"] == "secret"


def test_load_env_file_missing_is_a_noop(tmp_path):
    local.load_env_file(str(tmp_path / "missing.env"))


def test_make_token_store_requires_client_id(monkeypatch, tmp_path):
    monkeypatch.delenv("X_CLIENT_ID", raising=False)
    with pytest.raises(SystemExit, match="X_CLIENT_ID not set"):
        local.make_token_store(str(tmp_path))


def test_make_token_store_uses_local_token_file(monkeypatch, tmp_path):
    monkeypatch.setenv("X_CLIENT_ID", "client")
    monkeypatch.setenv("X_CLIENT_SECRET", "secret")

    store = local.make_token_store(str(tmp_path))

    assert isinstance(store, TokenStore)
    assert isinstance(store._storage, FileTokenStorage)
    assert store._storage._path == tmp_path / ".x_tokens.json"


def test_resolve_user_id_prefers_environment_without_network(monkeypatch):
    monkeypatch.setenv("X_USER_ID", "known-user")
    token_store = object()
    monkeypatch.setattr(
        local.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("environment value should avoid HTTP"),
    )
    assert local.resolve_user_id(token_store) == "known-user"


def test_resolve_user_id_calls_users_me_with_bearer(monkeypatch):
    monkeypatch.delenv("X_USER_ID", raising=False)
    seen = {}

    class Store:
        def get_access_token(self):
            return "access-token"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"data": {"id": "api-user"}}).encode()

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(local.urllib.request, "urlopen", fake_urlopen)

    assert local.resolve_user_id(Store()) == "api-user"
    assert seen["request"].full_url == local.API_BASE + "users/me"
    assert seen["request"].get_header("Authorization") == "Bearer access-token"
    assert seen["timeout"] == 30
