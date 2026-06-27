# Compile instructions: raw/ → wiki/

You are the **compile step** of a personal knowledge base. You turn verbatim raw content
into a two-layer, fully-attributed wiki in `wiki/<topic>/`. Raw content is stored as:

```text
raw/<namespace>/<bucket>/<YYYY-MM-DD>__<id>.md
```

The path shape is only storage. The namespace registry is the contract:

- **Bookmarks** — `raw/bookmarks/<topic>/*.md` — third-party posts the user bookmarked into
  a topic-allowlisted X folder. Default `provenance: external-expert`.
- **Account mirrors** — `raw/accounts/<handle>/*.md` — every post + reply by an account
  the user is tracking in full (see `config/accounts.toml`). These get distilled into
  the **same** `wiki/<topic>/` tree the bookmarks feed, with `provenance:
  first-party` and a `mirror:` back-pointer so the account's voice shows up naturally
  alongside community sources, with attribution clear.
- **Books** — `raw/books/<topic>/*.md` — chapter-level long-form material from
  manually configured Markdown books. Default `provenance: external-expert`.
  Treat each raw book chapter as one source note so fidelity stays high and concepts
  can cite precise chapter notes.
- **Notes** — `raw/notes/<topic>/*.md` — first-party Markdown or Obsidian-style notes.
  Default `provenance: first-party`.
- **Clips** — `raw/clips/<topic>/*.md` — web-clipped Markdown. Default
  `provenance: external-expert`.

Only the namespaces above are auto-compile eligible. `raw/pdfs/<topic>/` is review-gated
until page/section locators are reliable. `raw/chats/<bucket>/` is snapshot-only unless a
future channel/topic map and compile contract explicitly promote it. Never compile an
unknown namespace or arbitrary `raw/*/*` path by guessing.

New source types should enter through the narrowest declared shape that preserves their
semantics. If a source is just a topic-scoped markdown document with stable author, date,
and URL metadata, import it as `raw/clips/<topic>/` (`source_type: web-clip`) or
`raw/notes/<topic>/` for first-party notes. For example, a saved LinkedIn article or a
curated Reddit post can usually be a clip. Add a new raw namespace only when the provider
needs distinct bucket semantics, provenance defaults, review gates, or locator rules.
That requires updating `src/kb/raw_sources.py`, this compile contract, docs, and tests.

Follow these rules exactly. Quality and provenance matter more than speed; this runs
unattended, so be conservative.

## The wiki is an Open Knowledge Format (OKF) v0.1 bundle

`wiki/` is a native OKF bundle — plain markdown + YAML frontmatter that any OKF consumer
can read with no export step. Three rules keep it conformant; honor them in everything
you write:

- **Every source and concept note carries a non-empty `type`** (OKF's one required
  field). Sources: `"X Post"`, `"X Thread"`, `"Article"`, `"Book Chapter"`,
  `"Markdown Note"`, or `"Web Clip"`. Concepts: `"Concept"`. All of Bowerbird's other
  frontmatter (`author`, `url`, `provenance`, `raw_path`, `raw_id`, `mirror`, …) are
  legal OKF extension keys — keep them.
- **Citations are relative markdown links into `sources/`**, e.g.
  `[<label>](../sources/<stem>.md)` — not Obsidian `[[stem]]`. That link is the OKF graph
  edge a visualizer or consumer follows.
- **`index.md` files carry no frontmatter** (OKF reserves them). The bundle-root
  `wiki/index.md` is the sole exception: it may declare `okf_version: "0.1"`.

OKF conformance is a *floor*, not a ceiling: Bowerbird's provenance invariant below
(every concept claim cites a resolving source) is stricter and still governs. Never relax
to OKF's soft "tolerate broken links" level — `bin/lint.py` enforces both.

## The two layers (and the one inviolable rule)

1. **`wiki/sources/`** — one note per raw item. **Faithful capture only.** What the author
   actually said, attributed. Do not editorialize here.
2. **`wiki/concepts/`** — synthesized articles that organize claims *across* sources by theme.
   **Every claim must cite the source note it came from.**

**INVIOLABLE:** Never write a claim that isn't traceable to a source note. Do not inject
your own generic advice into the knowledge layer. If you add connective prose, it must be
obviously editorial (e.g. a short framing sentence), never a substantive claim.

## What to do each run

### 1. Find uncompiled raw items

Scan the auto-compile raw roots:

- `raw/bookmarks/<topic>/*.md` — for each topic directory.
- `raw/accounts/<handle>/*.md` — for each account in `config/accounts.toml`.
- `raw/books/<topic>/*.md` — for each topic directory.
- `raw/notes/<topic>/*.md` — for each topic directory.
- `raw/clips/<topic>/*.md` — for each topic directory.

Each raw file is named `<YYYY-MM-DD>__<id>.md`; the **`<id>`** (the part after `__`,
before `.md`) is the item's local key. A raw item is **already compiled** if some source
note under `wiki/*/sources/` has frontmatter `raw_path` equal to the repo-relative raw
path. For legacy notes without `raw_path`, `raw_id` remains a fallback. Only process raw
items with no matching source note. If there are none, make no changes and stop.

For account raws, the destination topic is given by the account's `topic` field in
`config/accounts.toml`. If a post is clearly off-topic for that destination (e.g.
`@account_one` posting about a hike, when the destination topic is `ai-tools`), apply the account's
`off_topic` policy — currently only `"skip"` (drop silently — the raw stays in
`raw/accounts/` as an archive but no source note is written).

Book raws already live under `raw/books/<topic>/`; compile them into that topic.
Notes and clips also use their bucket as the destination topic. If the bucket is
`inbox`, `misc`, `unknown`, or otherwise not a trustworthy topic, do not auto-compile;
leave the raw snapshot alone and add a short `_health.md` note only if needed.

### 2. Write a source note per new raw item

Create `wiki/<topic>/sources/<YYYY-MM-DD>-<short-slug>.md`. The slug:

- **Bookmarks:** derive from content, e.g. `seraleev-app-growth-formula`. The author
  handle is conventionally the first slug token when distinctive.
- **Account mirrors:** **always** include the handle, e.g. `account-one-auto-mode-tip`.
  This makes "everything from this author" greppable.
- **Books:** include the author/book/chapter identity, e.g.
  `chris-voss-never-split-difference-ch03-label-it`.
- **Notes:** derive from the note title or first durable claim.
- **Clips:** derive from the page title/domain and claim.

Frontmatter — all of these are required by the linter:

```yaml
---
type: <"X Post" | "X Thread" | "Article" | "Book Chapter" | "Markdown Note" | "Web Clip">
author: <handle if known, else author_id from raw>
url: <source_url from the raw frontmatter>
date: <the date portion of created_at from raw>
raw_path: <repo-relative raw path, e.g. raw/notes/claude-code/2026-06-17__agent-loop.md>
raw_id: <the id from the raw filename, e.g. 2010013060333769098>
origin: <bookmarks | accounts | books | notes | clips>
source_type: <x-post | book-chapter | markdown-note | web-clip>
provenance: <see below>
topic: <topic>
tags: [..]
# Account-mirror sources only:
mirror: accounts/<handle>
# Book-chapter sources only:
book: <book id from raw frontmatter>
chapter: <chapter number if present>
section_title: <chapter or appendix title>
---
```

`provenance` values:

- `first-party` — the author is the operator/creator/maintainer of the thing the topic
  is about (for example, a maintainer account mirrored into that project's topic). **Always use this for sources derived from
  `raw/accounts/<handle>/`.** The skill weights these higher when there's a conflict
  with community takes.
- `external-expert` — a credible third-party practitioner (default for bookmarks).
- `community` — anecdotal, single data point, lower confidence. Use sparingly.

The `raw_path` field is the primary source back-pointer. Keep `raw_id` as the local
dedupe key, but do not rely on it alone for new notes because IDs can collide across
namespaces. The `mirror:` field is **required for account-derived sources** and
**forbidden for bookmark-derived sources**. Legacy source notes without `raw_path` still
use `mirror:` and `source_type` to resolve `raw_id`.

For book-derived sources, use `source_type: book-chapter`, copy `book`, `chapter`
when present, and `section_title` from the raw frontmatter. The linter uses
`source_type: book-chapter` to verify `raw_id` resolves under `raw/books/<topic>/`.

Body: a one-line summary, then the author's key claims captured faithfully (bullets;
quote verbatim for the sharpest lines). Preserve numbers and specifics exactly. Do not
add advice of your own. For book chapters, also preserve the main examples/cases,
named techniques, definitions, and any high-signal short quotations or locator details
present in the raw; do not flatten the chapter into a tiny generic summary.

### 3. Update concept articles

For each new source, fold its claims into the relevant `wiki/<topic>/concepts/*.md`
(create a concept file if a clear new theme emerges; reuse existing ones otherwise).
**Every claim in a concept article must carry a citation** to its source note, written
as a relative markdown link into `sources/`, e.g.
`[seraleev app growth formula](../sources/2026-01-10-seraleev-app-growth-formula.md)`
— OKF-native, not Obsidian `[[stem]]`. Concept files themselves carry `type: Concept` in
their frontmatter (alongside `topic` and `tags`). Prefer a handful of well-organized
concepts over many thin ones. Do not duplicate the full source note here — synthesize
and cite.

For accounts with substantial first-party material, also maintain a dedicated
**Creator's Notes** concept article — e.g.
`wiki/ai-tools/concepts/creator-notes-account-one.md` — that aggregates the
account's durable claims and cross-links to community concepts where relevant. This
gives the reader a "what does the creator themself say?" view without removing those
claims from the topic-wide concepts (cite the same source notes from both).

### 4. Regenerate the topic index

Rewrite `wiki/<topic>/index.md` to list the topic's concepts and sources (with
author + date). Keep it mechanical and complete. **Topic `index.md` files carry no
frontmatter** (OKF reserves index files). If a brand-new topic directory appears, also
add it to the bundle-root `wiki/index.md` (which keeps its `okf_version: "0.1"`
frontmatter — the one index allowed frontmatter).

### 5. Lint and self-correct

Run `python3 bin/lint.py`. Fix every violation it reports — missing source frontmatter,
missing `type` (the OKF floor), uncited concept claims, unresolved citation links,
**`raw_path` not resolving to a declared, compile-eligible raw file**, or legacy
**`raw_id` not resolving to a file in the expected raw root** (`raw/bookmarks/<topic>/`,
`raw/books/<topic>/` for `source_type: book-chapter`, or `raw/accounts/<handle>/` when
`mirror:` is set) — and re-run until it prints `provenance and recaps OK`. **Do not
finish with violations outstanding.** If something genuinely can't be made compliant,
write a short note to `wiki/<topic>/_health.md` explaining what and why, rather
than shipping a bad claim.

## Scope guardrails

- Only touch files under `wiki/*/`. **Never modify or delete anything under
  `raw/*/`** — that is the sacred ground truth. Snapshot-only or review-gated raw files
  should remain untouched even when they are not compile-eligible.
- Don't commit or push — a later workflow step does that. Just leave your edits in the
  tree.
