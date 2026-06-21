"""TopicRouter — decides which topic a bookmark belongs to.

Today: folder -> topic via TopicsConfig. The `classify` hook is the seam for a
future model that routes folder-less ("unsorted") bookmarks; until it exists,
unsorted bookmarks route to None and are simply not ingested.
"""
from __future__ import annotations

from collections.abc import Callable

from .config import TopicsConfig


class TopicRouter:
    def __init__(
        self,
        config: TopicsConfig,
        classifier: Callable[[str], str | None] | None = None,
    ) -> None:
        self._folder_to_topic = config.folder_to_topic()
        self._classifier = classifier

    def route(self, folder_id: str | None, *, text: str | None = None) -> str | None:
        """Return the topic for a bookmark, or None if it shouldn't be ingested."""
        if folder_id is not None:
            return self._folder_to_topic.get(folder_id)
        # Folder-less bookmark: only a classifier can place it. Seam, not built yet.
        if self._classifier is not None and text is not None:
            return self._classifier(text)
        return None
