#!/usr/bin/env python3
"""Dump ALL X bookmarks (every folder + unsorted) to local raw markdown files.

Separate from the topic pipeline: this hits the GLOBAL bookmarks endpoint, which returns
full tweet content as "owned reads" (~$0.001 each, ~$0.20 for a few hundred). Each bookmark
becomes one file in OUTPUT_DIR, idempotent (skips files that already exist). Bookmarks are
tagged with any folder(s) they belong to (cross-referenced from the folder-contents endpoint)
to help later classification.

Auth: OAuth2 user-context via bin/.env (X_CLIENT_ID/SECRET) + bin/.x_tokens.json.
If the token is stale, run `python3 bin/x_auth_spike.py auth` first, then re-run this.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bowerbird.models import RawDoc                         # noqa: E402
from bowerbird.raw_writer import render                     # noqa: E402
from bowerbird.tokens import FileTokenStorage, TokenStore   # noqa: E402

USER_ID = os.environ.get("X_USER_ID", "201559911")
OUTPUT_DIR = os.path.expanduser("~/x-bookmarks-raw")
API = "https://api.x.com/2/"
TWEET_FIELDS = "conversation_id,author_id,created_at,note_tweet,referenced_tweets,article"


def load_env() -> None:
    path = os.path.join(HERE, ".env")
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def make_get(token_store: TokenStore):
    def get(path: str, params: dict) -> dict:
        url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {token_store.get_access_token()}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    return get


def folder_map(get) -> dict[str, list[str]]:
    """tweet_id -> [folder names] (folder-contents endpoint returns only ids)."""
    out: dict[str, list[str]] = {}
    folders = get(f"users/{USER_ID}/bookmarks/folders", {}).get("data", [])
    for f in folders:
        params: dict = {}
        while True:
            page = get(f"users/{USER_ID}/bookmarks/folders/{f['id']}", params)
            for item in page.get("data", []):
                out.setdefault(item["id"], []).append(f["name"])
            nxt = page.get("meta", {}).get("next_token")
            if not nxt:
                break
            params["pagination_token"] = nxt
    return out


def doc_for(t: dict, users: dict[str, str], folders: list[str]) -> RawDoc:
    text = (t.get("note_tweet") or {}).get("text") or t.get("text", "")
    article = t.get("article") or {}
    handle = users.get(t.get("author_id", ""))
    body_parts = [text]
    if article.get("plain_text") or article.get("title"):
        body_parts.append(f"## Article: {article.get('title', '')}\n\n{article.get('plain_text', '')}")
    fm = {
        "id": t["id"],
        "author": f"@{handle}" if handle else t.get("author_id", ""),
        "author_id": t.get("author_id", ""),
        "conversation_id": t.get("conversation_id", t["id"]),
        "created_at": t.get("created_at", ""),
        "source_url": f"https://x.com/i/web/status/{t['id']}",
    }
    if article.get("title"):
        fm["article_title"] = article["title"]
    if folders:
        fm["folders"] = ", ".join(folders)
    return RawDoc(topic="", id=t["id"], created_at=t.get("created_at", ""),
                  frontmatter=fm, body="\n\n".join(p for p in body_parts if p))


def main() -> None:
    load_env()
    token_store = TokenStore(
        os.environ["X_CLIENT_ID"], os.environ.get("X_CLIENT_SECRET"),
        FileTokenStorage(os.path.join(HERE, ".x_tokens.json")),
    )
    get = make_get(token_store)
    try:
        token_store.get_access_token()
    except urllib.error.HTTPError as e:
        if e.code in (400, 401):
            sys.exit("Token is stale. Run:  python3 bin/x_auth_spike.py auth   then re-run this.")
        raise

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("mapping folders...")
    fmap = folder_map(get)

    params = {
        "max_results": 100,
        "tweet.fields": TWEET_FIELDS,
        "expansions": "author_id",
        "user.fields": "username",
    }
    total = written = skipped = 0
    while True:
        page = get(f"users/{USER_ID}/bookmarks", params)
        users = {u["id"]: u["username"] for u in page.get("includes", {}).get("users", []) if u.get("username")}
        for t in page.get("data", []):
            total += 1
            doc = doc_for(t, users, fmap.get(t["id"], []))
            fname = f"{doc.created_at[:10]}__{doc.id}.md"
            path = os.path.join(OUTPUT_DIR, fname)
            if os.path.exists(path):
                skipped += 1
                continue
            with open(path, "w") as fh:
                fh.write(render(doc))
            written += 1
        nxt = page.get("meta", {}).get("next_token")
        if not nxt:
            break
        params["pagination_token"] = nxt

    print(f"\n--- dump complete ---")
    print(f"bookmarks seen:   {total}")
    print(f"files written:    {written}")
    print(f"skipped (exists): {skipped}")
    print(f"output dir:       {OUTPUT_DIR}")
    print(f"approx cost:      ${total * 0.001:.3f} (owned reads)")


if __name__ == "__main__":
    main()
