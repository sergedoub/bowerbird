---
name: bowerbird
description: >-
  Retrieve and apply the user's Bowerbird knowledge base: a personal, curated,
  cited markdown wiki. Use explicitly when the user says "$bowerbird", "use
  Bowerbird", "use my knowledge", "use my <topic> knowledge", or asks "what do
  my saved sources say?". Also use implicitly for strategy, writing, planning,
  product, research, taste, or decision work where the user's curated wiki may
  contain relevant prior sources. Do not use for simple factual questions,
  repo-local code questions, or tasks where the user clearly wants only
  generic/current information. Navigation-first retrieval (wiki/index.md →
  topic index → concepts → sources); cite every curated claim and keep generic
  model judgment separate.
---

# Bowerbird

Bowerbird retrieves and applies the user's personal, curated knowledge base. It is a
Karpathy-style markdown wiki (no embeddings, no RAG): you navigate files, you do not
query a vector store. The wiki is a native Open Knowledge Format (OKF) v0.1 bundle:
every note carries a `type`, and concept→source citations are relative markdown links.

**Location:** `KNOWLEDGE_BASE_PATH` (see Setup below)
**Layout (topic-namespaced):** `wiki/<topic>/` containing:
- `index.md` — entry point for the topic (concept + source map)
- `concepts/` — synthesized articles (`type: Concept`); every claim cites a source via a relative markdown link, e.g. `[label](../sources/<stem>.md)`
- `sources/` — faithful notes per bookmarked thread/article, with `type` / `author` / `url` / `date` frontmatter (what an expert actually said)

The bundle-root `wiki/index.md` lists all available topics.

## Setup

`KNOWLEDGE_BASE_PATH` refers to the user's Bowerbird repo checkout. Resolve it in
this order:

1. If this skill file lives inside a Bowerbird checkout (`skill/bowerbird/` next
   to a `wiki/` directory), the repo root is two directories up — use that.
2. Otherwise use the literal path on the line below (the install step writes it):
   - Bowerbird checkout: `~/bowerbird`
3. If neither resolves to a directory containing `wiki/`, tell the user the knowledge
   base is not present on this machine and where you looked.

## When to use

Use Bowerbird when the task could benefit from the user's curated, cited wiki, even if
the user does not name the skill directly.

**Explicit triggers**

- `$bowerbird`
- "use Bowerbird"
- "use my knowledge"
- "use my <topic> knowledge" (for any topic the user curates)
- "what do my saved sources say?"
- Any request to draw on the user's saved, curated, bookmarked, or filed knowledge

**Implicit triggers**

Use Bowerbird for strategy, writing, planning, product, research, taste, or decision
tasks when the user's compiled wiki may contain relevant prior sources.

**Do not use Bowerbird**

- For simple factual questions that do not need the user's curated context.
- For repo-local code questions where the repository itself is the relevant source.
- For tasks where the user clearly wants only generic, public, current, or web-sourced
  information.

## Retrieval protocol (navigation-first)

1. **Resolve the checkout.** Find `KNOWLEDGE_BASE_PATH`, then read
   `<KNOWLEDGE_BASE_PATH>/wiki/index.md` before selecting topic files.
2. **Resolve the topic.** If the user names a topic, normalize it to a directory name:
   lowercase, spaces → hyphens (e.g. "iOS dev" → `ios-dev`). Confirm it exists under
   `<KNOWLEDGE_BASE_PATH>/wiki/<topic>/`.
   - If the normalized topic exists, use it.
   - If the named topic does not match a directory, read `wiki/index.md` and infer the
     nearest available topic if there is one clear match.
   - If no topic was named, infer likely topics from `wiki/index.md`; ask the user only
     when multiple plausible topics remain.
   - If no relevant topic exists, say that plainly and stop using curated knowledge.
3. **Read the topic index:** `wiki/<topic>/index.md` for the concept + source map.
4. **Follow the map:** open the relevant `concepts/*.md`, then follow their markdown
   citation links (e.g. `[label](../sources/<stem>.md)`) into `sources/*.md` for the
   underlying claims. **Read the actual files — never answer from memory or training data.**
5. Use **Grep/ripgrep only to *locate*** notes when the index is not enough; navigation is
   the default, not search.

## Applying knowledge — the provenance invariant

- **Cite every curated claim inline** with source author + URL from the source note, e.g.
  `(@author, https://x.com/i/web/status/…)`.
- **Keep your own generic model judgment clearly separated and labeled as yours** —
  never blend it into curated claims. The entire value of this knowledge base is that it is
  specific, attributable, human-curated knowledge, not generic advice.
- If the knowledge base has **nothing relevant**, say so plainly. If useful, suggest the kind of
  source the user could bookmark or file into that topic. **Do not fabricate curated
  knowledge.**

## Compounding (optional)

If the task produces a validated **first-party** result worth keeping (e.g. "this angle
actually worked, here's the number"), offer to file it back into `sources/` as a first-party
note (`provenance: first-party`) so Bowerbird compounds over time. Deliverables themselves
live outside the wiki.
