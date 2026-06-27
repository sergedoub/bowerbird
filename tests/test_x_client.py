"""XBookmarkClient paging behavior."""
from bowerbird.x_client import XBookmarkClient


class FakeXBookmarkClient(XBookmarkClient):
    def __init__(self, pages):
        super().__init__("user-1", object())
        self.pages = pages
        self.calls = []

    def _get(self, path, params=None):
        self.calls.append((path, params))
        token = (params or {}).get("pagination_token")
        return self.pages[token]


class StreamingFakeXBookmarkClient(FakeXBookmarkClient):
    def __init__(self, pages):
        super().__init__(pages)
        self.hydrated = []

    def _hydrate(self, ids):
        self.hydrated.append(tuple(ids))
        return (
            {
                tid: {
                    "id": tid,
                    "author_id": "a",
                    "conversation_id": tid,
                    "created_at": "2026-05-01T00:00:00.000Z",
                    "text": f"text {tid}",
                }
                for tid in ids
            },
            {},
        )


def test_folder_tweet_id_limit_stops_before_next_page():
    client = FakeXBookmarkClient({
        None: {
            "data": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}],
            "meta": {"next_token": "page-2"},
        },
        "page-2": {"data": [{"id": "5"}]},
    })

    ids = client._folder_tweet_ids("folder-1", limit=3)

    assert ids == ["1", "2", "3"]
    assert client.calls == [("users/user-1/bookmarks/folders/folder-1", None)]


def test_folder_tweet_ids_paginate_without_limit():
    client = FakeXBookmarkClient({
        None: {"data": [{"id": "1"}], "meta": {"next_token": "page-2"}},
        "page-2": {"data": [{"id": "2"}]},
    })

    ids = client._folder_tweet_ids("folder-1")

    assert ids == ["1", "2"]
    assert client.calls == [
        ("users/user-1/bookmarks/folders/folder-1", None),
        ("users/user-1/bookmarks/folders/folder-1", {"pagination_token": "page-2"}),
    ]


def test_bookmark_count_walks_ids_without_hydrating():
    client = FakeXBookmarkClient({
        None: {"data": [{"id": "1"}], "meta": {"next_token": "page-2"}},
        "page-2": {"data": [{"id": "2"}, {"id": "3"}]},
    })

    assert client.bookmark_count_in_folder("folder-1") == 3
    assert client.calls == [
        ("users/user-1/bookmarks/folders/folder-1", None),
        ("users/user-1/bookmarks/folders/folder-1", {"pagination_token": "page-2"}),
    ]


def test_bookmarks_in_folder_streams_pages_so_consumers_can_stop_early():
    client = StreamingFakeXBookmarkClient({
        None: {"data": [{"id": "1"}, {"id": "2"}], "meta": {"next_token": "page-2"}},
        "page-2": {"data": [{"id": "3"}]},
    })

    bookmarks = client.bookmarks_in_folder("folder-1", "marketing")
    first = next(bookmarks)
    bookmarks.close()

    assert first.tweet.id == "1"
    assert client.hydrated == [("1", "2")]
    assert client.calls == [("users/user-1/bookmarks/folders/folder-1", None)]
