"""Recap feed builder: lane grouping, labels, caps, ordering — pure over injected reads."""
from kb.recap_feed import (
    build_feed,
    label_slug,
    origin_from_frontmatter,
    parse_frontmatter,
    strip_frontmatter,
)


def _note(mirror=None, body="the note body", date=None):
    fm = ["---", "author: '@someone'", "url: https://x.com/x/status/1"]
    if date:
        fm.append(f"date: {date}")
    if mirror:
        fm.append(f"mirror: {mirror}")
    fm.append("---")
    return "\n".join(fm) + f"\n\n{body}\n"


def test_groups_mirror_notes_into_account_lanes_and_rest_into_topics():
    files = {
        "wiki/claude-code/sources/2026-06-10-bcherny-tip.md": _note(mirror="accounts/bcherny"),
        "wiki/marketing/sources/2026-06-10-pricing.md": _note(),
    }
    feed = build_feed(list(files), files.__getitem__, today="2026-06-11")
    assert list(feed["accounts"]) == ["bcherny"]
    assert list(feed["topics"]) == ["marketing"]
    assert feed["summary"] == {"total_new": 2, "account_lanes": 1, "topic_lanes": 1}
    assert feed["generated"] == "2026-06-11"


def test_labels_from_config_win_over_slug_prettification():
    files = {"wiki/t/sources/2026-06-10-a.md": _note(mirror="accounts/bcherny")}
    feed = build_feed(list(files), files.__getitem__, today="2026-06-11",
                      labels={"bcherny": "Boris"})
    assert feed["accounts"]["bcherny"]["label"] == "Boris"

    feed_default = build_feed(list(files), files.__getitem__, today="2026-06-11")
    assert feed_default["accounts"]["bcherny"]["label"] == "Bcherny"


def test_caps_notes_per_lane_but_counts_all():
    files = {
        f"wiki/m/sources/2026-06-{10 + i:02d}-n{i}.md": _note(date=f"2026-06-{10 + i:02d}")
        for i in range(12)
    }
    feed = build_feed(list(files), files.__getitem__, today="2026-06-22", max_notes=8)
    lane = feed["topics"]["m"]
    assert lane["total_new"] == 12
    assert len(lane["notes"]) == 8
    dates = [n["date"] for n in lane["notes"]]
    assert dates == sorted(dates, reverse=True)  # newest-first


def test_truncates_bodies_and_strips_frontmatter():
    files = {"wiki/m/sources/2026-06-10-long.md": _note(body="x" * 5000)}
    feed = build_feed(list(files), files.__getitem__, today="2026-06-11", max_body=100)
    text = feed["topics"]["m"]["notes"][0]["text"]
    assert len(text) == 100
    assert "author:" not in text


def test_note_metadata_includes_origin_source_type_and_raw_path():
    files = {
        "wiki/marketing/sources/2026-06-10-clip.md": (
            "---\nauthor: a\nurl: https://example.com\ndate: 2026-06-10\n"
            "origin: clips\nsource_type: web-clip\n"
            "raw_path: raw/clips/marketing/2026-06-10__clip.md\n---\n\nbody\n"
        )
    }
    feed = build_feed(list(files), files.__getitem__, today="2026-06-11")
    note = feed["topics"]["marketing"]["notes"][0]
    assert note["origin"] == "clips"
    assert note["source_type"] == "web-clip"
    assert note["raw_path"] == "raw/clips/marketing/2026-06-10__clip.md"


def test_unreadable_paths_are_skipped():
    def read(_p):
        raise OSError("gone")

    feed = build_feed(["wiki/m/sources/2026-06-10-x.md"], read, today="2026-06-11")
    assert feed["summary"]["total_new"] == 0


def test_empty_window_produces_quiet_feed():
    feed = build_feed([], lambda p: "", today="2026-06-11")
    assert feed["summary"] == {"total_new": 0, "account_lanes": 0, "topic_lanes": 0}


def test_helpers():
    assert label_slug("claude-code") == "Claude Code"
    assert parse_frontmatter("no frontmatter") == {}
    assert strip_frontmatter("plain text") == "plain text"
    assert origin_from_frontmatter({"raw_path": "raw/notes/t/2026-06-10__x.md"}) == "notes"
