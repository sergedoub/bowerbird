#!/usr/bin/env python3
"""Backfill runner: pull a topic's bookmarked folder(s) into raw/bookmarks/<topic>/.

Wires the real clients together: bookmarks (user-context, cheap "owned reads" ~$0.001)
+ thread reconstruction (app-only search, ~$0.005/tweet). Threads are the cost driver,
so caps let us validate the pipeline cheaply before the full backlog:

  python3 bin/backfill.py --topic marketing --no-threads            # cheap: enumerate + single-tweet raw
  python3 bin/backfill.py --topic marketing --max-threads 3         # validate thread path on a few
  python3 bin/backfill.py --topic marketing                         # full run (reconstruct all heads)

Reads bin/.env for X_CLIENT_ID / X_CLIENT_SECRET / X_BEARER_TOKEN (and optional X_USER_ID).
Idempotent: re-runs skip already-written raw files.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.config import TopicsConfig           # noqa: E402
from kb.models import RawDoc                  # noqa: E402
from kb.raw_writer import RawWriter           # noqa: E402
from kb.search import SearchClient            # noqa: E402
from kb.threads import assemble               # noqa: E402
from kb.tokens import FileTokenStorage, TokenStore  # noqa: E402
from kb.x_client import XBookmarkClient       # noqa: E402


def load_env() -> None:
    path = os.path.join(HERE, ".env")
    if not os.path.exists(path):
        sys.exit("bin/.env not found.")
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def resolve_user_id(token_store: TokenStore) -> str:
    if os.environ.get("X_USER_ID"):
        return os.environ["X_USER_ID"]
    req = urllib.request.Request("https://api.x.com/2/users/me", method="GET")
    req.add_header("Authorization", f"Bearer {token_store.get_access_token()}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["data"]["id"]


def build_doc(bm, thread) -> RawDoc:
    t = bm.tweet
    tweet_count = len(thread.tweets) if thread else 1
    body = thread.text if thread else t.text
    if bm.article_title:
        body += f"\n\n[linked article: {bm.article_title}]"
    fm = {
        "topic": bm.topic,
        "author_id": t.author_id,
        "conversation_id": t.conversation_id,
        "created_at": t.created_at,
        "source_url": f"https://x.com/i/web/status/{t.id}",
        "folder_id": bm.folder_id,
        "tweet_count": tweet_count,
    }
    if bm.article_title:
        fm["article_title"] = bm.article_title
    return RawDoc(topic=bm.topic, id=t.id, created_at=t.created_at, frontmatter=fm, body=body)


def main() -> None:
    ap = argparse.ArgumentParser(prog=os.environ.get("BOWERBIRD_PROG"))
    ap.add_argument("--topic", help="single topic (default: all in config)")
    ap.add_argument("--limit", type=int, default=0, help="max bookmarks to process (0 = all)")
    ap.add_argument("--max-threads", type=int, default=0, help="cap thread reconstructions (0 = no cap)")
    ap.add_argument("--no-threads", action="store_true", help="skip reconstruction (single-tweet raw)")
    args = ap.parse_args()

    load_env()
    token_store = TokenStore(
        os.environ["X_CLIENT_ID"], os.environ.get("X_CLIENT_SECRET"),
        FileTokenStorage(os.path.join(HERE, ".x_tokens.json")),
    )
    user_id = resolve_user_id(token_store)
    bookmarks = XBookmarkClient(user_id, token_store)
    search = SearchClient(os.environ["X_BEARER_TOKEN"])
    cfg = TopicsConfig.load(os.path.join(ROOT, "config", "topics.toml"))
    writer = RawWriter(os.path.join(ROOT, "raw", "bookmarks"))

    topics = [t for t in cfg.topics if (not args.topic or t.name == args.topic)]
    if not topics:
        sys.exit(f"topic '{args.topic}' not in config")

    seen = written = skipped = threads_done = thread_tweets = 0
    for topic in topics:
        for folder_id in topic.folder_ids:
            for bm in bookmarks.bookmarks_in_folder(folder_id, topic.name):
                if args.limit and seen >= args.limit:
                    break
                seen += 1
                thread = None
                do_threads = not args.no_threads and bm.is_thread_head
                if do_threads and (not args.max_threads or threads_done < args.max_threads):
                    thread = assemble(bm.tweet, search.fetch_conversation)
                    threads_done += 1
                    thread_tweets += len(thread.tweets)
                path = writer.write(build_doc(bm, thread))
                if path:
                    written += 1
                    print(f"  wrote {path.name}  ({'thread x' + str(len(thread.tweets)) if thread else 'single'})")
                else:
                    skipped += 1

    est_cost = seen * 0.001 + thread_tweets * 0.005
    print(f"\n--- backfill summary ({', '.join(t.name for t in topics)}) ---")
    print(f"bookmarks seen:        {seen}")
    print(f"raw files written:     {written}")
    print(f"skipped (already had): {skipped}")
    print(f"threads reconstructed: {threads_done} ({thread_tweets} tweets)")
    print(f"approx X API cost:     ${est_cost:.3f}")


if __name__ == "__main__":
    main()
