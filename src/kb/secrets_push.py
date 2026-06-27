"""Non-interactive GitHub Actions secret push — file-based, nothing typed.

The agent-native counterpart to the wizard's secrets step: credentials staged in the
gitignored bin/.env (e.g. piped from a portal Copy button by a coding agent) plus the
OAuth token file are pushed to the repo's Actions secrets via `gh secret set`. Secret
VALUES never appear on stdout or in the command line — they flow file -> gh stdin.

Pure over an injected setter, so it's unit-testable offline.
"""
from __future__ import annotations

from collections.abc import Callable

# Keys the workflows may need, in push order. X_TOKENS comes from the token file.
ENV_SECRET_KEYS = ("X_CLIENT_ID", "X_CLIENT_SECRET", "X_BEARER_TOKEN",
                   "GH_PAT", "OPENAI_API_KEY", "CODEX_ACCESS_TOKEN", "ANTHROPIC_API_KEY",
                   "GEMINI_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "SLACK_BOT_TOKEN")
LIVE_INSTANCE_VARIABLE = "BOWERBIRD_LIVE_INSTANCE"
LIVE_INSTANCE_SECRET_NAMES = ("X_CLIENT_ID", "X_BEARER_TOKEN", "X_TOKENS", "GH_PAT")


def push_secrets(
    env: dict,
    tokens_json: str,
    set_secret: Callable[[str, str], bool],
) -> dict:
    """Push every staged secret; returns {"set": [...], "skipped": [...], "failed": [...]}.

    `env` is the parsed bin/.env; `tokens_json` the raw token file contents ("" if the
    OAuth flow hasn't run); `set_secret(name, value)` performs one push (gh-backed in
    bin/, faked in tests). Only key NAMES are reported — never values.
    """
    staged = {k: str(env.get(k, "")).strip() for k in ENV_SECRET_KEYS}
    staged["X_TOKENS"] = tokens_json.strip()

    result: dict = {"set": [], "skipped": [], "failed": []}
    for name, value in staged.items():
        if not value:
            result["skipped"].append(name)
        elif set_secret(name, value):
            result["set"].append(name)
        else:
            result["failed"].append(name)
    return result
