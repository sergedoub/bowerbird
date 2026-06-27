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
| Recaps | `recaps/<profile>/<date>.md`, `recaps/manifests/*.json` | Durable recap files plus runtime-agnostic delivery handoff. |

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
        .github/workflows/recap.yml
                 |
                 v
        recaps/<profile>/<date>.md
        recaps/manifests/<run-date>.json
                 |
                 v
        delivery adapters (Slack, email, or another consumer)
```

The repository uses Git history as part of the workflow. Recap generation is
based on source notes added to `wiki/*/sources/*.md` in each profile's calendar
window, not on the dates of the original X posts. That distinction matters when
the compiler catches up on old raw material.

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
non-X importers use the same storage shape:
`raw/<namespace>/<bucket>/<date>__<id>.md`. Namespaces such as `notes` and
`clips` can compile automatically when their bucket is a topic. Review-gated
namespaces such as `pdfs` can store snapshots without being compiled until
their locator/provenance contract is strong enough.

## Adding New Source Types

Do not put new providers under arbitrary `raw/<provider>/` paths and hope the
compiler figures them out. A source should either fit an existing declared
namespace or come with a code/docs change that declares a new namespace.

Use an existing namespace when the semantics already fit:

- First-party writing, Obsidian notes, or local markdown: `raw/notes/<topic>/`.
- Web/API material that is already a stable article, post, comment, or page:
  `raw/clips/<topic>/`.
- Long-form books split into chapters: `raw/books/<topic>/`.

For example, a LinkedIn article can usually be imported as a web clip:

```text
raw/clips/<topic>/<YYYY-MM-DD>__linkedin-<article-id>.md
```

with raw frontmatter like:

```markdown
---
author: "Jane Doe"
created_at: "2026-06-27T00:00:00Z"
provenance: external-expert
source_type: web-clip
source_url: "https://www.linkedin.com/pulse/..."
topic: "<topic>"
---

Verbatim or lightly normalized markdown body of the article.
```

A selected Reddit post or comment can also be a clip when the user has chosen
the topic and the raw file carries a stable permalink, author, date, and body.
If the goal is unattended ingestion of a subreddit, user, comment tree, or other
provider-specific stream, first decide the routing contract: is the bucket a
topic, an account, a subreddit, or something that needs a map? If that routing
is not explicit, store snapshots only and do not auto-compile them.

Add a new namespace only when the provider needs distinct behavior. That means
declaring it in `src/bowerbird/raw_sources.py` with:

- bucket semantics (`topic`, `account`, or mapped)
- compile state (`auto`, review-gated, or snapshot-only)
- default source type and provenance
- locator requirements, if citations need page, section, comment, or message IDs

Then update the compile contract, tests, and docs before wiring an importer.
The importer should still write append-only markdown raw files; it should not
bypass `raw/` or write directly to `wiki/`.

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
It is a generated file view over newly added wiki source notes. `bowerbird recap`
reads `config/recaps.toml`, loads prompts from `compile/recaps/`, groups new
sources into selected account and topic lanes, and writes Markdown under
`recaps/<profile>/<date>.md`.

Each generated recap has `type: Recap` frontmatter with provenance: profile,
frequency, calendar window, selected lanes, source note paths, totals, prompt
path, model/provider, generated timestamp, and delivery targets. The human body
is a compact digest: one title, one high-signal line per lane, and one footer
with counts and keywords. It does not carry citations; the provenance lives in frontmatter. A matching
`recaps/manifests/<run-date>.json` file lists generated files and non-secret
delivery targets for Slack, email, or any other adapter.

See [Daily Slack recap](slack-recap.md) for the file-first delivery contract.
