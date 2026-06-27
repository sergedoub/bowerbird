"""TokenStore: refresh only when expired, and always persist the rotated refresh token."""
import pytest

from bowerbird.tokens import TokenStore


class FakeStorage:
    def __init__(self, tokens):
        self.tokens = dict(tokens)
        self.saves = 0

    def load(self):
        return dict(self.tokens)

    def save(self, tokens):
        self.tokens = dict(tokens)
        self.saves += 1


class FakePoster:
    """Returns a fresh, ROTATED refresh token on every refresh (mirrors X behavior)."""
    def __init__(self):
        self.calls = []
        self.n = 0

    def __call__(self, form):
        self.calls.append(form)
        self.n += 1
        return {
            "access_token": f"access-{self.n}",
            "refresh_token": f"refresh-{self.n}",
            "expires_in": 7200,
            "scope": "bookmark.read",
        }


def _store(tokens, poster, now):
    return TokenStore("client-id", "secret", FakeStorage(tokens), token_poster=poster, now=lambda: now)


def test_valid_token_is_returned_without_refreshing():
    poster = FakePoster()
    store = _store(
        {"access_token": "still-good", "refresh_token": "r0", "expires_in": 7200, "obtained_at": 1000},
        poster, now=1000,
    )
    assert store.get_access_token() == "still-good"
    assert poster.calls == []  # no network when the token is still valid


def test_expired_token_triggers_refresh():
    poster = FakePoster()
    store = _store(
        {"access_token": "old", "refresh_token": "r0", "expires_in": 7200, "obtained_at": 1000},
        poster, now=9000,  # well past obtained_at + expires_in
    )
    assert store.get_access_token() == "access-1"
    assert poster.calls[0]["grant_type"] == "refresh_token"
    assert poster.calls[0]["refresh_token"] == "r0"


def test_rotated_refresh_token_is_persisted():
    poster = FakePoster()
    storage = FakeStorage(
        {"access_token": "old", "refresh_token": "r0", "expires_in": 7200, "obtained_at": 1000}
    )
    store = TokenStore("cid", "secret", storage, token_poster=poster, now=lambda: 9000)
    store.get_access_token()
    assert storage.tokens["refresh_token"] == "refresh-1"  # the NEW one is saved
    assert "obtained_at" in storage.tokens
    assert storage.saves == 1


def test_missing_refresh_token_raises():
    poster = FakePoster()
    store = _store({"access_token": "old", "expires_in": 1, "obtained_at": 0}, poster, now=9000)
    with pytest.raises(ValueError):
        store.get_access_token()
