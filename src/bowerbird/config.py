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


RECAP_FREQUENCIES = ("daily", "weekly", "hourly")
RECAP_FORMATS = ("markdown", "slack_mrkdwn", "email_markdown")
RECAP_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _slug(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]*", value))


@dataclass(frozen=True)
class DeliveryTarget:
    """A non-secret delivery target for a generated recap file."""

    kind: str
    destination: str


@dataclass(frozen=True)
class RecapProfile:
    """A durable recap file profile.

    Presence in config/recaps.toml means the profile is active. Secrets stay out
    of this config; destinations are non-secret handoff coordinates consumed by
    delivery adapters.
    """

    name: str
    frequency: str
    prompt_path: str
    output_format: str
    accounts: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    deliveries: tuple[DeliveryTarget, ...] = ()
    weekly_due_day: str = "monday"
    interval_hours: int = 1
    include_urls: bool = False


@dataclass(frozen=True)
class RecapsConfig:
    profiles: tuple[RecapProfile, ...]

    @classmethod
    def load(cls, path: str | Path) -> "RecapsConfig":
        return cls.from_dict(tomllib.loads(Path(path).read_text()))

    @classmethod
    def from_dict(cls, data: dict) -> "RecapsConfig":
        raw_profiles = data.get("recaps", [])
        if not isinstance(raw_profiles, list):
            raise ConfigError("recaps config must use [[recaps]] tables")
        if not raw_profiles:
            return cls(profiles=())

        profiles: list[RecapProfile] = []
        seen: set[str] = set()
        for raw in raw_profiles:
            if not isinstance(raw, dict):
                raise ConfigError(f"recap profile must be a table, got {raw!r}")

            name = str(raw.get("name", "")).strip()
            if not name:
                raise ConfigError("recap profile missing name")
            if not _slug(name):
                raise ConfigError(
                    f"recap profile '{name}' must be a lowercase slug with letters, numbers, and hyphens"
                )
            if name in seen:
                raise ConfigError(f"duplicate recap profile '{name}'")
            seen.add(name)

            frequency = str(raw.get("frequency", "")).strip().lower()
            if frequency not in RECAP_FREQUENCIES:
                raise ConfigError(
                    f"recap profile '{name}' has unknown frequency '{frequency}' "
                    f"(expected one of {RECAP_FREQUENCIES})"
                )
            output_format = str(raw.get("format", "markdown")).strip().lower() or "markdown"
            if output_format not in RECAP_FORMATS:
                raise ConfigError(
                    f"recap profile '{name}' has unknown format '{output_format}' "
                    f"(expected one of {RECAP_FORMATS})"
                )
            prompt_path = str(raw.get("prompt", "")).strip()
            if not prompt_path:
                raise ConfigError(f"recap profile '{name}' missing prompt")
            if not prompt_path.startswith("compile/recaps/"):
                raise ConfigError(
                    f"recap profile '{name}' prompt must live under compile/recaps/"
                )

            weekly_due_day = str(raw.get("weekly_due_day", "monday")).strip().lower() or "monday"
            if weekly_due_day not in RECAP_WEEKDAYS:
                raise ConfigError(
                    f"recap profile '{name}' has unknown weekly_due_day '{weekly_due_day}' "
                    f"(expected one of {RECAP_WEEKDAYS})"
                )
            interval_hours = _positive_int(raw.get("interval_hours", 1), f"recap profile '{name}' interval_hours")
            if frequency == "hourly" and 24 % interval_hours != 0:
                raise ConfigError(
                    f"recap profile '{name}' interval_hours must divide 24 for UTC windows"
                )
            include_urls = bool(raw.get("include_urls", False))

            accounts = tuple(
                value.lstrip("@").strip().lower()
                for value in _string_list(name, "accounts", raw.get("accounts", []))
                if value.lstrip("@").strip()
            )
            topics = tuple(
                value.strip()
                for value in _string_list(name, "topics", raw.get("topics", []))
                if value.strip()
            )
            if not accounts and not topics:
                raise ConfigError(f"recap profile '{name}' must select at least one account or topic")
            if len(set(accounts)) != len(accounts):
                raise ConfigError(f"recap profile '{name}' has duplicate accounts")
            if len(set(topics)) != len(topics):
                raise ConfigError(f"recap profile '{name}' has duplicate topics")

            raw_deliveries = raw.get("deliveries", [])
            if not isinstance(raw_deliveries, list):
                raise ConfigError(f"recap profile '{name}' deliveries must be an array")
            deliveries = tuple(_parse_delivery_target(name, item) for item in raw_deliveries)
            profiles.append(
                RecapProfile(
                    name=name,
                    frequency=frequency,
                    prompt_path=prompt_path,
                    output_format=output_format,
                    accounts=accounts,
                    topics=topics,
                    deliveries=deliveries,
                    weekly_due_day=weekly_due_day,
                    interval_hours=interval_hours,
                    include_urls=include_urls,
                )
            )
        return cls(profiles=tuple(profiles))


def _positive_int(raw: object, label: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{label} must be an integer") from exc
    if value <= 0:
        raise ConfigError(f"{label} must be positive")
    return value


def _string_list(profile_name: str, field: str, raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise ConfigError(f"recap profile '{profile_name}' {field} must be an array")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ConfigError(f"recap profile '{profile_name}' {field} must contain strings")
        values.append(item)
    return tuple(values)


def _parse_delivery_target(profile_name: str, raw: object) -> DeliveryTarget:
    if not isinstance(raw, dict):
        raise ConfigError(f"recap profile '{profile_name}' delivery must be a table, got {raw!r}")
    kind = str(raw.get("type", "")).strip().lower()
    destination = str(raw.get("destination", "")).strip()
    if not kind:
        raise ConfigError(f"recap profile '{profile_name}' delivery missing type")
    if not _slug(kind):
        raise ConfigError(
            f"recap profile '{profile_name}' delivery type '{kind}' must be a lowercase slug"
        )
    if not destination:
        raise ConfigError(f"recap profile '{profile_name}' delivery missing destination")
    return DeliveryTarget(kind=kind, destination=destination)


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
            return cls(topics=())
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


@dataclass(frozen=True)
class Account:
    """An X account to mirror in full.

    `handle` is the username without the leading '@'. `topic` names the topic into
    which the compile step distills this account's posts (`wiki/<topic>/sources/`).
    `label` is an optional display name used by recap profiles (defaults to the handle).
    """
    handle: str
    topic: str
    label: str | None = None


@dataclass(frozen=True)
class AccountsConfig:
    """The list of accounts whose full output (posts + replies) we dump daily.

    Reads config/accounts.toml. Each account is a `[[handles]]` table:

        [[handles]]
        handle = "account_one"
        topic  = "ai-updates"

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
            return cls(accounts=())
        seen: set[str] = set()
        accounts: list[Account] = []
        for raw in handles:
            if not isinstance(raw, dict):
                raise ConfigError(
                    f"accounts config entry must be a table with handle+topic, got {raw!r}"
                )
            handle = str(raw.get("handle", "")).lstrip("@").strip()
            topic = str(raw.get("topic", "")).strip()
            if not handle:
                raise ConfigError(f"missing handle in accounts entry: {raw!r}")
            if not topic:
                raise ConfigError(f"missing topic for handle '{handle}' in accounts config")
            if handle.lower() in seen:
                raise ConfigError(f"duplicate handle '{handle}' in accounts config")
            seen.add(handle.lower())
            label = str(raw.get("label", "")).strip() or None
            accounts.append(Account(handle=handle, topic=topic, label=label))
        return cls(accounts=tuple(accounts))


@dataclass(frozen=True)
class SearchMonitor:
    """An X Recent Search monitor that writes raw/searches/<name>/."""

    name: str
    topic: str
    query: str
    label: str | None = None
    lookback_hours: int = 24
    max_results: int = 10
    max_pages: int = 1


@dataclass(frozen=True)
class SearchesConfig:
    """X keyword/search monitors configured in config/searches.toml."""

    searches: tuple[SearchMonitor, ...]

    @classmethod
    def load(cls, path: str | Path) -> "SearchesConfig":
        return cls.from_dict(tomllib.loads(Path(path).read_text()))

    @classmethod
    def from_dict(cls, data: dict) -> "SearchesConfig":
        raw_searches = data.get("searches", [])
        if not raw_searches:
            return cls(searches=())
        if not isinstance(raw_searches, list):
            raise ConfigError("searches config must use [[searches]] tables")

        searches: list[SearchMonitor] = []
        seen: set[str] = set()
        for raw in raw_searches:
            if not isinstance(raw, dict):
                raise ConfigError(f"search config entry must be a table, got {raw!r}")
            name = str(raw.get("name", "")).strip()
            topic = str(raw.get("topic", "")).strip()
            query = str(raw.get("query", "")).strip()
            if not name:
                raise ConfigError("search monitor missing name")
            if not _slug(name):
                raise ConfigError(
                    f"search monitor '{name}' must be a lowercase slug with letters, numbers, and hyphens"
                )
            if name in seen:
                raise ConfigError(f"duplicate search monitor '{name}'")
            seen.add(name)
            if not topic:
                raise ConfigError(f"search monitor '{name}' missing topic")
            if not _slug(topic):
                raise ConfigError(
                    f"search monitor '{name}' topic '{topic}' must be a lowercase slug"
                )
            if not query:
                raise ConfigError(f"search monitor '{name}' missing query")
            lookback_hours = _positive_int(
                raw.get("lookback_hours", 24),
                f"search monitor '{name}' lookback_hours",
            )
            if lookback_hours > 168:
                raise ConfigError(
                    f"search monitor '{name}' lookback_hours cannot exceed Recent Search's 7-day window"
                )
            max_results = _positive_int(
                raw.get("max_results", 10),
                f"search monitor '{name}' max_results",
            )
            if max_results < 10 or max_results > 100:
                raise ConfigError(f"search monitor '{name}' max_results must be between 10 and 100")
            max_pages = _positive_int(raw.get("max_pages", 1), f"search monitor '{name}' max_pages")
            label = str(raw.get("label", "")).strip() or None
            searches.append(
                SearchMonitor(
                    name=name,
                    topic=topic,
                    query=query,
                    label=label,
                    lookback_hours=lookback_hours,
                    max_results=max_results,
                    max_pages=max_pages,
                )
            )
        return cls(searches=tuple(searches))


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
