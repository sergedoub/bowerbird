"""TopicsConfig — the topic -> X folder allowlist (extensibility seam).

Reads config/topics.toml with the stdlib tomllib (no dependency). Validates that
every topic has at least one folder and that no folder feeds two topics (which
would make routing ambiguous).
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Topic:
    name: str
    folder_ids: tuple[str, ...]


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TopicsConfig:
    topics: tuple[Topic, ...]

    @classmethod
    def load(cls, path: str | Path) -> "TopicsConfig":
        data = tomllib.loads(Path(path).read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "TopicsConfig":
        raw = data.get("topics", {})
        if not raw:
            raise ConfigError("no [topics.*] tables found in config")
        topics: list[Topic] = []
        seen_folders: dict[str, str] = {}
        for name, body in raw.items():
            folder_ids = tuple(body.get("folder_ids", []))
            if not folder_ids:
                raise ConfigError(f"topic '{name}' has no folder_ids")
            for fid in folder_ids:
                if fid in seen_folders:
                    raise ConfigError(
                        f"folder {fid} is mapped to both '{seen_folders[fid]}' and '{name}'"
                    )
                seen_folders[fid] = name
            topics.append(Topic(name=name, folder_ids=folder_ids))
        return cls(topics=tuple(topics))

    def folder_to_topic(self) -> dict[str, str]:
        return {fid: t.name for t in self.topics for fid in t.folder_ids}

    def folder_ids(self) -> list[str]:
        return [fid for t in self.topics for fid in t.folder_ids]


OFF_TOPIC_POLICIES = ("skip", "quarantine")


@dataclass(frozen=True)
class Account:
    """An X account to mirror in full.

    `handle` is the username without the leading '@'. `topic` names the topic into
    which the compile step distills this account's posts (`wiki/<topic>/sources/`).
    `off_topic` is the policy for posts that don't fit the configured topic — currently
    only "skip" is implemented; "quarantine" is reserved for a future parking lot.
    `label` is an optional display name used by the recap feed (defaults to the handle).
    """
    handle: str
    topic: str
    off_topic: str = "skip"
    label: str | None = None


@dataclass(frozen=True)
class AccountsConfig:
    """The list of accounts whose full output (posts + replies) we dump daily.

    Reads config/accounts.toml. Each account is a `[[handles]]` table:

        [[handles]]
        handle = "bcherny"
        topic  = "claude-code"
        off_topic = "skip"

    Normalizes any stray leading '@' on the handle and rejects duplicates (which would
    dump the same account twice). `topic` is required so the compile step knows where
    to route distilled source notes; the topic itself doesn't need to exist in
    topics.toml — accounts feed directly into `wiki/<topic>/`, no bookmarks
    folder required.
    """
    accounts: tuple[Account, ...]

    @classmethod
    def load(cls, path: str | Path) -> "AccountsConfig":
        return cls.from_dict(tomllib.loads(Path(path).read_text()))

    @classmethod
    def from_dict(cls, data: dict) -> "AccountsConfig":
        handles = data.get("handles", [])
        if not handles:
            raise ConfigError("no [[handles]] entries found in accounts config")
        seen: set[str] = set()
        accounts: list[Account] = []
        for raw in handles:
            if not isinstance(raw, dict):
                raise ConfigError(
                    f"accounts config entry must be a table with handle+topic, got {raw!r}"
                )
            handle = str(raw.get("handle", "")).lstrip("@").strip()
            topic = str(raw.get("topic", "")).strip()
            off_topic = str(raw.get("off_topic", "skip")).strip() or "skip"
            if not handle:
                raise ConfigError(f"missing handle in accounts entry: {raw!r}")
            if not topic:
                raise ConfigError(f"missing topic for handle '{handle}' in accounts config")
            if off_topic not in OFF_TOPIC_POLICIES:
                raise ConfigError(
                    f"unknown off_topic policy '{off_topic}' for '{handle}' "
                    f"(expected one of {OFF_TOPIC_POLICIES})"
                )
            if handle.lower() in seen:
                raise ConfigError(f"duplicate handle '{handle}' in accounts config")
            seen.add(handle.lower())
            label = str(raw.get("label", "")).strip() or None
            accounts.append(Account(handle=handle, topic=topic, off_topic=off_topic, label=label))
        return cls(accounts=tuple(accounts))


@dataclass(frozen=True)
class Book:
    """A long-form Markdown book to split into raw chapter inputs."""

    book_id: str
    topic: str
    title: str
    author: str
    published_date: str
    source_path: str
    provenance: str = "external-expert"


@dataclass(frozen=True)
class BooksConfig:
    """Books configured for one-shot local ingestion into raw/books/<topic>/."""

    books: tuple[Book, ...]

    @classmethod
    def load(cls, path: str | Path) -> "BooksConfig":
        return cls.from_dict(tomllib.loads(Path(path).read_text()))

    @classmethod
    def from_dict(cls, data: dict) -> "BooksConfig":
        raw_books = data.get("books", [])
        if not raw_books:
            raise ConfigError("no [[books]] entries found in books config")

        seen: set[str] = set()
        books: list[Book] = []
        for raw in raw_books:
            if not isinstance(raw, dict):
                raise ConfigError(f"books config entry must be a table, got {raw!r}")

            book_id = str(raw.get("book_id", "")).strip()
            topic = str(raw.get("topic", "")).strip()
            title = str(raw.get("title", "")).strip()
            author = str(raw.get("author", "")).strip()
            published_date = str(raw.get("published_date", "")).strip()
            source_path = str(raw.get("source_path", "")).strip()
            provenance = str(raw.get("provenance", "external-expert")).strip() or "external-expert"

            missing = [
                name for name, value in (
                    ("book_id", book_id),
                    ("topic", topic),
                    ("title", title),
                    ("author", author),
                    ("published_date", published_date),
                    ("source_path", source_path),
                )
                if not value
            ]
            if missing:
                raise ConfigError(f"book config entry missing required fields: {', '.join(missing)}")
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", book_id):
                raise ConfigError(
                    f"book_id '{book_id}' must be a lowercase slug with letters, numbers, and hyphens"
                )
            if provenance not in ("first-party", "external-expert", "community"):
                raise ConfigError(
                    f"unknown provenance '{provenance}' for book '{book_id}'"
                )
            if book_id in seen:
                raise ConfigError(f"duplicate book_id '{book_id}' in books config")

            seen.add(book_id)
            books.append(
                Book(
                    book_id=book_id,
                    topic=topic,
                    title=title,
                    author=author,
                    published_date=published_date,
                    source_path=source_path,
                    provenance=provenance,
                )
            )
        return cls(books=tuple(books))

    def get(self, book_id: str) -> Book:
        for book in self.books:
            if book.book_id == book_id:
                return book
        raise ConfigError(f"book '{book_id}' not in config")
