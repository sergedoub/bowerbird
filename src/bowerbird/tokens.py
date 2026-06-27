"""TokenStore — yields a valid OAuth2 user-context access token for the bookmarks API.

Hides the whole rotating-refresh-token dance behind one method, `get_access_token()`.

Verified facts this encodes (spike 2026-05-21, see PRD #1):
  - access tokens last ~2h; refresh requires the `offline.access` scope;
  - refresh tokens ROTATE (single-use) -> the new one MUST be persisted every refresh,
    or the next run is locked out;
  - refresh tokens expire after ~6 months of inactivity.

The HTTP call and the persistence are injected, so the rotation logic is unit-testable
with no network and no real files.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

TOKEN_URL = "https://api.x.com/2/oauth2/token"


class TokenStorage(Protocol):
    def load(self) -> dict: ...
    def save(self, tokens: dict) -> None: ...


class FileTokenStorage:
    """Persists tokens as JSON with 0600 perms (default: bin/.x_tokens.json)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> dict:
        if not self._path.exists():
            raise FileNotFoundError(
                f"{self._path} not found — run the one-time OAuth flow first "
                "(bin/x_auth_spike.py auth)."
            )
        return json.loads(self._path.read_text())

    def save(self, tokens: dict) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(tokens, indent=2))
        os.chmod(tmp, 0o600)
        tmp.replace(self._path)  # atomic on POSIX


def _http_token_poster(client_id: str, client_secret: str | None) -> Callable[[dict], dict]:
    """Default token poster: POST form-encoded to the X token endpoint (Basic auth if confidential)."""

    def post(form: dict) -> dict:
        data = urllib.parse.urlencode(form).encode()
        req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        if client_secret:
            basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            req.add_header("Authorization", f"Basic {basic}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    return post


class TokenStore:
    def __init__(
        self,
        client_id: str,
        client_secret: str | None,
        storage: TokenStorage,
        *,
        token_poster: Callable[[dict], dict] | None = None,
        now: Callable[[], float] = time.time,
        expiry_buffer_s: int = 120,
    ) -> None:
        self._client_id = client_id
        self._storage = storage
        self._post = token_poster or _http_token_poster(client_id, client_secret)
        self._now = now
        self._buffer = expiry_buffer_s

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing (and persisting the rotated refresh token) if needed."""
        tokens = self._storage.load()
        if not self._is_expired(tokens):
            return tokens["access_token"]
        return self._refresh(tokens)["access_token"]

    def _is_expired(self, tokens: dict) -> bool:
        obtained = tokens.get("obtained_at", 0)
        expires_in = tokens.get("expires_in", 0)
        return self._now() >= (obtained + expires_in - self._buffer)

    def _refresh(self, tokens: dict) -> dict:
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise ValueError("no refresh_token stored (was offline.access granted?)")
        new = self._post(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._client_id,
            }
        )
        new["obtained_at"] = int(self._now())
        # Critical: persist the (rotated) refresh token immediately.
        self._storage.save(new)
        return new
