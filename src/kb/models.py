"""Plain data records passed between modules. No behavior, no I/O."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tweet:
    """A single post, as returned by the bookmarks or search endpoints.

    `text` is the FULL text (note_tweet.text for long tweets, else the 280-char text).
    `replied_to` is the parent tweet id (from referenced_tweets), used to walk self-threads.
    """
    id: str
    author_id: str
    conversation_id: str
    created_at: str  # ISO 8601, e.g. "2026-01-10T15:37:12.000Z"
    text: str
    replied_to: str | None = None


def tweet_from_api(t: dict) -> Tweet:
    """Build a Tweet from a v2 API object: prefer note_tweet.text; extract the reply parent."""
    note = (t.get("note_tweet") or {}).get("text")
    replied_to = None
    for ref in t.get("referenced_tweets") or []:
        if ref.get("type") == "replied_to":
            replied_to = ref.get("id")
            break
    return Tweet(
        id=t["id"],
        author_id=t.get("author_id", ""),
        conversation_id=t.get("conversation_id", t["id"]),
        created_at=t.get("created_at", ""),
        text=note or t.get("text", ""),
        replied_to=replied_to,
    )


# Tweet fields every read should request: full text (note_tweet), thread links
# (referenced_tweets), and X-native Article content (article.plain_text).
TWEET_FIELDS = "conversation_id,author_id,created_at,note_tweet,referenced_tweets,article"


@dataclass(frozen=True)
class Bookmark:
    """A bookmarked post plus the folder/topic it was filed under."""
    tweet: Tweet
    folder_id: str
    topic: str
    article_title: str | None = None      # X-native Article title (or link-card title)
    article_text: str | None = None       # full X-native Article body (article.plain_text)
    author_username: str | None = None    # @handle, when resolvable via expansions

    @property
    def is_thread_head(self) -> bool:
        # The head of a thread has id == conversation_id.
        return self.tweet.id == self.tweet.conversation_id


@dataclass(frozen=True)
class Thread:
    """A reconstructed self-thread: the head author's posts in chronological order."""
    head_id: str
    author_id: str
    conversation_id: str
    tweets: tuple[Tweet, ...] = field(default_factory=tuple)

    @property
    def text(self) -> str:
        return "\n\n".join(t.text for t in self.tweets)


@dataclass(frozen=True)
class RawAddress:
    """Storage address under raw/<namespace>/<bucket>/."""
    namespace: str
    bucket: str


@dataclass(frozen=True)
class RawDoc:
    """A unit to persist into the append-only raw layer."""
    topic: str
    id: str          # stable id (the tweet/conversation id) -> deterministic filename
    created_at: str  # ISO 8601; the date prefixes the filename
    frontmatter: dict
    body: str
    address: RawAddress | None = None
