"""Text-first health checks for a Bowerbird checkout.

The checks here are pure over files and an injected lint result so the CLI,
agents, and tests can all use the same contract without any UI server.
"""
from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .config import AccountsConfig, ConfigError, RecapsConfig, TopicsConfig
from .recaps import validate_recap_files


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


def _check_recaps_config(repo_root: Path) -> HealthItem:
    path = repo_root / "config" / "recaps.toml"
    try:
        config = RecapsConfig.load(path)
    except (FileNotFoundError, tomllib.TOMLDecodeError, ConfigError) as exc:
        return _item("config_recaps", "error", f"config/recaps.toml {_config_error(exc)}",
                     path=str(path))

    missing_prompts = [
        profile.prompt_path
        for profile in config.profiles
        if not (repo_root / profile.prompt_path).is_file()
    ]
    if missing_prompts:
        return _item(
            "config_recaps",
            "error",
            "recap prompt file missing: " + ", ".join(missing_prompts),
            path=str(path),
            missing_prompts=missing_prompts,
        )
    deliveries = sum(len(profile.deliveries) for profile in config.profiles)
    return _item(
        "config_recaps",
        "ok",
        f"config/recaps.toml valid ({len(config.profiles)} profile(s), {deliveries} delivery target(s))",
        path=str(path),
        profiles=len(config.profiles),
        deliveries=deliveries,
    )


def _check_recap_files(repo_root: Path) -> HealthItem:
    issues = validate_recap_files(repo_root)
    if issues:
        return _item(
            "recaps",
            "error",
            "\n".join(issues[:8]),
            issues=issues,
        )
    recaps_dir = repo_root / "recaps"
    recap_count = len(list(recaps_dir.glob("*/*.md"))) if recaps_dir.exists() else 0
    manifest_dir = recaps_dir / "manifests"
    manifest_count = len(list(manifest_dir.glob("*.json"))) if manifest_dir.exists() else 0
    return _item(
        "recaps",
        "ok",
        f"recaps/ valid ({recap_count} recap file(s), {manifest_count} manifest(s))",
        recap_files=recap_count,
        manifests=manifest_count,
    )


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
        items = [
            _check_topics(root),
            _check_accounts(root),
            _check_recaps_config(root),
            _check_recap_files(root),
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
