# How It Works

This repository turns selected source material into a cited markdown wiki — a native
**Open Knowledge Format (OKF) v0.1 bundle** (Google's vendor-neutral knowledge format:
plain markdown + YAML frontmatter, a `type` on every note, a markdown-link graph). It is
designed for personal knowledge work first, but the mechanics are general enough to open
source and reuse, and the OKF bundle is readable by any OKF-aware tool.

## Data Model

The repo has three important file layers:

| Layer | Path | Purpose |
| --- | --- | --- |
| Raw inputs | `raw/<namespace>/<bucket>/*.md` | Append-only source snapshots. Declared namespaces define semantics and compile eligibility. |
| Wiki | `wiki/<topic>/sources/*.md`, `wiki/<topic>/concepts/*.md` | LLM-compiled source notes and cited concept articles. |
| Recap feed | `compile/recap-feed.json` | Daily machine-readable input for recap delivery. |

Raw files are append-only ground truth. The compile step reads them, but normal
automation should not edit or delete them.

## Pipeline

```text
X bookmark folders      X account timelines      Markdown books / notes / clips
  |                        |                         |
  | bin/pull.py            | bin/dump_account.py      | declared importers
  v                        v                         v
raw/bookmarks/<topic>/  raw/accounts/<handle>/   raw/<namespace>/<bucket>/
  |                        |                         |
  +------------------------+-------------------------+
                 |
                 v
        .github/workflows/compile.yml
        bin/compile.sh runs the agent CLI selected by COMPILE_RUNNER
        (codex | claude | gemini) against compile/INSTRUCTIONS.md
                 |
                 v
        wiki/<topic>/sources/
        wiki/<topic>/concepts/
        wiki/<topic>/index.md
                 |
                 v
        python3 bin/lint.py
                 |
                 v
        .github/workflows/kb-recap-feed.yml
                 |
                 v
        compile/recap-feed.json
                 |
                 v
        one daily recap (slack-recap workflow, web app cron, or any feed consumer)
```

The repository uses Git history as part of the workflow. The daily recap feed is
based on source notes added to `wiki/*/sources/*.md` in the prior 24 hours, not
on the dates of the original X posts. That distinction matters when the compiler
catches up on old raw material.

## Ingestion

Bookmark ingestion is topic based. `config/topics.toml` maps a topic name to one
or more X bookmark folder IDs. `bin/pull.py` fetches bookmarks from those
folders, reconstructs threads when possible, captures long-form X article text
when present, and writes deterministic raw files:

```text
raw/bookmarks/<topic>/<YYYY-MM-DD>__<tweet-id>.md
```

Account ingestion is handle based. `config/accounts.toml` lists X handles and
the wiki topic each account should feed. `bin/dump_account.py` fetches each
account's posts and replies over a trailing window, excludes reposts, and writes:

```text
raw/accounts/<handle>/<YYYY-MM-DD>__<tweet-id>.md
```

Both importers are idempotent because the tweet ID is in the filename. Newer
non-X importers use the same storage shape: `raw/<namespace>/<bucket>/<date>__<id>.md`.
Namespaces such as `notes` and `clips` can compile automatically when their bucket is a
topic. Review-gated namespaces such as `pdfs` can store snapshots without being compiled
until their locator/provenance contract is strong enough.

## Compile

The compile step is intentionally separate from ingestion. It scans declared,
compile-eligible raw namespaces, skips any raw path that already appears in a
wiki source note, and writes:

- `wiki/<topic>/sources/<date>-<slug>.md`: faithful source notes.
- `wiki/<topic>/concepts/<theme>.md`: synthesized concept pages.
- `wiki/<topic>/index.md`: topic index.

The contract lives in `compile/INSTRUCTIONS.md`. The key rule is that every
substantive wiki claim must cite a source note — written as a relative markdown link
into `sources/`, which doubles as the OKF graph edge between concept and source.

`python3 bin/lint.py` enforces the provenance rules before wiki changes are
committed.

## Recap

The recap is not another importer and should not be a separate status stream.
It is a view over newly added wiki source notes. The feed generator
(`bin/recap_feed.py`) groups new sources into account lanes and topic
lanes and writes `compile/recap-feed.json`; the built-in Slack connector's
`slack-recap` workflow, the web app's daily cron, or any consumer of the feed
contract turns that into one daily message.

See [Daily Slack recap](slack-recap.md) for the feed format and delivery options.
