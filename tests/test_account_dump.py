"""run_dump: account timeline -> raw/, windowed and idempotent; doc captures reply links."""
from kb.account_dump import build_raw_doc, run_dump
from kb.config import Account
from kb.raw_writer import RawWriter


class FakeTimeline:
    """Stands in for TimelineClient: serves canned tweet pages per handle.

    `by_handle` values are either a flat list of tweets (served as one page) or a list of
    lists (served page by page). `pages_served` counts pages actually requested, so tests
    can assert that stop-at-seen avoided fetching deeper pages.
    """

    def __init__(self, by_handle):
        self._by_handle = by_handle
        self.start_times = []
        self.page_sizes = []
        self.pages_served = 0

    def user_tweet_pages(self, handle, *, start_time=None, page_size=100):
        self.start_times.append(start_time)
        self.page_sizes.append(page_size)
        items = self._by_handle.get(handle, [])
        pages = items if (items and isinstance(items[0], list)) else [items]
        for page in pages:
            self.pages_served += 1
            yield page


def _post(id, *, reply_to=None, conv=None, text=None):
    t = {
        "id": id,
        "author_id": "a",
        "conversation_id": conv or id,
        "created_at": "2026-05-01T00:00:00.000Z",
        "text": text or f"text {id}",
    }
    if reply_to:
        t["referenced_tweets"] = [{"type": "replied_to", "id": reply_to}]
    return t


def test_writes_posts_and_replies(tmp_path):
    accounts = [Account(handle="bcherny", topic="claude-code")]
    client = FakeTimeline({"bcherny": [_post("100"), _post("200", reply_to="100")]})
    writer = RawWriter(tmp_path)

    s = run_dump(accounts, client, writer)
    assert s["seen"] == 2 and s["written"] == 2 and s["skipped"] == 0
    assert (tmp_path / "bcherny" / "2026-05-01__100.md").exists()
    assert (tmp_path / "bcherny" / "2026-05-01__200.md").exists()


def test_rerun_is_idempotent_forward_only(tmp_path):
    accounts = [Account(handle="bcherny", topic="claude-code")]
    client = FakeTimeline({"bcherny": [_post("100")]})
    writer = RawWriter(tmp_path)
    run_dump(accounts, client, writer)
    s2 = run_dump(accounts, client, writer)  # nothing new
    assert s2["written"] == 0 and s2["skipped"] == 1


def test_start_time_is_passed_through_to_client(tmp_path):
    accounts = [Account(handle="bcherny", topic="claude-code")]
    client = FakeTimeline({"bcherny": [_post("100")]})
    run_dump(accounts, client, RawWriter(tmp_path), start_time="2026-05-21T00:00:00Z")
    assert client.start_times == ["2026-05-21T00:00:00Z"]


def test_windowed_rerun_stops_after_first_all_seen_page(tmp_path):
    accounts = [Account(handle="bcherny", topic="claude-code")]
    pages = [[_post("300"), _post("200")], [_post("100")]]
    writer = RawWriter(tmp_path)
    run_dump(accounts, FakeTimeline({"bcherny": pages}), writer, start_time="2026-05-21T00:00:00Z")

    client = FakeTimeline({"bcherny": pages})
    s = run_dump(accounts, client, writer, start_time="2026-05-21T00:00:00Z")
    assert client.pages_served == 1  # page 2 never fetched (never paid for)
    assert s["early_stops"] == 1 and s["written"] == 0 and s["skipped"] == 2


def test_full_run_never_stops_early(tmp_path):
    accounts = [Account(handle="bcherny", topic="claude-code")]
    writer = RawWriter(tmp_path)
    # Windowed instance already holds the newest post but not the older one below it.
    run_dump(accounts, FakeTimeline({"bcherny": [[_post("300")]]}), writer,
             start_time="2026-05-21T00:00:00Z")

    client = FakeTimeline({"bcherny": [[_post("300")], [_post("100")]]})
    s = run_dump(accounts, client, writer, start_time=None)  # --full
    assert client.pages_served == 2
    assert s["written"] == 1 and s["early_stops"] == 0
    assert (tmp_path / "bcherny" / "2026-05-01__100.md").exists()


def test_page_with_any_new_post_keeps_walking(tmp_path):
    accounts = [Account(handle="bcherny", topic="claude-code")]
    writer = RawWriter(tmp_path)
    run_dump(accounts, FakeTimeline({"bcherny": [[_post("300")]]}), writer,
             start_time="2026-05-21T00:00:00Z")

    # Page 1 mixes one seen + one new post -> walk continues into page 2.
    client = FakeTimeline({"bcherny": [[_post("400"), _post("300")], [_post("200")]]})
    s = run_dump(accounts, client, writer, start_time="2026-05-21T00:00:00Z")
    assert client.pages_served == 2
    assert s["written"] == 2 and s["early_stops"] == 0


def test_max_posts_caps_processing_and_requested_page_size(tmp_path):
    accounts = [Account(handle="bcherny", topic="claude-code")]
    client = FakeTimeline({"bcherny": [[_post(str(i)) for i in range(100, 110)]]})
    s = run_dump(accounts, client, RawWriter(tmp_path), max_posts=5)
    assert s["seen"] == 5 and s["written"] == 5
    assert client.page_sizes == [5]  # the cap also caps paid reads


def test_max_posts_stops_paging_across_pages(tmp_path):
    accounts = [Account(handle="bcherny", topic="claude-code")]
    client = FakeTimeline({"bcherny": [[_post("300"), _post("200")], [_post("100")]]})
    s = run_dump(accounts, client, RawWriter(tmp_path), max_posts=2)
    assert s["seen"] == 2
    assert client.pages_served == 1


def test_build_raw_doc_marks_replies_and_keeps_parent():
    doc = build_raw_doc(_post("200", reply_to="100"), "bcherny")
    assert doc.frontmatter["account"] == "@bcherny"
    assert doc.frontmatter["is_reply"] is True
    assert doc.frontmatter["in_reply_to"] == "100"


def test_build_raw_doc_marks_original_post():
    doc = build_raw_doc(_post("100"), "bcherny")
    assert doc.frontmatter["is_reply"] is False
    assert "in_reply_to" not in doc.frontmatter


def test_build_raw_doc_prefers_note_tweet_and_captures_article():
    t = _post("300", text="short")
    t["note_tweet"] = {"text": "the full long-form body that exceeds 280 chars"}
    t["article"] = {"title": "Deep Dive", "plain_text": "paragraph one. paragraph two."}
    doc = build_raw_doc(t, "bcherny")
    assert "the full long-form body" in doc.body  # note_tweet wins over truncated text
    assert "## Article: Deep Dive" in doc.body
    assert "paragraph two." in doc.body
    assert doc.frontmatter["article_title"] == "Deep Dive"
