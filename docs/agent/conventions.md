# Conventions & gotchas

Hard constraints, gotchas, and do/don't rules for agents editing this repo.

## Hard constraints

### Stdlib-only at runtime

The runtime has **zero non-stdlib dependencies**. `pyproject.toml`:

```toml
[project]
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8"]
```

This is a deliberate choice — the pipelines must work in any Python 3.11+ environment with no `pip install`. HTTP uses `urllib.request`. TOML parsing uses `tomllib` (Python 3.11+). JSON uses `json`. **Do not introduce `requests`, `httpx`, `pydantic`, `tweepy`, or any other runtime dep.** If you need behavior they offer, write it against stdlib (see `src/kb/x_client.py` for an example).

`pytest` is dev-only and only needed for the test suite.

### Python 3.11+

`tomllib` is used unconditionally — code will not import on 3.10. CI runs 3.13 (see `actions/setup-python@v5` step in `compile.yml`).

### Sacred `raw/` directories

See [provenance](provenance.md). Never edit/delete/rename files under `raw/`.

### Path disjointness (fork upgrade contract)

Forks upgrade via `git merge upstream/main` (see `docs/upgrading.md`). That only stays conflict-free if upstream changes touch **code paths only** (`src/`, `bin/`, `tests/`, `compile/INSTRUCTIONS.md`, `compile/PROMPT.md`, `.github/`, `docs/`, `connectors/`, `skill/`) and instance automation writes **data paths only** (`raw/`, `wiki/`, `config/`, `compile/recap-feed.json`). Don't add workflow steps that write to code paths, and don't ship upstream commits that write to data paths. User-tunable workflow values belong in repository variables, not workflow edits (cron lines are the one documented exception).

### No RAG, no embeddings, no Postgres-backed content

See [overview](overview.md). Markdown files are the database; tokens live in a local file or the `X_TOKENS` repo secret. If you find yourself wanting a vector store, you are off-design.

### OKF-native wiki

`wiki/` is a native **Open Knowledge Format (OKF) v0.1 bundle**, so anything writing to the wiki layer keeps it conformant: every `sources/`/`concepts/` note carries a non-empty `type`; concept citations are relative markdown links into `sources/` (not Obsidian `[[stem]]`); `index.md` files are frontmatter-free except the bundle-root `wiki/index.md`, which declares `okf_version: "0.1"`. This is a floor *under* — never a replacement for — the strict provenance lint; `bin/lint.py` enforces both. The one-time conversion lives in `bin/migrate_okf.py`.

## Gotchas

### Rotating X tokens

The OAuth2 user-context refresh token **rotates on every refresh** (Twitter/X's choice, not ours). If `pull.py` refreshes successfully but crashes before `TokenStorage.save()` lands the new dict, the next run is locked out (refresh token already invalidated server-side). Mitigations:

- `TokenStore` is structured to call `save()` immediately after `_refresh()`. Do not reorder.
- In CI the persistence target is the `X_TOKENS` repo secret, written via `GH_PAT`. A failure here is recoverable by manually replacing the secret with a freshly-obtained token (see `bin/x_auth_spike.py`).
- The account-mirror pipeline (`dump_account.py`) does NOT have this gotcha — it uses an app-only Bearer that doesn't rotate.

### `workflow_run` only fires from the default branch

`compile.yml` chains off other workflows. The triggering match is against the **default branch** copy of the consumer workflow file. Edits to workflow chaining on a feature branch will not take effect until merged to `main`.

### `GITHUB_TOKEN` commits don't fire `push` events

By design — prevents recursive CI. That's why `compile.yml` chains via `workflow_run` instead of listening for pushes to `raw/`. (It also listens for direct `push` paths as a fallback for human/PAT pushes.)

### Adding a topic or account

- Topic: add `[topics.<name>]` block in `config/topics.toml` with X folder `folder_ids`. No other code changes.
- Account: prefer `bowerbird accounts add <handle> --topic <topic>`, then commit config and run a targeted `account-dump` dispatch.

### `bin/x_auth_spike.py` is not part of cron

It's an interactive helper to discover bookmark folder IDs. Don't wire it into a workflow.

## Style

- Snake_case for Python; modules grouped by responsibility under `src/kb/`.
- All I/O uses pure functions where possible (the linter is the cleanest example — `lint(wiki_dir) -> list[Violation]`).
- Tests are offline. Inject fakes for HTTP clients and the filesystem boundary; never hit the real X API from a test.

## Commit hygiene

- Workflows commit as `github-actions[bot]` (`41898282+github-actions[bot]@users.noreply.github.com`) — keep that identity when editing workflow commit steps.
- Agents committing on a user's behalf should use the user's GitHub noreply address, never a private email (GitHub blocks pushes exposing private emails).
- Don't `git push --force` to `main` — `main` carries the instance's daily data-commit history.

## What lives where (quick reference)

| If you're touching… | Look in… |
|---------------------|----------|
| Bookmark ingest | `bin/pull.py`, `src/kb/pull.py`, `src/kb/search.py`, `src/kb/threads.py` |
| Account-mirror ingest | `bin/dump_account.py`, `src/kb/account_dump.py`, `src/kb/timeline.py` |
| Token storage / refresh | `src/kb/tokens.py` |
| Wiki provenance rules | `src/kb/linter.py`, `bin/lint.py`, `compile/INSTRUCTIONS.md` |
| Topic / account routing | `src/kb/routing.py`, `src/kb/config.py`, `config/*.toml` |
| Cron / CI | `.github/workflows/*.yml` |
| Tests | `tests/test_*.py` |
