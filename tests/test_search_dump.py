"""run_dump: X Recent Search -> raw/searches/<monitor>/."""
import datetime as dt

from bowerbird.config import SearchMonitor
from bowerbird.raw_writer import RawWriter
from bowerbird.search_dump import build_raw_doc, newest_raw_id, run_dump


class FakeSearchClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def search_pages(self, monitor, *, since_id=None, start_time=None, max_results=None, max_pages=None):
        self.calls.append({
            "monitor": monitor.name,
            "since_id": since_id,
            "start_time": start_time,
            "max_results": max_results,
            "max_pages": max_pages,
        })
        yield from self.pages


def _monitor():
    return SearchMonitor(
        name="llm-wiki",
        topic="llm-wiki",
        query='"llm wiki" lang:en -is:retweet -is:reply',
    )


def _post(tweet_id, *, author_id="a1"):
    return {
        "id": tweet_id,
        "author_id": author_id,
        "conversation_id": tweet_id,
        "created_at": "2026-06-30T04:01:00.000Z",
        "text": f"text {tweet_id}",
        "lang": "en",
    }


def test_search_dump_writes_raw_search_files_with_author_url(tmp_path):
    page = {
        "data": [_post("100")],
        "includes": {"users": [{"id": "a1", "username": "alice", "name": "Alice"}]},
        "meta": {},
    }
    client = FakeSearchClient([page])
    summary = run_dump(
        [_monitor()],
        client,
        RawWriter(tmp_path),
        raw_root=tmp_path,
        now_utc=dt.datetime(2026, 6, 30, 8, 0, tzinfo=dt.UTC),
    )

    raw = tmp_path / "searches" / "llm-wiki" / "2026-06-30__100.md"
    assert summary["written"] == 1
    assert raw.exists()
    text = raw.read_text()
    assert "author: \"@alice\"" in text
    assert 'source_url: "https://x.com/alice/status/100"' in text
    assert "monitor: llm-wiki" in text
    assert client.calls[0]["start_time"] == "2026-06-29T08:00:00Z"


def test_search_dump_uses_since_id_after_first_run(tmp_path):
    monitor = _monitor()
    writer = RawWriter(tmp_path)
    first = FakeSearchClient([{"data": [_post("100")], "includes": {}, "meta": {}}])
    run_dump(
        [monitor],
        first,
        writer,
        raw_root=tmp_path,
        now_utc=dt.datetime(2026, 6, 30, 8, 0, tzinfo=dt.UTC),
    )

    second = FakeSearchClient([{"data": [_post("100")], "includes": {}, "meta": {}}])
    summary = run_dump(
        [monitor],
        second,
        writer,
        raw_root=tmp_path,
        now_utc=dt.datetime(2026, 6, 30, 12, 0, tzinfo=dt.UTC),
    )
    assert newest_raw_id(tmp_path, "llm-wiki") == "100"
    assert second.calls[0]["since_id"] == "100"
    assert second.calls[0]["start_time"] is None
    assert summary["written"] == 0
    assert summary["skipped"] == 1


def test_build_raw_doc_falls_back_to_stable_status_url():
    doc = build_raw_doc(_post("200", author_id="42"), _monitor(), None)
    assert doc.frontmatter["author"] == "42"
    assert doc.frontmatter["source_url"] == "https://x.com/i/web/status/200"
    assert doc.address is not None
    assert doc.address.namespace == "searches"
    assert doc.address.bucket == "llm-wiki"
