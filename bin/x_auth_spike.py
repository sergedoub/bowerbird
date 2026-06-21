#!/usr/bin/env python3
"""X account authorization for Bowerbird (`bowerbird auth`) — stdlib only.

Runs the OAuth2 (PKCE) browser sign-in against YOUR X developer app and saves the
user-context tokens to bin/.x_tokens.json. Run it once during setup, and again any
time the refresh token expires (after ~6 months of inactivity). Also provides raw
API helpers for poking the X API with your credentials.

Config is read from env, or from a gitignored bin/.env file (KEY=VALUE lines):
  X_CLIENT_ID       (required)
  X_CLIENT_SECRET   (optional; if set -> confidential client, HTTP Basic auth)
  X_REDIRECT_URI    (default http://bowerbird.localhost:8080/callback)
  X_SCOPES          (default "bookmark.read tweet.read users.read offline.access")

Usage:
  bowerbird auth                   # one-time browser approval -> saves tokens
  bowerbird auth me                # GET /2/users/me (who am I?)
  bowerbird auth refresh           # refresh now; reports the rotated refresh token
  bowerbird auth get <api-path>    # raw GET against https://api.x.com/2/<api-path>
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import socket
import socketserver
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
API_BASE = "https://api.x.com/2/"
HERE = os.path.dirname(os.path.abspath(__file__))
TOKENS_FILE = os.environ.get("TOKENS_FILE", os.path.join(HERE, ".x_tokens.json"))
ENV_FILE = os.path.join(HERE, ".env")
DEFAULT_SCOPES = "bookmark.read tweet.read users.read offline.access"
DEFAULT_REDIRECT_URI = "http://bowerbird.localhost:8080/callback"


def load_dotenv() -> None:
    """Load simple KEY=VALUE lines from bin/.env into os.environ (no overwrite)."""
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))


def cfg() -> dict:
    client_id = os.environ.get("X_CLIENT_ID")
    if not client_id:
        sys.exit("ERROR: X_CLIENT_ID not set (put it in bin/.env or the environment).")
    return {
        "client_id": client_id,
        "client_secret": os.environ.get("X_CLIENT_SECRET"),  # None => public client
        "redirect_uri": os.environ.get("X_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        "scopes": os.environ.get("X_SCOPES", DEFAULT_SCOPES),
    }


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def token_request(form: dict, c: dict) -> dict:
    """POST to the token endpoint. Confidential clients use HTTP Basic auth."""
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    if c["client_secret"]:
        basic = b64url_basic(c["client_id"], c["client_secret"])
        req.add_header("Authorization", f"Basic {basic}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"Token endpoint HTTP {e.code}: {body}")


def b64url_basic(cid: str, secret: str) -> str:
    return base64.b64encode(f"{cid}:{secret}".encode()).decode()


def save_tokens(tok: dict) -> None:
    tok["obtained_at"] = int(time.time())
    with open(TOKENS_FILE, "w") as f:
        json.dump(tok, f, indent=2)
    os.chmod(TOKENS_FILE, 0o600)


def load_tokens() -> dict:
    if not os.path.exists(TOKENS_FILE):
        sys.exit("No saved tokens. Run `auth` first.")
    with open(TOKENS_FILE) as f:
        return json.load(f)


class _CallbackHandler(BaseHTTPRequestHandler):
    captured: dict = {}

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != _CallbackHandler.expected_path:
            self.send_response(404)
            self.end_headers()
            return
        _CallbackHandler.captured = dict(urllib.parse.parse_qsl(parsed.query))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Authorized. You can close this tab and return to the terminal.</h2>")

    def log_message(self, *args):  # silence
        pass


class _LocalCallbackServer(HTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self) -> None:
        # Accept both ::1 and 127.0.0.1 when the OS supports dual-stack IPv6.
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except OSError:
            pass
        socketserver.TCPServer.server_bind(self)
        self.server_name = "bowerbird.localhost"
        self.server_port = self.server_address[1]


class _LocalCallbackServerIPv4(HTTPServer):
    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        self.server_name = "bowerbird.localhost"
        self.server_port = self.server_address[1]


def _callback_server(port: int):
    try:
        return _LocalCallbackServer(("::", port), _CallbackHandler)
    except OSError:
        return _LocalCallbackServerIPv4(("127.0.0.1", port), _CallbackHandler)


def cmd_auth(_args) -> None:
    c = cfg()
    verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(16)

    parts = urllib.parse.urlparse(c["redirect_uri"])
    _CallbackHandler.expected_path = parts.path or "/callback"
    port = parts.port or 8080

    params = {
        "response_type": "code",
        "client_id": c["client_id"],
        "redirect_uri": c["redirect_uri"],
        "scope": c["scopes"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)

    print("Opening browser to authorize. If it doesn't open, paste this URL:\n")
    print(url + "\n")
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass

    print(f"Waiting for the redirect on {c['redirect_uri']} ...")
    server = _callback_server(port)
    server.handle_request()  # blocks until one callback arrives
    captured = _CallbackHandler.captured

    if captured.get("state") != state:
        sys.exit(f"State mismatch (possible CSRF). Got: {captured}")
    if "code" not in captured:
        sys.exit(f"No authorization code returned: {captured}")

    tok = token_request(
        {
            "grant_type": "authorization_code",
            "code": captured["code"],
            "redirect_uri": c["redirect_uri"],
            "code_verifier": verifier,
            "client_id": c["client_id"],
        },
        c,
    )
    save_tokens(tok)
    print("\n✅ Auth OK. Tokens saved to", TOKENS_FILE)
    print("   scopes granted:", tok.get("scope"))
    print("   has refresh_token:", bool(tok.get("refresh_token")))
    print("   access token expires_in:", tok.get("expires_in"), "seconds")


def cmd_refresh(_args) -> None:
    c = cfg()
    old = load_tokens()
    if not old.get("refresh_token"):
        sys.exit("No refresh_token saved (did you include offline.access?).")
    new = token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": old["refresh_token"],
            "client_id": c["client_id"],
        },
        c,
    )
    rotated = new.get("refresh_token") != old.get("refresh_token")
    save_tokens(new)
    print("✅ Refresh OK. New access token issued.")
    print("   refresh token ROTATED:", rotated,
          "(if True, TokenStore MUST persist the new refresh token on every refresh)")
    print("   new scopes:", new.get("scope"))


def _get(path: str, query: str | None) -> None:
    tok = load_tokens()
    access = tok.get("access_token")
    if path.startswith("http"):
        url = path
    else:
        url = API_BASE + path.lstrip("/")
    if query:
        sep = "&" if "?" in url else "?"
        url += sep + urllib.parse.urlencode({"query": query})
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {access}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"HTTP {resp.status}  {url}")
            print(json.dumps(json.load(resp), indent=2)[:6000])
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"HTTP {e.code}  {url}\n{body}")
        if e.code == 401:
            print("\n(401 — try `python3 bin/x_auth_spike.py refresh` then retry.)")


def cmd_get(args) -> None:
    _get(args.path, args.query)


def cmd_me(_args) -> None:
    _get("users/me", None)


def cmd_search(args) -> None:
    """Full-archive search is APP-ONLY auth (Bearer token), not user-context."""
    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        sys.exit("Set X_BEARER_TOKEN in bin/.env (portal -> Keys and tokens -> Bearer Token). "
                 "Full-archive search requires OAuth 2.0 Application-Only auth.")
    url = API_BASE + "tweets/search/all"
    url += "?" + urllib.parse.urlencode({"query": args.query, "max_results": 100})
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {bearer}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
            print(f"HTTP {resp.status}  {url}")
            print("result_count:", data.get("meta", {}).get("result_count"))
            print(json.dumps(data, indent=2)[:5000])
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}  {url}\n{e.read().decode(errors='replace')}")


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"), description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth").set_defaults(func=cmd_auth)
    sub.add_parser("refresh").set_defaults(func=cmd_refresh)
    sub.add_parser("me").set_defaults(func=cmd_me)
    g = sub.add_parser("get")
    g.add_argument("path", help="API path, e.g. users/<id>/bookmarks/folders")
    g.add_argument("--query", help="value for the ?query= param (search endpoints)")
    g.set_defaults(func=cmd_get)
    s = sub.add_parser("search")
    s.add_argument("--query", required=True, help="search query, e.g. conversation_id:123")
    s.set_defaults(func=cmd_search)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
