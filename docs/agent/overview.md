--- 

# Overview

A personal, LLM-compiled knowledge base. Inputs are raw markdown snapshots under declared namespaces: X bookmarks and full-account post mirrors at launch, plus notes, clips, and long-form sources through the same raw contract. Outputs are markdown wiki articles with mechanical provenance — every synthesized claim cites a verbatim source.

## Philosophy: Karpathy-style, NO RAG

- The knowledge layer is plain markdown a human (or coding agent) can read and grep — a native **Open Knowledge Format (OKF) v0.1 bundle** (Google's vendor-neutral knowledge format). No embeddings, no vector store, no retrieval-augmented generation pipeline. Search is wiki navigation: `wiki/index.md` → topic indexes → markdown citation links → source notes.
- Compile uses an LLM, but **only as a writer** — never as a runtime retriever. At read time there is no LLM in the loop unless a separate skill chooses to load relevant files itself.
- See `README.md` for the user-facing tour, and `compile/INSTRUCTIONS.md` for the LLM contract.

## The ingestion pipelines

Launch ingestion is **forward-only, idempotent, and run unattended on GitHub Actions cron**. Ingest never does synthesis — it only deposits verbatim content into `raw/<namespace>/<bucket>/`.

1. **Bookmark pull** — `bin/pull.py` reads new bookmarks from allowlisted X folders (per `config/topics.toml`) and writes them into `raw/bookmarks/<topic>/`. Uses an OAuth2 user-context token that **rotates on every refresh**; the rotated value is persisted to the `X_TOKENS` repo secret in CI via `GH_PAT`. Local runs persist to a file (`bin/.x_tokens.json` by default).
2. **Account mirror** — `bin/dump_account.py` mirrors every post + reply (no retweets) by handles in `config/accounts.toml` into `raw/accounts/<handle>/`. Trailing 3-day window, deduped. Uses an app-only Bearer token (`X_BEARER_TOKEN`), no rotation.
3. **Other raw origins** — `src/kb/raw_sources.py` declares the non-X namespaces the compiler and linter understand. `books`, `notes`, and `clips` are auto-compile eligible topic buckets; `pdfs` are review-gated; `chats` are snapshot-only. Unknown `raw/*` directories are not processed by convention.

All pipelines write into `raw/` directories that are **sacred append-only ground truth** — never edited or deleted in-place. See [provenance](provenance.md).

## The compile step

`compile/INSTRUCTIONS.md` defines the LLM contract. The `.github/workflows/compile.yml` workflow runs `bin/compile.sh`, which invokes the agent CLI selected by `config/models.toml` or the `COMPILE_RUNNER` repo variable (codex | claude | gemini) headlessly with `compile/PROMPT.md`. The agent produces `wiki/<topic>/sources/<slug>.md` + updates `wiki/<topic>/concepts/<theme>.md`, regenerates `wiki/<topic>/index.md`, then `bin/lint.py` runs as the provenance guardrail. The compile commit only ships if lint passes — for any runner.

## The wiki-use skill

The downstream wiki-style agent instructions live in `skill/my-knowledge/SKILL.md`. That skill is the runtime consumer of the compiled knowledge base: it performs navigation-first retrieval from `wiki/index.md` to topic indexes, concept files, and their markdown citation links into sources. It reads actual files, cites curated claims with source attribution, and keeps generic model opinion separate from knowledge-base claims.

## Key identifiers

- **Project:** Bowerbird. Each user's fork is their instance; default branch `main` carries both code and the user's data commits.
- **Language:** Pipeline is Python 3.11+ (CI runs 3.13), stdlib-only runtime (`urllib`, `tomllib`); dev-only dep is `pytest`. Connector agents are external consumers of generated recap files and manifests under `recaps/`, starting with Slack. See `pyproject.toml`.
- **Knowledge format:** `wiki/` is a native **Open Knowledge Format (OKF) v0.1 bundle** — markdown + YAML frontmatter, a `type` on every note, a markdown-link graph. OKF is a conformance floor; Bowerbird's stricter provenance lint governs above it. See [provenance.md](provenance.md).
- **Enabled topics/accounts:** whatever the instance's `config/topics.toml` and `config/accounts.toml` declare — read the configs, don't assume.
- **CI secrets:** `X_TOKENS` (rotating user-context token), `X_BEARER_TOKEN` (app-only), `GH_PAT` (fine-grained PAT to write back to `X_TOKENS`), plus compile-runner credentials (see [github-actions](github-actions.md)).
- **Documentation index:** `llms.txt` at the repo root.

## Where to look first for common questions

| Question | File |
|----------|------|
| How does a bookmark become a wiki article? | [pipeline.md](pipeline.md) + `compile/INSTRUCTIONS.md` |
| What workflows run on what schedule? | [github-actions.md](github-actions.md) |
| How should an agent use the compiled wiki? | `skill/my-knowledge/SKILL.md` |
| What does the linter enforce? | [provenance.md](provenance.md) + `src/kb/linter.py` |
| How do I add a new topic? | `config/topics.toml` (one TOML table) — see [repo-layout.md](repo-layout.md) |
| How do I add a new account? | `bowerbird accounts add <handle> --topic <topic>` |
| How do I add a new source origin? | `src/kb/raw_sources.py` first, then writer/importer code |
| Why no `requirements.txt`? | Stdlib-only — see [conventions.md](conventions.md) |

---
