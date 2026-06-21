---
type: Concept
---

# How a provenance-first knowledge base works

The system described across these sources has four load-bearing properties.

**Curation is the entry gate.** Knowledge enters by being deliberately saved — the
bookmark is the unit of curation, and anything not worth saving isn't knowledge yet
[2026-06-01-bowerbird-file-first-curation](../sources/2026-06-01-bowerbird-file-first-curation.md).

**Raw inputs are append-only ground truth.** Importers write verbatim copies with
deterministic filenames; nothing is ever edited or deleted, and re-runs are no-ops for
anything already on disk [2026-06-03-bowerbird-append-only-raw](../sources/2026-06-03-bowerbird-append-only-raw.md).

**The wiki has two layers that never mix.** Faithful, attributed source notes on one
side; synthesized concept articles on the other, where every claim cites the source
note it came from. A linter enforces the split mechanically — claims cite sources,
links resolve, sources carry author/url/date [2026-06-02-bowerbird-two-layer-wiki](../sources/2026-06-02-bowerbird-two-layer-wiki.md).

**Consumption is push, not pull.** A daily recap summarizes what was added in the last
day, computed from the wiki's git history rather than post dates so backlog compiles
don't masquerade as news [2026-06-05-bowerbird-daily-recap](../sources/2026-06-05-bowerbird-daily-recap.md).
