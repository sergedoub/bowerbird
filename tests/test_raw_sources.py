from kb.raw_sources import (
    COMPILE_AUTO,
    COMPILE_REVIEW,
    BUCKET_TOPIC,
    is_compile_eligible,
    namespace_for,
    parse_raw_path,
)


def test_declared_namespace_carries_semantics():
    notes = namespace_for("notes")
    assert notes is not None
    assert notes.bucket_kind == BUCKET_TOPIC
    assert notes.compile_state == COMPILE_AUTO
    assert notes.default_source_type == "markdown-note"

    pdfs = namespace_for("pdfs")
    assert pdfs is not None
    assert pdfs.compile_state == COMPILE_REVIEW
    assert not is_compile_eligible(pdfs)
    assert is_compile_eligible(pdfs, reviewed=True)


def test_parse_raw_path_accepts_only_repo_relative_raw_items():
    parsed = parse_raw_path("raw/notes/claude-code/2026-06-17__agent-loop.md")
    assert parsed is not None
    assert parsed.namespace == "notes"
    assert parsed.bucket == "claude-code"
    assert parsed.filename == "2026-06-17__agent-loop.md"

    assert parse_raw_path("/raw/notes/topic/x.md") is None
    assert parse_raw_path("raw/notes/../topic/x.md") is None
    assert parse_raw_path("wiki/notes/topic/x.md") is None
    assert parse_raw_path("raw/notes/topic/x.txt") is None
