"""Folder listing: aligned table over an injected client, empty-state message."""
from kb.folders import (
    estimate_owned_read_cost,
    estimate_post_read_cost,
    format_folders,
    run_folders,
    with_counts,
)


class FakeBookmarkClient:
    def __init__(self, folders):
        self._folders = folders
        self.counts = {}

    def folders(self):
        return self._folders

    def bookmark_count_in_folder(self, folder_id):
        return self.counts[folder_id]


def test_formats_aligned_name_id_table():
    out = format_folders([
        {"id": "111", "name": "marketing"},
        {"id": "222", "name": "ai"},
    ])
    lines = out.splitlines()
    assert lines[0].startswith("FOLDER")
    assert "marketing  111" in lines[1]
    assert lines[2].startswith("ai")
    assert lines[2].endswith("222")


def test_empty_listing_explains_itself():
    assert "no bookmark folders found" in format_folders([])


def test_run_folders_prints_and_returns_folders():
    folders = [{"id": "111", "name": "marketing"}]
    printed = []
    result = run_folders(FakeBookmarkClient(folders), out=printed.append)
    assert result == folders
    assert "111" in printed[0]


def test_counted_folder_table_includes_estimates():
    out = format_folders(
        [{"id": "111", "name": "marketing", "count": 12}],
        include_counts=True,
    )

    assert "ITEMS" in out
    assert "12" in out
    assert "$0.012" in out
    assert "$0.060" in out


def test_with_counts_walks_each_folder_explicitly():
    client = FakeBookmarkClient([
        {"id": "111", "name": "marketing"},
        {"id": "222", "name": "ai"},
    ])
    client.counts = {"111": 3, "222": 5}

    assert with_counts(client, client.folders()) == [
        {"id": "111", "name": "marketing", "count": 3},
        {"id": "222", "name": "ai", "count": 5},
    ]


def test_cost_estimates_use_x_read_prices():
    assert estimate_owned_read_cost(10) == 0.01
    assert estimate_post_read_cost(10) == 0.05
