# Repository Guidelines

## Project Structure & Module Organization

This is a Python 3.11+ knowledge-base pipeline. Library code lives in `src/kb/`, with CLI entry points in `bin/`. Tests live in `tests/` and mirror the module names, for example `tests/test_pull.py` for `src/kb/pull.py`. Runtime configuration is TOML under `config/`: topics are in `config/topics.toml`, account mirrors in `config/accounts.toml`.

Content inputs are Markdown files under declared raw namespaces shaped as `raw/<namespace>/<bucket>/<YYYY-MM-DD>__<id>.md`, for example `raw/bookmarks/<topic>/`, `raw/accounts/<handle>/`, `raw/notes/<topic>/`, and `raw/clips/<topic>/`; treat all `raw/*/` files as append-only pipeline data. Compiled wiki output lives under `wiki/<topic>/`, which is a native **Open Knowledge Format (OKF) v0.1 bundle** (markdown + YAML frontmatter, a `type` on every note, markdown-link citations). Agent-facing design notes are in `docs/agent/`, and the compile contract is in `compile/INSTRUCTIONS.md`.

## Build, Test, and Development Commands

- `python3 -m pip install -e '.[dev]'`: install the package in editable mode with pytest.
- `python3 -m pytest`: run the offline test suite configured by `pyproject.toml`.
- `python3 bin/lint.py`: run the provenance linter across generated wiki content.
- `python3 bin/pull.py --topic marketing`: pull new bookmarks for one configured topic.
- `python3 bin/dump_account.py --handle bcherny --days 3`: mirror a configured account over a trailing window.

Networked commands require local secrets in `bin/.env` or CI secrets. Do not commit local token files.

## Coding Style & Naming Conventions

Keep runtime code stdlib-only; `pytest` is dev-only. Do not add runtime dependencies such as `requests`, `httpx`, or `pydantic`. Use snake_case for modules, functions, and variables. Keep modules focused by responsibility under `src/kb/`. Prefer pure functions with injected clients or filesystem boundaries where practical, especially for code that needs tests.

## Testing Guidelines

Use pytest. Tests must be offline and deterministic: inject fake HTTP clients, token stores, clocks, or filesystem roots instead of calling the real X API. Name tests `test_<module>.py` and test functions `test_<behavior>()`. Add or update tests when changing routing, parsing, token refresh, raw writing, or linter behavior.

## Commit & Pull Request Guidelines

Recent commits use short imperative or scoped messages, for example `compile: update wiki from new raw` and `Add trq212 to account mirror`. Keep commits focused. For PRs, include a brief summary, tests run, affected pipeline or topic/account config, and any linked issue. Include screenshots only for HTML or visual output changes.

## Security & Agent-Specific Instructions

Never edit, delete, or rename files under `raw/*/` unless explicitly instructed. Preserve provenance links in wiki output — concept citations are relative markdown links into `sources/`, and every note carries a `type` (the OKF floor) — and run `python3 bin/lint.py` before shipping compile changes. Keep secrets out of git, especially `bin/.env` and token JSON files.

When asked to create an HTML file, open it in the local browser after finishing so the user can inspect the rendered result immediately.
