from bowerbird.books import build_raw_doc, extract_sections, run_ingest
from bowerbird.config import Book
from bowerbird.raw_writer import RawWriter


BOOK = Book(
    book_id="fixture-book",
    topic="negotiation",
    title="Fixture Book",
    author="A. Author",
    published_date="2026-01-01",
    source_path="fixture.md",
)


def test_extract_sections_keeps_chapters_and_appendix_until_backmatter():
    md = """---
title: Fixture
---

## CONTENTS

## [**CHAPTER 1**](#c1){.cn}
## [**THE FIRST MOVE**](#t1){.ct}

Chapter one body.

## [**CHAPTER 2**](#c2){.cn}
## [**THE SECOND MOVE**](#t2){.ct}

Chapter two body.

## [**APPENDIX**](#a){.fmh}
## [**PREPARE A SHEET**](#a){.ct}

Appendix body.

## [**NOTES**](#notes){.fmh}

Notes should not be included.
"""
    sections = extract_sections(md, "fixture-book")
    assert [(s.raw_id, s.section_type, s.number, s.title) for s in sections] == [
        ("fixture-book-ch01", "chapter", 1, "THE FIRST MOVE"),
        ("fixture-book-ch02", "chapter", 2, "THE SECOND MOVE"),
        ("fixture-book-appendix", "appendix", None, "PREPARE A SHEET"),
    ]
    assert "Notes should not be included" not in sections[-1].body


def test_build_raw_doc_uses_book_frontmatter_and_deterministic_id():
    section = extract_sections("## CHAPTER 1\n## Title\n\nBody", "fixture-book")[0]
    doc = build_raw_doc(BOOK, section)
    assert doc.topic == "negotiation"
    assert doc.id == "fixture-book-ch01"
    assert doc.frontmatter["source_type"] == "book-chapter"
    assert doc.frontmatter["source_url"] == "book://fixture-book/ch01"
    assert doc.frontmatter["chapter"] == 1


def test_run_ingest_writes_once_then_skips(tmp_path):
    source = tmp_path / "book.md"
    source.write_text("## CHAPTER 1\n## Title\n\nBody")
    book = Book(
        book_id="fixture-book",
        topic="negotiation",
        title="Fixture Book",
        author="A. Author",
        published_date="2026-01-01",
        source_path=str(source),
    )
    writer = RawWriter(tmp_path / "raw" / "books")
    first = run_ingest(book, writer)
    second = run_ingest(book, writer)

    assert first["seen"] == 1
    assert first["written"] == 1
    assert second["skipped"] == 1
    assert (tmp_path / "raw" / "books" / "negotiation" / "2026-01-01__fixture-book-ch01.md").exists()
