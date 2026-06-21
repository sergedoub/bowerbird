"""IndexGenerator — build wiki/index.md mechanically (NOT via the LLM).

STUB. Per the PRD the index is generated deterministically by scanning source/concept
frontmatter + headings, so the navigation entry point is reliable and not a hallucination
surface. Implementation lands once the wiki note conventions are frozen by the first
hand-tuned compile.
"""
from __future__ import annotations

from pathlib import Path


class IndexGenerator:
    def generate(self, topic_dir: str | Path) -> str:
        raise NotImplementedError("IndexGenerator.generate — implemented in a follow-up PR")
