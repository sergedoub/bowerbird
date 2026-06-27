---
name: my-knowledge
description: Retrieve and apply the user's personal curated knowledge base (X-bookmark-derived, topic-namespaced markdown wiki). Use whenever the user says "use my knowledge" or "use my <topic> knowledge" — e.g. "use my marketing knowledge" — or otherwise asks to draw on their saved / curated / bookmarked knowledge for a task. Navigation-first retrieval (wiki index → concepts → sources); always cite sources and keep generic AI opinions separate from curated claims.
---

# my-knowledge

Retrieve and apply the user's personal, curated knowledge base. It's a Karpathy-style
markdown wiki (no embeddings, no RAG) — you navigate files, you don't query a vector
store. The wiki is a native Open Knowledge Format (OKF) v0.1 bundle: every note carries a
`type`, and concept→source citations are relative markdown links.

**Location:** `KNOWLEDGE_BASE_PATH` (see Setup below)
**Layout (topic-namespaced):** `wiki/<topic>/` containing:
- `index.md` — entry point for the topic (concept + source map)
- `concepts/` — synthesized articles (`type: Concept`); every claim cites a source via a relative markdown link, e.g. `[label](../sources/<stem>.md)`
- `sources/` — faithful notes per bookmarked thread/article, with `type` / `author` / `url` / `date` frontmatter (what an expert actually said)

The bundle-root `wiki/index.md` lists all available topics.

## Setup

`KNOWLEDGE_BASE_PATH` refers to the user's knowledge-base repo checkout. Resolve it in
this order:

1. If this skill file lives inside a knowledge-base checkout (`skill/my-knowledge/` next
   to a `wiki/` directory), the repo root is two directories up — use that.
2. Otherwise use the literal path on the line below (the install step writes it):
   - knowledge base checkout: `~/knowledge-base`
3. If neither resolves to a directory containing `wiki/`, tell the user the knowledge
   base isn't present on this machine and where you looked.

## When to use

Trigger phrases: **"use my knowledge"**, **"use my <topic> knowledge"** (for any topic
the user curates), or any request to draw on the user's saved / curated / bookmarked
knowledge for the task at hand.

## Retrieval protocol (navigation-first)

1. **Resolve the topic.** Normalize the requested topic to a directory name: lowercase,
   spaces → hyphens (e.g. "iOS dev" → `ios-dev`). Confirm it exists by listing
   `<KNOWLEDGE_BASE_PATH>/wiki`.
   - If no topic was given, or it doesn't match a directory, read `wiki/index.md`
     (or list `wiki/`) and **ask which topic** — don't guess.
2. **Read the topic index:** `wiki/<topic>/index.md` for the concept + source map.
3. **Follow the map:** open the relevant `concepts/*.md`, then follow their markdown
   citation links (e.g. `[label](../sources/<stem>.md)`) into `sources/*.md` for the
   underlying claims. **Read the actual files — never answer from memory or training data.**
4. Use **Grep/ripgrep only to *locate*** notes when the index isn't enough; navigation is the
   default, not search.

## Applying knowledge — the provenance invariant

- **Cite every curated claim inline** with author + url from the source note, e.g.
  `(@author, https://x.com/i/web/status/…)`.
- **Keep your own generic / AI opinions clearly separated and labeled as yours** — never blend
  them into curated claims. The entire value of this KB is that it's specific, attributable,
  human-curated knowledge, not generic advice.
- If the KB has **nothing relevant**, say so plainly and suggest the user bookmark/file more
  into that topic's X folder. **Do not fabricate curated knowledge.**

## Compounding (optional)

If the task produces a validated **first-party** result worth keeping (e.g. "this angle
actually worked, here's the number"), offer to file it back into `sources/` as a first-party
note (`provenance: first-party`) so the KB compounds over time. Deliverables themselves live
outside the wiki.
