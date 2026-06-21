"""ArticleExtractor — fetch a linked URL and return clean markdown.

STUB. Many bookmarks link out to essays; that long-form content is the real knowledge
(the tweet is just a pointer). This extracts the article into raw/ alongside the tweet.

Interface kept deliberately small so the implementation (readability + HTML->markdown,
likely a small dependency) can land later without touching callers. Will be fixture-tested
(sample HTML -> expected markdown).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkdownDoc:
    title: str
    markdown: str
    url: str


class ArticleExtractor:
    def extract(self, url: str) -> MarkdownDoc:
        raise NotImplementedError("ArticleExtractor.extract — implemented in a follow-up PR")
