# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Bowerbird: a personal, LLM-compiled markdown knowledge base (Karpathy-style — **no RAG, no embeddings, no vector store**). The unit of curation is a raw markdown snapshot under a declared namespace, for example an X bookmark, a mirrored account post, an Obsidian note, a web clip, or a book chapter. X bookmarks and account mirrors are the launch ingestion paths; the rest of the pipeline is intentionally source-agnostic. Raw inputs become an attributable two-layer wiki, and a daily recap feed drives one Slack message. The system scales by adding configuration or a declared raw namespace, not by changing the wiki model.

The wiki is a native **Open Knowledge Format (OKF) v0.1 bundle** (Google's vendor-neutral knowledge format, published 2026-06-12 — markdown + YAML frontmatter, a `type` on every note, a markdown-link graph between notes). OKF is a *floor*: Bowerbird's stricter provenance lint (every claim cites a resolving source) sits on top and still governs. See `docs/agent/provenance.md`.

The current source of truth lives in `llms.txt` and the linked `docs/agent/*.md` files.

**New to this repo (fresh clone, nothing configured)?** Type `/setup` — the
repo ships a guided, in-session setup skill (`.claude/skills/setup/SKILL.md`)
covering credentials, the X app, OAuth, folder mapping, secrets, the first
pull, and the web app.

## Commands

```bash
# Pipeline tests (pytest config in pyproject.toml: testpaths=tests, pythonpath=src)
python3 -m pytest                          # full suite (fast, all offline with fakes)
python3 -m pytest tests/test_threads.py::test_name -q   # one test

# Web app tests/build (from web/)
cd web && npm test && npm run typecheck && npm run build

# The bowerbird CLI (installed by `pip install -e .`) wraps every bin/ script:
bowerbird init                             # interactive setup wizard
bowerbird auth                             # OAuth flow -> saves bin/.x_tokens.json
bowerbird folders                          # list bookmark folders (names + ids)
bowerbird pull [--topic t] [--no-threads]  # bookmarks -> raw/bookmarks/<topic>/
bowerbird backfill --topic t --no-threads  # historical bookmarks, cost-controlled
bowerbird dump-account [--handle h] [--days 3 | --full] [--max-posts n]
bowerbird models                           # compile + recap provider/model
bowerbird lint                             # provenance guardrail: must print "provenance OK"

# Recap feed (what kb-recap-feed.yml runs)
python3 bin/recap_feed.py [--window-hours 24]

# Compile locally with any runner
COMPILE_RUNNER=codex bash bin/compile.sh && python3 bin/lint.py
```

The pipeline has **no build step and no third-party runtime dependency** — the `kb` package is stdlib-only (`urllib`, `tomllib`, `json`). Only the dev extra (`pytest`) is external. Keep it that way unless there's a strong reason; new deps break the "runs anywhere, including bare CI" property. The web app (`web/`) is a separate Next.js/TypeScript deployable with its own dependencies.

## Architecture: declared raw inputs -> compile -> use

```
X bookmarks          ──pull────────> raw/bookmarks/<topic>/ ─┐
configured X accts   ──dump_account> raw/accounts/<handle>/ ─┤
Markdown/Obsidian    ──future/local> raw/notes/<topic>/ ─────┤
web clips            ──future/local> raw/clips/<topic>/ ─────┤─compile─> wiki/<topic>/ ──use──> my-knowledge skill
books                ──ingest_book─> raw/books/<topic>/ ─────┘  (LLM)    (sources/ + concepts/)        (navigation)
```

The directory shape is `raw/<namespace>/<bucket>/<YYYY-MM-DD>__<id>.md`. The namespace registry in `src/kb/raw_sources.py` is the contract that says what a namespace means, whether its bucket is a topic, account, or mapped bucket, and whether it is eligible for unattended compile. Unknown `raw/*` namespaces are not auto-compiled by guessing. All raw roots are append-only ground truth.

At launch, two X ingestion pipelines feed the **same** wiki tree. Compile distinguishes origins by source-note frontmatter: `origin`, `source_type`, `provenance`, `raw_path`, and when needed `mirror: accounts/<handle>`. The same contract is used for books, notes, and clips.

### Stage 1a — Pull bookmarks (deterministic Python, `src/kb/`)
`bin/pull.py` wires injected clients into `kb.pull.run_pull`. The flow: `config/topics.toml` allowlist → `XBookmarkClient` enumerates folder tweet ids and hydrates them via `GET /2/tweets` → thread heads get reconstructed by `SearchClient` + `threads.assemble` → `RawWriter` persists one markdown file per item under `raw/bookmarks/<topic>/`.

Two design properties to preserve:
- **`raw/` is sacred ground truth**: append-only, never mutated or deleted. `RawWriter` filenames are deterministic (`<YYYY-MM-DD>__<tweet-id>.md`), so re-running is a no-op for already-seen items (`write()` returns `None`). This is what makes the pull **idempotent and forward-only by construction** — there is no cursor/state to track; "have we seen this?" is just file existence.
- **Dependency injection everywhere**: HTTP clients, token posters, the conversation fetch, and `time`/`sleep` are all injected. This is why the whole pull is unit-testable offline with fakes (see `tests/`). When adding logic, follow this pattern — push I/O to the edges, keep the core a pure function over injected collaborators.

### Stage 1b — Account mirror (`bin/dump_account.py` → `kb.account_dump.run_dump`)
A sibling pipeline for following accounts (not your bookmarks). `config/accounts.toml` lists `[[handles]]` entries — each binds an X username to a wiki `topic` and an `off_topic` policy (only `"skip"` is implemented; `"quarantine"` is reserved). `TimelineClient` walks `GET /2/users/:id/tweets` (retweets excluded, replies kept) and `RawWriter` writes into `raw/accounts/<handle>/`. Auth here is the **app-only Bearer only** — no user-context token, no refresh rotation. Each run is scoped to a trailing window (`--days`, default 3), so a missed daily run self-heals on the next overlap; `--full` overrides to grab the API's full ~3,200-post ceiling.

### Stage 1c — Other raw origins (`src/kb/raw_sources.py`)
`raw_sources.RAW_NAMESPACES` declares the non-X origins the compiler and linter understand:
`books`, `notes`, and `clips` are auto-compile eligible topic buckets; `pdfs` are review-gated until page locators are reliable; `chats` are snapshot-only until a future channel/topic map exists. A new source origin should first become a declared namespace with tests, then a writer that produces the same deterministic raw file shape and frontmatter. Do not rely on "anything under raw/" being processed.

### Stage 2 — Compile (LLM, governed by `compile/INSTRUCTIONS.md`)
The compile step is **generative** (an LLM writes the wiki), so it can't be unit-tested. Instead it's bounded by two things:
- `compile/INSTRUCTIONS.md` — the exact contract the LLM follows. Read it before changing anything about compile behavior.
- `bin/lint.py` (`kb.linter`) — the **executable form of the citation invariant**, run as a guardrail. It enforces: every `sources/*.md` has required frontmatter (`author`, `url`, `date`); every `concepts/*.md` cites ≥1 source via a relative markdown link into `sources/` (legacy `[[source]]` still accepted); every citation link resolves to an existing source note; every `raw_path` resolves to a real file under a declared, compile-eligible raw namespace; legacy source notes without `raw_path` still resolve `raw_id` under the original bookmark/account/book roots; and — via the companion `kb.linter.okf_conformance` — every note carries a non-empty `type` (the OKF floor).

The wiki has **two layers, and one inviolable rule**:
- `wiki/sources/` — one faithful note per raw item (what the author actually said, attributed). No editorializing.
- `wiki/concepts/` — synthesized cross-source articles (`type: Concept`). **Every claim must cite the source note it came from** via a relative markdown link into `sources/`, e.g. `[label](../sources/<stem>.md)` (OKF-native; legacy `[[wikilink]]` still tolerated by the lint). Never inject generic advice into the knowledge layer.

A raw item is "already compiled" iff some source note's `raw_path` frontmatter equals the repo-relative raw path. Legacy notes without `raw_path` fall back to `raw_id`. The compile only touches `wiki/*/` — never `raw/`.

### Stage 3 — Use (`skill/my-knowledge/SKILL.md`)
A global, topic-aware skill (installed at `~/.claude`, mirrored here) does **navigation-first retrieval**: root `index.md` → topic `wiki/index.md` → `concepts/` → markdown citation links into `sources/`. It reads actual files (never answers from memory), cites every curated claim inline with author+url, and keeps the model's own generic opinions clearly separated from curated claims.

## The extensibility seams

**Adding a raw origin:** add or update a `RawNamespace` in `src/kb/raw_sources.py`, with tests that prove compile eligibility and lint behavior. Pick the bucket meaning deliberately: topic buckets compile directly into `wiki/<topic>/`, account buckets need config mapping, and mapped buckets need an explicit router before compile. Unknown namespaces and undeclared bucket semantics must fail closed.

**Adding a topic (bookmark side):** add a `[topics.<name>]` table with X folder ids in `config/topics.toml`. Nothing else. `kb.config.TopicsConfig` validates that every topic has ≥1 folder and that no folder feeds two topics (which would make routing ambiguous). Folder ids come from `GET /2/users/:id/bookmarks/folders` (use `bin/x_auth_spike.py`). `kb.routing.TopicRouter` has a `classifier` hook for routing folder-less "unsorted" bookmarks, but it's a seam, not built — unsorted bookmarks currently route to `None` and aren't ingested by the topic pipeline.

**Adding an account to mirror:** add a `[[handles]]` entry to `config/accounts.toml` with `handle`, `topic` (where the compile should file distilled source notes — does not need a corresponding bookmarks folder), and `off_topic` policy. `kb.config.AccountsConfig` parses it; `compile/INSTRUCTIONS.md` reads the topic binding when deciding which `wiki/sources/` directory to write into and stamps `provenance: first-party` + `mirror: accounts/<handle>` on the resulting note.

## Auth model (verified by the spike — easy to get wrong)

Two **different** credentials are required:
- **Bookmarks/folders** use OAuth2 **user-context** tokens (`kb.tokens.TokenStore`).
- **Search** (for thread reconstruction) **rejects user-context with 403** and requires an **app-only Bearer** (`X_BEARER_TOKEN`). `SearchClient` tries full-archive (`/2/tweets/search/all`) first and permanently falls back to recent search (`/2/tweets/search/recent`, 7-day window) for the rest of the run if the plan rejects full-archive with 403; `summary["search_mode"]` reports which tier ran.

The user-context **refresh token rotates (single-use)**: every refresh returns a new one that *must* be persisted immediately, or the next run is locked out. `TokenStore._refresh` does this. Refresh tokens also expire after ~6 months of inactivity, which is the main "silent death" failure mode — the web app's Health page surfaces it, and signing in with X on the web app re-seeds the `X_TOKENS` secret to recover.

Token storage is `bin/.x_tokens.json` (`FileTokenStorage`, 0600). In CI the `X_TOKENS` secret is materialized to that file before the run and the rotated value is written back to the secret afterward (see `pull.yml`). Secrets live in `bin/.env` locally (gitignored) and GitHub Actions secrets in CI.

## Automation (`.github/workflows/`)

- `pull.yml` (`pull-bookmarks`) — daily cron. Materializes `X_TOKENS` secret → file, runs `pull.py`, then **writes the rotated token back** to the secret via a fine-grained PAT (`GH_PAT`), and commits new `raw/` files with the default `GITHUB_TOKEN`.
- `account-dump.yml` — daily cron. Runs `dump_account.py` on a trailing window for every handle in `config/accounts.toml` and commits new `raw/accounts/<handle>/` files. Bearer-only, no token rotation.
- `compile.yml` (`compile-wiki`) — runs `bin/compile.sh`, which installs and headlessly invokes the agent CLI selected by the `COMPILE_RUNNER` repo variable (codex | claude | gemini, default codex/OpenAI) against `compile/PROMPT.md` → `compile/INSTRUCTIONS.md`, gates on `bin/lint.py`, then commits `wiki/` changes. It's **chained from both `pull-bookmarks` and `account-dump` via `workflow_run`** (not push/dispatch) because commits made with `GITHUB_TOKEN` don't fire push/dispatch events.
- `kb-recap-feed.yml` — daily cron. Runs `bin/recap_feed.py` (`kb.recap_feed`, unit-tested): writes `compile/recap-feed.json` from `wiki/*/sources/` notes added in the last 24 hours, grouped into account lanes (`mirror: accounts/<handle>`) and topic lanes. Concept/index changes are intentionally not counted.
- `ci.yml` — pytest + lint on code-path changes (includes the sample-data fixtures under `samples/`).

GitHub Actions never post Slack updates. The daily recap is delivered by the web app's `/api/cron/recap` (or any other consumer of `compile/recap-feed.json` — the feed is the stable contract; see `docs/slack-recap.md`).

## Web app (`web/`)

Next.js/TypeScript, self-hosted by each user (their Vercel/Railway, their env vars). One deploy = one user = this repo. `web/src/lib/repoClient.ts` is the ONLY module that talks to GitHub; `configModel` mirrors `kb.config` validation; sign-in-with-X (owner-gated) seals the captured token into the `X_TOKENS` secret; `/api/cron/recap` delivers the daily recap through the `DeliveryAdapter` seam (Slack webhook at launch). Tests: `cd web && npm test` (vitest, mocked HTTP, offline).

## Not yet implemented (stubs that raise `NotImplementedError`)

`kb.indexer.IndexGenerator` (mechanical index generation — index is currently written by the compile LLM), `kb.articles.ArticleExtractor` (fetch linked essays to markdown; X-native Article bodies *are* already captured in pull via `article.plain_text`), and `kb.health.HealthCheck` (staleness/lint observability — the web app's Health page covers the operational need; the stub remains for a CLI equivalent). Each has a deliberately small interface and a docstring explaining the intended design — read it before implementing.

## Data-loss guardrails specific to this repo

- **Never modify or delete anything under `raw/*/`.** Raw files are irreplaceable ground truth; the entire system's provenance depends on them being verbatim and append-only.
- Don't hand-edit `wiki/` to add claims without a source citation (a relative markdown link into `sources/`) — `bin/lint.py` will (correctly) fail.
- Don't commit `bin/.env`, `*.x_tokens.json`, or any token material (gitignored, but verify before staging).
