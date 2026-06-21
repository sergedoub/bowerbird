#!/usr/bin/env python3
"""Real-world wiring for the init wizard (`bowerbird init`).

All logic lives in kb.wizard (offline-testable); this script provides the effectful
implementations: terminal I/O, the OAuth flow (delegated to bin/x_auth_spike.py in a
subprocess), the bookmark client, and GitHub secrets via the gh CLI.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.local import load_env_file, make_token_store, resolve_user_id  # noqa: E402
from kb.wizard import WizardDeps, WizardIO, run_wizard   # noqa: E402
from kb.x_client import XBookmarkClient                  # noqa: E402

ENV_PATH = os.path.join(HERE, ".env")
TOKENS_PATH = os.path.join(HERE, ".x_tokens.json")
CONFIG_DIR = os.path.join(ROOT, "config")


def read_env() -> dict:
    env: dict = {}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip("'\"")
    return env


def write_env(env: dict) -> None:
    body = "\n".join(f"{k}={v}" for k, v in env.items()) + "\n"
    fd = os.open(ENV_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(body)


def oauth_flow() -> bool:
    # Fresh process so x_auth_spike picks up the env file the wizard just wrote.
    proc = subprocess.run([sys.executable, os.path.join(HERE, "x_auth_spike.py"), "auth"])
    return proc.returncode == 0 and os.path.exists(TOKENS_PATH)


def load_tokens() -> str:
    if os.path.exists(TOKENS_PATH):
        return open(TOKENS_PATH).read()
    return ""


def make_folder_client() -> XBookmarkClient:
    for k, v in read_env().items():
        os.environ.setdefault(k, v)
    tokens = make_token_store(HERE)
    return XBookmarkClient(resolve_user_id(tokens), tokens)


def gh_available() -> bool:
    if not shutil.which("gh"):
        return False
    return subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0


def set_secret(name: str, value: str) -> bool:
    proc = subprocess.run(["gh", "secret", "set", name, "--body", value],
                          cwd=ROOT, capture_output=True)
    return proc.returncode == 0


def set_variable(name: str, value: str) -> bool:
    proc = subprocess.run(["gh", "variable", "set", name, "--body", value],
                          cwd=ROOT, capture_output=True)
    return proc.returncode == 0


def read_config(name: str) -> str:
    path = os.path.join(CONFIG_DIR, name)
    return open(path).read() if os.path.exists(path) else ""


def write_config(name: str, text: str) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(os.path.join(CONFIG_DIR, name), "w") as f:
        f.write(text)


def main() -> None:
    load_env_file(ENV_PATH)
    io = WizardIO(ask=input, say=print)
    deps = WizardDeps(
        oauth_flow=oauth_flow,
        load_tokens=load_tokens,
        make_folder_client=make_folder_client,
        gh_available=gh_available,
        set_secret=set_secret,
        set_variable=set_variable,
        read_env=read_env,
        write_env=write_env,
        read_config=read_config,
        write_config=write_config,
    )
    try:
        result = run_wizard(io, deps)
    except (EOFError, KeyboardInterrupt):
        print("\nSetup aborted — re-run `bowerbird init` anytime; it never overwrites "
              "existing config without asking.")
        sys.exit(1)
    sys.exit(1 if result.aborted else 0)


if __name__ == "__main__":
    main()
