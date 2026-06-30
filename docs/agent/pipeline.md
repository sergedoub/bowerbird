# Pipeline

End-to-end flow from raw inputs to cited wiki concepts. Declared raw namespaces, one shared compile + lint guardrail.

## Module map (`src/bowerbird/`)

| Module | Purpose |
|--------|---------|
| `config.py` | TOML loaders. `TopicsConfig.load(path)` returns `Topic[]` with `folder_ids`. `AccountsConfig.load(path)` returns `Account[]` (each with `handle`, `topic`). Raises `ConfigError` on malformed input. |
| `models.py` | Dataclasses for raw items, threads, accounts. |
| `raw_sources.py` | Declared raw namespace registry: bucket semantics, compile lifecycle, default source type/provenance. |
| `tokens.py` | `TokenStore` wraps a `TokenStorage` (Protocol: `load()`, `save(dict)`). `FileTokenStorage` for local; `TokenStore.get_access_token()` handles expiry + `_refresh()`. The refreshed dict is persisted via `storage.save()` — this is what propagates the rotated refresh token. |
| `x_client.py` | Low-level X API HTTP (stdlib `urllib`). |
| `search.py`, `threads.py` | Bookmark fetch and thread reassembly. X-native article bodies are captured by the pull path when the API returns `article.plain_text`. |
| `timeline.py` | Account timeline fetch (app-only Bearer; no rotation). |
| `books.py` | Splits configured Markdown books into chapter-level raw files. |
| `raw_writer.py` | Writes raw markdown files with deterministic names. Idempotent — re-running can't duplicate. |
| `pull.py` | Library entry point for the bookmark pipeline; orchestrates client → threads → writer. |
| `account_dump.py` | Library entry point for the account-mirror pipeline. |
| `routing.py` | Maps folder ID → topic (for the pull pipeline). |
| `recaps.py` | Builds file-first recap artifacts and manifests from selected wiki source notes. Pure over injected reads and synthesis. |
| `recap_llm.py` | Hosted model call edge for recap body generation. Stdlib-only `urllib`; tests inject deterministic synthesis. |
| `cli.py` | The `bowerbird` console entry point — thin verb router over the bin/ scripts (runpy). |
| `wizard.py` | The `bowerbird init` setup wizard; all effects injected via `WizardDeps` (offline-testable). |
| `folders.py` | Bookmark-folder listing/formatting for the CLI and wizard. |
| `local.py` | Shared local-run wiring for bin scripts: `.env` loading, token store, user-id resolution. |
| `linter.py` | `lint(wiki_dir, repo_root=None)` returns `Violation[]`. When `repo_root` is provided, also checks that each source note's `raw_path` resolves to a declared, compile-eligible raw file; legacy notes without `raw_path` fall back to `raw_id` resolution. Companion `okf_conformance(wiki_dir)` adds the OKF `type`-presence floor. See [provenance](provenance.md). |
| `health.py` | Text-first doctor checks for config, recap file validity, and lint status. |

## Entry points (`bin/`)

All `bin/*.py` are stdlib-only CLI scripts. Run them with `python3 bin/<name>.py`, or via the installed `bowerbird` CLI (`bowerbird <verb>` — see `src/bowerbird/cli.py` for the verb map).

| Script | What it does |
|--------|--------------|
| `pull.py` | Daily bookmark pull. Reads `config/topics.toml`, fetches new bookmarks from allowlisted folders, reassembles threads, captures linked articles, writes to `raw/bookmarks/<topic>/`. Persists the rotated token via the active `TokenStorage`. |
| `dump_account.py` | Daily account mirror. Reads `config/accounts.toml`, fetches the trailing window (default 3 days) of each handle's posts + replies, writes to `raw/accounts/<handle>/`. App-only Bearer. |
| `ingest_book.py` | Manual book ingest. Reads `config/books.toml`, splits one Markdown book by chapter/appendix, writes to `raw/books/<topic>/`. |
| `dump_all.py` | Archive helper for dumping all bookmark folders plus unsorted bookmarks outside the compile pipeline. |
| `backfill.py` | One-off backfill — pulls historical bookmarks past the daily window. |
| `lint.py` | Walks every `wiki/<topic>/` and runs `bowerbird.linter.lint(wiki, repo_root=ROOT)` plus `bowerbird.linter.okf_conformance(wiki)` (the OKF `type` floor), then validates committed recap files/manifests. Exits 0 (prints `provenance and recaps OK`) or 1. |
| `recap.py` | Runs `bowerbird recap`: reads `config/recaps.toml`, scans git-added `wiki/*/sources/*.md` notes for due calendar windows, writes `recaps/<profile>/<date>.md` and `recaps/manifests/<run-date>.json`. |
| `slack_recap.py` | Runs `bowerbird slack-recap`: reads the latest recap manifest, opens manifest-listed recap files, and posts Slack delivery targets with `SLACK_BOT_TOKEN` as the dedicated Bowerbird bot. |
| `doctor.py` | Checks config, recap file validity, and provenance lint status. Supports `--json` for agents. |
| `folders.py` | Lists the authenticated user's bookmark folders (names + ids). |
| `init_wizard.py` | Real-world wiring for the `bowerbird init` wizard (terminal I/O, OAuth subprocess, gh CLI secrets). |
| `compile.sh` | The pluggable compile runner seam — installs and invokes the agent CLI selected by `COMPILE_RUNNER`. See `docs/compile-runners.md`. |
| `x_auth_spike.py` | The OAuth flow + raw API helpers (`bowerbird auth`). |

## End-to-end flow

```
[ X bookmarks      ]     [ X account timeline ]     [ Markdown books ]     [ Notes / clips ]
   │ bin/pull.py            │ bin/dump_account.py       │ bin/ingest_book.py
   │ (rotating token)       │ (app-only Bearer)          │ (manual local)
   ▼                        ▼                           ▼
raw/bookmarks/<topic>/*.md raw/accounts/<handle>/*.md raw/books/<topic>/*.md raw/{notes,clips}/<topic>/*.md
        │                         │                         │
        └──────────┬──────────────┴──────────────┬──────────┘
                   │ workflow_run chain
                   │ (either pull-bookmarks OR account-dump triggers compile)
                   ▼
          .github/workflows/compile.yml
          └─► bin/compile.sh (agent CLI selected by COMPILE_RUNNER:
              codex | claude | gemini)
              reads compile/PROMPT.md -> compile/INSTRUCTIONS.md
              scans all raw roots:
                declared auto-compile raw namespaces
              writes wiki/sources/*.md
              updates wiki/concepts/*.md
              regenerates wiki/index.md
              │
              ▼
          bin/lint.py guardrail
              │ exit 0 → commit ships
              │ exit 1 → fail the run
              ▼
          .github/workflows/recap.yml
          (daily or after compile: bin/recap.py groups new wiki
           source notes into configured account and topic lanes)
              │
              ▼
          recaps/<profile>/<date>.md
          recaps/manifests/<run-date>.json
              │
              ▼
          delivery adapters
          (bin/slack_recap.py for Slack, email, or another connector)
```

## Filename invariants

- **Raw bookmark file:** `raw/bookmarks/<topic>/<YYYY-MM-DD>__<tweet-id>.md`. The id after `__` is the dedup key.
- **Raw account post file:** `raw/accounts/<handle>/<YYYY-MM-DD>__<tweet-id>.md`. Same shape.
- **Raw book chapter file:** `raw/books/<topic>/<YYYY-MM-DD>__<book-id>-chNN.md`. Appendix sections use `<book-id>-appendix`.
- **Raw file:** `raw/<namespace>/<bucket>/<YYYY-MM-DD>__<id>.md`. Namespace rules live in `src/bowerbird/raw_sources.py`; bucket is usually the topic, except namespaces such as `accounts` where the bucket is resolved through config.
- **Wiki source note:** `wiki/<topic>/sources/<YYYY-MM-DD>-<short-slug>.md`. Frontmatter `raw_path` points to the raw file and `raw_id` keeps the local dedup key. Account-mirror source notes additionally carry `provenance: first-party` and a `mirror: accounts/<handle>` back-pointer.
- **Wiki concept article:** `wiki/<topic>/concepts/<theme-slug>.md`. Carries `type: Concept`; cites sources via relative markdown links, `[label](../sources/<source-stem>.md)`.
- **Recap file:** `recaps/<profile>/<YYYY-MM-DD>.md`. Carries `type: Recap` frontmatter with profile, window, selected lanes, source note paths, totals, prompt, model/provider, timestamp, and delivery targets.
- **Recap manifest:** `recaps/manifests/<run-date>.json`. Runtime-agnostic delivery handoff listing generated recap files and non-secret targets.

These are not just conventions — the linter and the compile step depend on them. Don't rename files mechanically; the `raw_path` / `raw_id` glue is what makes the system idempotent.

## Accounts config (`config/accounts.toml`)

Each tracked account is a `[[handles]]` table:

```toml
[[handles]]
handle    = "account_one"
topic     = "ai-updates"   # distilled source notes land in wiki/ai-updates/sources/
```

`topic` is required. The named topic does not need a corresponding bookmarks
folder in `topics.toml` — accounts feed the wiki layer directly. Account
mirrors are complete: every uncompiled raw account item should become a
faithful source note in the configured topic. Higher-level concepts and recaps
decide what to cite after the complete source-note layer exists.

Use `bowerbird accounts add <handle> --topic <topic>` for normal account
adds. For a targeted first import, dispatch
`gh workflow run account-dump.yml -f handle=<handle> -f days=3`; the workflow
commits new `raw/accounts/<handle>/` files and chains `compile-wiki`.

## Books config (`config/books.toml`)

Each configured book is a `[[books]]` table:

```toml
[[books]]
book_id = "never-split-the-difference"
topic = "negotiation"
title = "Never Split the Difference: Negotiating as if Your Life Depended on It"
author = "Chris Voss"
published_date = "2016-05-16"
source_path = "/path/to/book.md"
provenance = "external-expert"
```

Run `python3 bin/ingest_book.py --book <book_id>` to split the Markdown source into
chapter-level raw files. This is manual by design: local book files are private inputs,
while the compile contract treats the resulting raw chapter files like any other
source with strict provenance.

## Idempotency

Every step is restartable:
- `raw_writer` checks file existence by deterministic name before writing.
- `compile` scans declared auto-compile raw namespaces, then skips any path already referenced as `raw_path` in a `wiki/sources/*.md`.
- `ingest_book` writes deterministic chapter ids, so re-running the same book skips existing raw chapter files.
- `lint` is a pure function over the filesystem state.

A failed cron run can be re-dispatched (`workflow_dispatch`) with no risk of duplicates.
