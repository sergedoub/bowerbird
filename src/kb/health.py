"""Text-first health checks for a Bowerbird checkout.

The web UI used to own this surface. The checks here are pure over files and an
injected lint result so the CLI, agents, and tests can all use the same contract.
"""
from __future__ import annotations

import datetime as dt
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .config import AccountsConfig, ConfigError, TopicsConfig


@dataclass(frozen=True)
class LintStatus:
    exit_code: int
    output: str = ""


@dataclass(frozen=True)
class HealthItem:
    name: str
    status: str
    message: str
    details: Mapping[str, Any]

    @property
    def ok(self) -> bool:
        return self.status != "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class HealthReport:
    ok: bool
    items: tuple[HealthItem, ...]

    @property
    def issues(self) -> tuple[str, ...]:
        return tuple(item.message for item in self.items if item.status == "error")

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(item.message for item in self.items if item.status == "warn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "items": [item.to_dict() for item in self.items],
            "issues": list(self.issues),
            "warnings": list(self.warnings),
        }


def _item(name: str, status: str, message: str, **details: Any) -> HealthItem:
    return HealthItem(name=name, status=status, message=message, details=details)


def _config_error(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "missing"
    if isinstance(exc, tomllib.TOMLDecodeError):
        return f"invalid TOML: {exc}"
    return f"invalid: {exc}"


def _check_topics(repo_root: Path) -> HealthItem:
    path = repo_root / "config" / "topics.toml"
    try:
        config = TopicsConfig.load(path)
    except (FileNotFoundError, tomllib.TOMLDecodeError, ConfigError) as exc:
        return _item("config_topics", "error", f"config/topics.toml {_config_error(exc)}",
                     path=str(path))
    count = len(config.topics)
    return _item("config_topics", "ok", f"config/topics.toml valid ({count} topic(s))",
                 path=str(path), topics=count)


def _check_accounts(repo_root: Path) -> HealthItem:
    path = repo_root / "config" / "accounts.toml"
    try:
        config = AccountsConfig.load(path)
    except (FileNotFoundError, tomllib.TOMLDecodeError, ConfigError) as exc:
        return _item("config_accounts", "error",
                     f"config/accounts.toml {_config_error(exc)}", path=str(path))
    count = len(config.accounts)
    return _item("config_accounts", "ok", f"config/accounts.toml valid ({count} account(s))",
                 path=str(path), accounts=count)


def _parse_date(value: object) -> dt.date | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _summary_int(summary: Mapping[str, Any], key: str) -> int | None:
    value = summary.get(key, 0)
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _check_recap_feed(repo_root: Path, today: dt.date, max_feed_age_days: int) -> list[HealthItem]:
    path = repo_root / "compile" / "recap-feed.json"
    if not path.exists():
        return [_item("recap_feed", "error", "compile/recap-feed.json missing", path=str(path))]
    try:
        feed = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [_item("recap_feed", "error", f"compile/recap-feed.json invalid JSON: {exc}",
                      path=str(path))]
    if not isinstance(feed, dict):
        return [_item("recap_feed", "error", "compile/recap-feed.json must be a JSON object",
                      path=str(path))]

    summary = feed.get("summary", {})
    if not isinstance(summary, dict):
        return [_item("recap_feed", "error", "compile/recap-feed.json has no summary object",
                      path=str(path))]
    generated = _parse_date(feed.get("generated"))
    if generated is None:
        return [_item("recap_feed", "error", "compile/recap-feed.json has invalid generated date",
                      path=str(path), generated=feed.get("generated"))]

    total_new = _summary_int(summary, "total_new")
    account_lanes = _summary_int(summary, "account_lanes")
    topic_lanes = _summary_int(summary, "topic_lanes")
    if total_new is None or account_lanes is None or topic_lanes is None:
        return [_item("recap_feed", "error", "compile/recap-feed.json has invalid summary counts",
                      path=str(path), summary=summary)]
    items = [
        _item(
            "recap_feed",
            "ok",
            f"compile/recap-feed.json valid ({total_new} new note(s))",
            path=str(path),
            generated=generated.isoformat(),
            total_new=total_new,
            account_lanes=account_lanes,
            topic_lanes=topic_lanes,
        )
    ]

    age_days = (today - generated).days
    if age_days < 0:
        status = "warn"
        message = f"recap feed generated in the future ({generated.isoformat()})"
    elif age_days > max_feed_age_days:
        status = "warn"
        message = f"recap feed is {age_days} day(s) old"
    else:
        status = "ok"
        message = f"recap feed is fresh ({age_days} day(s) old)"
    items.append(_item("recap_freshness", status, message, generated=generated.isoformat(),
                       today=today.isoformat(), age_days=age_days,
                       max_feed_age_days=max_feed_age_days))
    return items


def _check_lint(lint_status: LintStatus | None) -> HealthItem:
    if lint_status is None:
        return _item("lint", "warn", "provenance lint was not run")
    output = lint_status.output.strip()
    if lint_status.exit_code == 0:
        return _item("lint", "ok", output or "provenance lint passed",
                     exit_code=lint_status.exit_code)
    first_lines = "\n".join(output.splitlines()[:8])
    return _item("lint", "error", first_lines or "provenance lint failed",
                 exit_code=lint_status.exit_code)


class HealthCheck:
    def __init__(self, stale_after_days: int = 14) -> None:
        self.stale_after_days = stale_after_days

    def check(
        self,
        repo_root: str | Path,
        *,
        today: dt.date | None = None,
        lint_status: LintStatus | None = None,
    ) -> HealthReport:
        root = Path(repo_root)
        actual_today = today or dt.datetime.now(dt.UTC).date()
        items = [
            _check_topics(root),
            _check_accounts(root),
            *_check_recap_feed(root, actual_today, self.stale_after_days),
            _check_lint(lint_status),
        ]
        return HealthReport(
            ok=all(item.status != "error" for item in items),
            items=tuple(items),
        )


def report_to_text(report: HealthReport) -> str:
    lines = ["Bowerbird doctor", f"status: {'ok' if report.ok else 'error'}"]
    for item in report.items:
        label = item.status.upper()
        lines.append(f"{label:<5} {item.name}: {item.message}")
    return "\n".join(lines)
