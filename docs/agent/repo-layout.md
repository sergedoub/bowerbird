# Repository layout

## Top-level

| Path | Role |
|------|------|
| `README.md` | Public human-facing overview with quick start links. |
| `AGENTS.md` | Codex-facing repository instructions. Keep at the repo root so Codex discovers it automatically. |
| `CLAUDE.md` | Claude Code-facing repository instructions. Keep at the repo root so Claude discovers it automatically. |
| `pyproject.toml` | Build + pytest config. `name=bowerbird`, `requires-python=">=3.11"`, runtime `dependencies=[]`, dev `pytest>=8`. Source root is `src/`. |
| `bin/` | CLI entry points (stdlib-only Python scripts). See [pipeline](pipeline.md). |
| `src/bowerbird/` | Library code — pipelines, clients, linter, models. See [pipeline](pipeline.md). |
| `tests/` | Offline pytest suite (no network). |
| `config/` | TOML configuration. Extensibility seam for topics, accounts, books, models, and recap profiles. The source repo keeps empty templates here; an installed fork writes its chosen config here. |
| `compile/` | `INSTRUCTIONS.md` (the LLM compile contract), `PROMPT.md` (the shared runner prompt), and `compile/recaps/` prompt files. No generated recap output lives here. |
| `recaps/` | Generated recap Markdown and delivery manifests. Commit these files in an installed fork; delivery adapters consume them. The source repo does not ship generated recaps. |
| `skill/` | The Bowerbird retrieval skill for downstream coding agents. |
| `connectors/` | Connector setup playbooks and service manifests, starting with Slack. Runtime code stays in `bin/` and `src/bowerbird/` with the rest of the pipeline. |
| `raw/<namespace>/<bucket>/` | Sacred append-only raw inputs. Namespace semantics and compile eligibility are declared in `src/bowerbird/raw_sources.py`. Generated raw files belong in an installed fork or separate data repo. |
| `wiki/index.md` | Bundle-root index of the OKF v0.1 bundle; declares `okf_version: "0.1"`. |
| `wiki/<topic>/` | Compiled topic wiki: sources, concepts, and index. A topic subtree of the OKF bundle rooted at `wiki/`; generated wiki files belong in an installed fork or separate data repo. |
| `.github/workflows/` | Five workflows (four pipeline + ci) — see [github-actions](github-actions.md). |
| `docs/*.md` | Public human-facing docs: setup, architecture, X imports, compile runners, recap, upgrading. |
| `docs/agent/` | This agent-facing documentation set (you are here). |
| `llms.txt` | Index for the agent-facing docs. |

## Raw and wiki layout

```
raw/
├── bookmarks/
│   └── marketing/
│       └── <YYYY-MM-DD>__<id>.md     # verbatim bookmarked content
├── accounts/
│   └── account_one/
│       └── <YYYY-MM-DD>__<id>.md     # verbatim account mirror content
├── books/
│   └── negotiation/
│       └── <YYYY-MM-DD>__<book-id>-chNN.md  # verbatim book chapter content
├── notes/
│   └── marketing/
│       └── <YYYY-MM-DD>__<id>.md     # first-party Markdown or Obsidian-style notes
├── clips/
│   └── marketing/
│       └── <YYYY-MM-DD>__<id>.md     # web-clipped Markdown
├── pdfs/                             # review-gated until locators are reliable
└── chats/                            # snapshot-only until a topic/channel map exists

wiki/                                 # OKF v0.1 bundle root
├── index.md                          # bundle-root index — declares okf_version: "0.1"
└── marketing/
    ├── index.md                      # topic index — frontmatter-free (OKF reserved file)
    ├── sources/
    │   └── <YYYY-MM-DD>-<slug>.md    # one per raw item; `type` + raw_path frontmatter
    └── concepts/
        └── <theme-slug>.md           # `type: Concept`; cites sources via markdown links
```

- **`raw/`** is **append-only**. Never edit or delete files here; the compile step depends on `raw_path` stability for idempotency.
- **Declared namespaces only:** `src/bowerbird/raw_sources.py` declares the namespaces the compiler and linter understand. `bookmarks`, `accounts`, `books`, `notes`, and `clips` are auto-compile eligible. `pdfs` are review-gated. `chats` are snapshot-only. Unknown `raw/*` paths must fail closed instead of being compiled by convention.
- **`wiki/`** is owned by the compile step and is a native **OKF v0.1 bundle**: every note carries a `type`, citations are relative markdown links, and `index.md` files are frontmatter-free except the bundle-root `wiki/index.md` (which declares `okf_version`). Manual edits are fine but must keep `bin/lint.py` green.
- Account-mirror source notes land in `wiki/<topic>/sources/` alongside bookmark sources, distinguished by `provenance: first-party` and a logical `mirror: accounts/<handle>` back-pointer.
- Book-chapter source notes also land in `wiki/<topic>/sources/`, with `source_type: book-chapter` so the linter resolves their `raw_id` under `raw/books/<topic>/`.
- Notes and clips use their bucket as the destination topic and carry `source_type: markdown-note` or `source_type: web-clip`.

## Configuration files (`config/`)

All TOML so they parse with the stdlib `tomllib`.

### `config/topics.toml`

```toml
[topics.marketing]
folder_ids = ["2057603076853547356"]
# [topics.ios-dev]
# folder_ids = ["..."]
```

**Adding a topic:** add one `[topics.<name>]` table with the X bookmark `folder_ids` it should ingest from. No other code changes required — the pipeline auto-routes. Discover folder IDs with `bowerbird folders` or interactively via `bowerbird init`.

### `config/accounts.toml`

```toml
[[handles]]
handle = "account_one"
topic  = "ai-updates"
```

Each account is a `[[handles]]` table:

| Field | Required | Description |
|-------|----------|-------------|
| `handle` | yes | X username without the leading `@`. |
| `topic` | yes | Topic into which distilled source notes are filed (`wiki/<topic>/sources/`). The topic does not need a corresponding bookmarks folder in `topics.toml`. |
| `label` | no | Display name used by recap profiles. Defaults to a prettified handle. |

**Adding an account:** prefer `bowerbird accounts add <handle> --topic <topic>`
instead of hand-editing TOML. Then dispatch
`gh workflow run account-dump.yml -f handle=<handle> -f days=3` for the
first trailing-window import. The next `compile-wiki` run distills the posts
into the configured topic's wiki.

### `config/recaps.toml`

```toml
[[recaps]]
name = "ai-accounts-daily"
frequency = "daily"
accounts = ["account_one"]
prompt = "compile/recaps/default.md"
format = "slack_mrkdwn"

[[recaps.deliveries]]
type = "slack"
destination = "#bowerbird-recaps"
```

Presence of a profile means enabled. A profile selects account and/or topic
lanes from compiled `wiki/*/sources/*.md` notes, chooses `daily` or `weekly`
calendar windows, points at a prompt under `compile/recaps/`, and lists
non-secret delivery targets. `bowerbird recap` writes generated files under
`recaps/<profile>/` plus `recaps/manifests/`.

### `config/books.toml`

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

**Adding a book:** add a `[[books]]` table, then run `python3 bin/ingest_book.py --book <book_id>` to split the Markdown source into `raw/books/<topic>/` chapter files. Book ingest is manual/local; compile distills those chapter files into the normal `wiki/<topic>/sources/` and `wiki/<topic>/concepts/` layers.

## Tests (`tests/`)

Run with `python3 -m pytest`. Pytest config is in `pyproject.toml`: `testpaths=["tests"]`, `pythonpath=["src"]`. Tests are offline — they inject fakes for HTTP and filesystem where needed. Layout matches src/ modules (e.g. `test_pull.py`, `test_account_dump.py`, `test_linter.py`, `test_tokens.py`, `test_raw_writer.py`, `test_threads.py`, `test_config.py`).
