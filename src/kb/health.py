"""HealthCheck — observability for the unattended pipeline (writes _health.md / alerts).

STUB. The system runs hands-off, so health is detected, not reviewed. Most important
signal: staleness — "no new raw sources in N days" flags a silent token death (the X
refresh token expires after ~6 months of inactivity). Also: lint-violation summary and
thin-source counts. Implementation lands with the GitHub Actions wiring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class HealthReport:
    ok: bool
    issues: tuple[str, ...] = field(default_factory=tuple)


class HealthCheck:
    def __init__(self, stale_after_days: int = 14) -> None:
        self.stale_after_days = stale_after_days

    def check(self, repo_root: str | Path) -> HealthReport:
        raise NotImplementedError("HealthCheck.check — implemented with the Actions wiring")
