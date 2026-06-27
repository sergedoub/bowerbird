"""Local-run wiring shared by bin/ scripts: .env loading, token store, user-id resolution.

Each bin script historically carried its own copies of these helpers; new scripts (folders,
init wizard) import them from here instead. Pure setdefault semantics: real environment
variables always win over bin/.env values.
"""
from __future__ import annotations

import json
import os
import urllib.request

from .tokens import FileTokenStorage, TokenStore

API_BASE = "https://api.x.com/2/"


def load_env_file(path: str) -> None:
    """Load KEY=VALUE lines from a gitignored .env file into os.environ (setdefault)."""
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def make_token_store(bin_dir: str) -> TokenStore:
    """User-context TokenStore over the local token file (bin/.x_tokens.json)."""
    client_id = os.environ.get("X_CLIENT_ID")
    if not client_id:
        raise SystemExit("X_CLIENT_ID not set (bin/.env locally, or environment).")
    storage = FileTokenStorage(os.path.join(bin_dir, ".x_tokens.json"))
    return TokenStore(client_id, os.environ.get("X_CLIENT_SECRET"), storage)


def resolve_user_id(token_store: TokenStore) -> str:
    """X user id for the authenticated user: X_USER_ID env var, else GET /2/users/me."""
    if os.environ.get("X_USER_ID"):
        return os.environ["X_USER_ID"]
    req = urllib.request.Request(API_BASE + "users/me", method="GET")
    req.add_header("Authorization", f"Bearer {token_store.get_access_token()}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["data"]["id"]
