# Provenance

The architectural commitment of this knowledge base: **every claim is traceable to a verbatim source**. The compile step is allowed to synthesize, but is never allowed to assert anything that isn't grounded in a captured raw item. Mechanical lint enforces this so the unattended pipeline can't quietly drift.

## Open Knowledge Format (OKF) v0.1

`wiki/` is a native **OKF v0.1 bundle** (Google's vendor-neutral knowledge format): plain
markdown + YAML frontmatter, organized into a topic hierarchy, with a markdown-link graph
between notes. Three conformance rules: every non-reserved note carries a non-empty
`type`; `index.md` files are frontmatter-free (except the bundle-root `wiki/index.md`,
which declares `okf_version: "0.1"`); citations are relative markdown links. Any OKF
consumer can read the bundle with no export step.

OKF conformance is a **floor**, not a ceiling. OKF itself is deliberately permissive
("consumers MUST tolerate broken links / missing fields"); Bowerbird's provenance
invariant below is **stricter** and is what actually governs. `bin/lint.py` enforces both —
the OKF `type` floor *and* the strict citation rules. Never relax to OKF's soft level.

## The sacred directories

`raw/<namespace>/<bucket>/` is **append-only ground truth**. The path shape is storage;
the declared namespace registry defines semantics and compile eligibility. Current
auto-compile namespaces are `bookmarks`, `accounts`, `books`, `notes`, and `clips`.
Review-gated or snapshot-only namespaces may hold raw snapshots without being eligible
for unattended compile. Rules:

1. Files in `raw/` are written **once** by the ingest pipelines (`bin/pull.py`, `bin/dump_account.py`, `bin/ingest_book.py`) and never edited, renamed, or deleted afterwards.
2. The filename pattern `<YYYY-MM-DD>__<id>.md` is the dedup key — the pipelines check existence before writing.
3. Anything in `raw/` is the canonical statement of what an external author said. The wiki layer paraphrases / synthesizes; raw stays verbatim.

Violating these rules silently breaks idempotency and breaks the citation chain (source
notes link back to `raw_path`, with legacy notes falling back to `raw_id`).

## Two-layer wiki

Per `compile/INSTRUCTIONS.md`:

- **`wiki/sources/`** — one note per raw item. **Faithful capture only**: paraphrase what the author actually said. No editorializing here.
- **`wiki/concepts/`** — synthesized articles organized by theme (`type: Concept`). **Every claim must cite a source via a relative markdown link, `[label](../sources/<source-stem>.md)`.**

> INVIOLABLE: never write a substantive claim in a concept article that isn't traceable to a source note. Generic AI opinion is not allowed in `concepts/`.

Connective prose is permitted if it's obviously editorial (a one-sentence framing), but cannot carry the load of a knowledge claim.

## Provenance taxonomy

Every source note carries a `provenance:` frontmatter field indicating the origin of the raw material:

| Value | Meaning |
|-------|---------|
| `first-party` | Account-mirror source — the tracked account's own words (from `raw/accounts/<handle>/`). The note also carries `mirror: accounts/<handle>` as a logical back-pointer. |
| `external-expert` | Bookmarked third-party post the user saved into a topic folder (from `raw/bookmarks/<topic>/`). Default for bookmark sources. |
| `community` | Community or crowd-sourced material. Snapshot-only chat exports use this by default until promoted by an explicit compile contract. |

Account-mirror source notes land in the **same** `wiki/<topic>/sources/` tree as bookmark sources, distinguished by `provenance: first-party` and the `mirror:` back-pointer.

Book, note, and clip source notes also land in `wiki/<topic>/sources/`. Books use
`source_type: book-chapter`, carry `book`, `chapter` when present, and resolve
their legacy `raw_id` under `raw/books/<topic>/`. Notes use
`source_type: markdown-note`; clips use `source_type: web-clip`.

## Linter rules (`src/kb/linter.py`, invoked by `bin/lint.py`)

`lint(wiki_dir, repo_root=None)` returns a list of `Violation(path, kind, message)` objects. Core kinds plus `missing_type` from the companion `okf_conformance(wiki_dir)`:

| Kind | Trigger |
|------|---------|
| `missing_frontmatter` | A `sources/*.md` file is missing one or more required frontmatter keys. Required set is defined as `REQUIRED_SOURCE_FRONTMATTER` in the linter module. |
| `uncited_concept` | A `concepts/*.md` file contains zero source citations (neither a markdown link into `sources/` nor a legacy `[[wikilink]]`). |
| `broken_link` | A citation in a concept article — a markdown link into `sources/`, or a legacy `[[citation]]` — does not resolve to a file stem in the same topic's `sources/`. |
| `missing_raw` | A source note's `raw_path` does not resolve to a real file. Legacy notes without `raw_path` fall back to `raw_id` resolution in the expected bookmark/book/account raw root. Only checked when `repo_root` is passed to `lint()`. |
| `invalid_raw_path` | `raw_path` is not a safe repo-relative `raw/<namespace>/<bucket>/<file>.md` path. |
| `unknown_raw_namespace` | `raw_path` uses a namespace that is not declared in `src/kb/raw_sources.py`. |
| `raw_not_compile_eligible` | `raw_path` points at a review-gated or snapshot-only namespace that should not be compiled unattended. |
| `missing_type` | A non-reserved note (`sources/` or `concepts/`) lacks a non-empty `type` — the OKF conformance floor, from `okf_conformance()`. |

`bin/lint.py` walks every `wiki/<topic>/` and prints `[topic] kind: relpath :: message` for each violation. It also validates committed recap files/manifests under `recaps/`. It exits 1 if any were found, else prints `provenance and recaps OK` and exits 0.

The compile workflow runs `bin/lint.py` as the guardrail; a failing lint means the LLM's commits do not ship.

## Required source-note frontmatter

From `compile/INSTRUCTIONS.md` (the contract the compile step writes against):

```yaml
---
type: X Post                         # OKF required field; or X Thread / Article / Book Chapter / Markdown Note / Web Clip
author: <handle if known, else the author_id from raw>
url: <source_url from the raw frontmatter>
date: <date portion of created_at from raw>
raw_path: <repo-relative path under raw/>
raw_id: <id from the raw filename — links this note to its raw item>
source_type: x-post                  # or book-chapter / markdown-note / web-clip
origin: bookmarks                    # raw namespace
provenance: external-expert        # or first-party for account-mirror sources
topic: <topic>
mirror: accounts/<handle>          # account-mirror sources only; omit for bookmarks
book: <book id>                     # book-chapter sources only
chapter: <chapter number>           # book-chapter sources only, when present
section_title: <chapter title>      # book-chapter sources only
---
```

`raw_path` is the primary back-pointer: it lets the compile step skip already-processed
raw items and lets readers walk from a wiki claim → source note → verbatim raw. `raw_id`
is retained as the local dedup key and for legacy source notes.

## Citation syntax

Concept articles cite a source note with a relative markdown link into `sources/` (OKF-native):

```markdown
The "60k formula" reaches breakeven in week 4 [seraleev formula update](../sources/2026-01-10-seraleev-formula-60k-update.md).
```

The linter resolves the link's basename stem (`2026-01-10-seraleev-formula-60k-update`) against `wiki/<topic>/sources/` stems. Citations must point to a source in the **same topic** (cross-topic citation is currently not supported by the linter). Legacy Obsidian `[[stem]]` wikilinks are still accepted by the linter for resilience, but the OKF-native form is the markdown link.

## What an agent editing the wiki must check

Before committing a change to `wiki/`:

1. `python3 -m pytest` passes (linter has unit tests).
2. `python3 bin/lint.py` prints `provenance and recaps OK`.
3. Any new concept article carries `type: Concept` and cites at least one source note.
4. Any new source note has all required frontmatter (including a `type`) and a `raw_path` that resolves to an actual declared, compile-eligible raw file. Keep `raw_id` too, but do not use it as the only back-pointer for new notes.
