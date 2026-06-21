"""kb — personal knowledge-base pipeline (raw inputs -> compiled wiki/).

Deep modules with simple, stable interfaces:
  config   TopicsConfig      topic -> X folder allowlist (the extensibility seam)
  books    BookIngest        Markdown books -> chapter-level raw files
  tokens   TokenStore        OAuth2 user-context access token (handles rotating refresh)
  threads  ThreadAssembler   reconstruct a self-thread from a conversation search
  raw_sources RawNamespace   declared raw namespace semantics and lifecycle
  raw_writer RawWriter       append-only, idempotent writes into raw namespaces
  routing  TopicRouter       bookmark -> topic (folder map now; classifier seam later)
  linter   ProvenanceLinter  enforce the citation invariant over wiki/
"""

__version__ = "0.1.0"
