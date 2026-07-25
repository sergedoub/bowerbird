# Contributing to Bowerbird

Thanks for helping improve Bowerbird. Small, focused changes with offline tests
are easiest to review.

## Before you start

- Search existing issues and pull requests before opening a new one.
- Use a public issue for bugs and feature proposals. Report vulnerabilities
  privately according to [SECURITY.md](SECURITY.md).
- Keep the public source repository separate from any private Bowerbird
  instance. Never submit personal raw material, compiled notes, destinations,
  account lists, or credentials.
- For a substantial change, open an issue first so the approach and scope can
  be agreed before implementation.

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Development setup

Bowerbird requires Python 3.11 or newer. Create a virtual environment and
install the development extra:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

Runtime code must remain Python-standard-library only. `pytest` is a development
dependency; do not introduce runtime packages such as `requests`, `httpx`,
`pydantic`, or provider SDKs.

## Make a focused change

Library code belongs in `src/bowerbird/`, command entry points in `bin/`, and
tests in `tests/`. Prefer focused modules, pure functions, and injected clients,
clocks, token stores, or filesystem roots.

Files below `raw/` are append-only pipeline data. Do not edit, delete, rename,
or commit generated `raw/`, `wiki/`, or `recaps/` content in a source-code pull
request. Preserve every provenance link and the required OKF `type` field when
working on compile behavior.

Network-backed commands require personal credentials and are not part of the
offline test suite. Tests must never call X, GitHub, Slack, or a model provider.
Use fakes and temporary directories instead.

## Validate the change

Run both required checks from the repository root:

```bash
python3 -m pytest
python3 bin/lint.py
```

Add or update deterministic tests for changes to routing, parsing, token
refresh, raw writing, repository boundaries, or linter behavior. If a check
cannot be run, explain why in the pull request.

The credential-dependent workflows in `.github/workflows/` are reusable
automation for private instances. They are gated from mutating the public source
repository and are not substitutes for the offline CI suite.

## Open a pull request

Use a short imperative commit message, such as `accounts: validate mirror
handle`. A pull request should include:

- a concise summary and reason for the change;
- tests and lint checks run;
- any affected pipeline, topic, account, workflow, or configuration behavior;
- confirmation that no secrets or personal instance data are included; and
- a linked issue when one exists.

Automated or AI-assisted contributions are welcome, but the submitter is
responsible for understanding, testing, and reviewing every change. Disclose
material automated assistance in the pull request and be prepared to revise the
change based on maintainer review.
