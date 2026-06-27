"""run_pull: writes new bookmarks to raw/, reconstructs thread heads, idempotent on re-run."""
from bowerbird.config import Topic
from bowerbird.models import Bookmark, Tweet
from bowerbird.pull import build_raw_doc, run_pull
from bowerbird.raw_writer import RawWriter


class FakeBookmarks:
    def __init__(self, by_folder):
        self._by_folder = by_folder
        self.calls = []

    def bookmarks_in_folder(self, folder_id, topic, *, limit=None):
        self.calls.append((folder_id, topic, limit))
        items = self._by_folder.get(folder_id, [])
        if limit is not None:
            items = items[:limit]
        for tw in items:
            yield Bookmark(tweet=tw, folder_id=folder_id, topic=topic)


class FakeSearch:
    def __init__(self):
        self.calls = 0

    def fetch_conversation(self, conversation_id, author_id):
        self.calls += 1
        return []  # standalone -> assemble yields a thread of one (the head)


def _tw(id, conv=None):
    conv = conv or id
    return Tweet(id=id, author_id="a", conversation_id=conv, created_at="2026-05-01T00:00:00.000Z", text=f"text {id}")


def test_writes_new_bookmarks_and_reconstructs_heads(tmp_path):
    topics = [Topic(name="marketing", folder_ids=("F1",))]
    bm = FakeBookmarks({"F1": [_tw("100"), _tw("200")]})  # both are heads (id == conversation_id)
    search = FakeSearch()
    writer = RawWriter(tmp_path)

    s = run_pull(topics, bm, search, writer)
    assert s["seen"] == 2 and s["written"] == 2 and s["threads"] == 2
    assert (tmp_path / "marketing" / "2026-05-01__100.md").exists()


def test_rerun_is_idempotent_forward_only(tmp_path):
    topics = [Topic(name="marketing", folder_ids=("F1",))]
    bm = FakeBookmarks({"F1": [_tw("100")]})
    writer = RawWriter(tmp_path)
    run_pull(topics, bm, FakeSearch(), writer)
    s2 = run_pull(topics, bm, FakeSearch(), writer)  # nothing new
    assert s2["written"] == 0 and s2["skipped"] == 1


def test_no_threads_flag_skips_search(tmp_path):
    topics = [Topic(name="marketing", folder_ids=("F1",))]
    search = FakeSearch()
    run_pull(topics, FakeBookmarks({"F1": [_tw("100")]}), search, RawWriter(tmp_path), reconstruct_threads=False)
    assert search.calls == 0


def test_limit_per_folder_caps_each_folder(tmp_path):
    topics = [Topic(name="marketing", folder_ids=("F1", "F2"))]
    bm = FakeBookmarks({
        "F1": [_tw("100"), _tw("200")],
        "F2": [_tw("300"), _tw("400")],
    })
    s = run_pull(topics, bm, FakeSearch(), RawWriter(tmp_path), limit_per_folder=1)

    assert s["seen"] == 2 and s["written"] == 2
    assert s["limit_per_folder"] == 1
    assert bm.calls == [("F1", "marketing", 1), ("F2", "marketing", 1)]
    assert (tmp_path / "marketing" / "2026-05-01__100.md").exists()
    assert (tmp_path / "marketing" / "2026-05-01__300.md").exists()


def test_stop_at_existing_keeps_scheduled_pull_forward_only(tmp_path):
    topics = [Topic(name="marketing", folder_ids=("F1",))]
    writer = RawWriter(tmp_path)
    writer.write(build_raw_doc(Bookmark(tweet=_tw("200"), folder_id="F1", topic="marketing"), None))
    bm = FakeBookmarks({"F1": [_tw("300"), _tw("200"), _tw("100")]})

    s = run_pull(topics, bm, FakeSearch(), writer, stop_at_existing=True)

    assert s["seen"] == 2
    assert s["written"] == 1
    assert s["skipped"] == 1
    assert s["stopped_at_existing"] == 1
    assert (tmp_path / "marketing" / "2026-05-01__300.md").exists()
    assert not (tmp_path / "marketing" / "2026-05-01__100.md").exists()


def test_existing_thread_head_does_not_reconstruct_before_skip(tmp_path):
    topics = [Topic(name="marketing", folder_ids=("F1",))]
    writer = RawWriter(tmp_path)
    writer.write(build_raw_doc(Bookmark(tweet=_tw("100"), folder_id="F1", topic="marketing"), None))
    search = FakeSearch()

    s = run_pull(topics, FakeBookmarks({"F1": [_tw("100")]}), search, writer)

    assert s["skipped"] == 1
    assert search.calls == 0


def test_build_raw_doc_captures_article_body_and_handle():
    bm = Bookmark(
        tweet=_tw("100"),
        folder_id="F1",
        topic="marketing",
        article_title="The Complete Guide",
        article_text="Step 1: pick the right app. Step 2: distribution.",
        author_username="rork",
    )
    doc = build_raw_doc(bm, None)
    assert doc.frontmatter["author"] == "@rork"      # handle, not numeric id
    assert "## Article: The Complete Guide" in doc.body
    assert "Step 2: distribution." in doc.body         # full article body, not just a pointer


def test_build_raw_doc_falls_back_to_author_id_without_handle():
    bm = Bookmark(tweet=_tw("100"), folder_id="F1", topic="marketing")
    assert build_raw_doc(bm, None).frontmatter["author"] == "a"  # author_id from _tw
