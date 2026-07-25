"""Safe GitHub CLI transport for Actions secret values."""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from os import PathLike


def set_github_secret(
    name: str,
    value: str,
    *,
    cwd: str | PathLike[str],
    repo: str = "",
    runner: Callable = subprocess.run,
):
    """Set one Actions secret with its value on stdin, never in process arguments."""
    command = ["gh", "secret", "set", name]
    if repo:
        command += ["--repo", repo]
    return runner(command, cwd=cwd, input=value.encode(), capture_output=True)
