"""Book ingestion: Markdown book -> raw/books/<topic>/ chapter files.

Books are long-form sources, so ingestion preserves chapter boundaries instead of
arbitrary token chunks. The compile step can then summarize each chapter source
faithfully and synthesize concepts with normal provenance links.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import Book
from .models import RawDoc


FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
CHAPTER_RE = re.compile(r"\bCHAPTER\s+(\d+)\b", re.IGNORECASE)
APPENDIX_RE = re.compile(r"\bAPPENDIX\b", re.IGNORECASE)
STOP_RE = re.compile(
    r"\b(ACKNOWLEDGMENTS?|NOTES|INDEX|ABOUT THE AUTHORS?|CREDITS|COPYRIGHT|ABOUT THE PUBLISHER)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BookSection:
    raw_id: str
    section_type: str
    number: int | None
    title: str
    body: str


def _without_frontmatter(text: str) -> str:
    return FRONTMATTER.sub("", text, count=1)


def _is_heading(line: str) -> bool:
    return line.startswith("#")


def clean_heading(line: str) -> str:
    """Convert noisy Calibre/Pandoc heading markup into readable heading text."""
    text = re.sub(r"^\s*#+\s*", "", line).strip()
    text = re.sub(r"\{#[^}]+\}", "", text)
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"\[\]\{#[^}]+\}", "", text)
    text = re.sub(r"\[\]\(#[^)]+\)", "", text)
    text = re.sub(r"\[[^\]]*\]\([^)]+\)", lambda m: m.group(0).split("](")[0].lstrip("["), text)
    text = text.replace("*", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _heading_after(lines: list[str], start: int) -> str:
    for line in lines[start + 1:start + 8]:
        if _is_heading(line):
            title = clean_heading(line)
            if title and not CHAPTER_RE.search(title) and not APPENDIX_RE.fullmatch(title):
                return title
    return ""


def _section_starts(lines: list[str]) -> list[tuple[int, str, int | None, str]]:
    starts: list[tuple[int, str, int | None, str]] = []
    for i, line in enumerate(lines):
        if not _is_heading(line):
            continue
        heading = clean_heading(line)
        chapter = CHAPTER_RE.search(heading)
        if chapter:
            number = int(chapter.group(1))
            title = _heading_after(lines, i) or f"Chapter {number}"
            starts.append((i, "chapter", number, title))
            continue
        if APPENDIX_RE.search(heading):
            title = _heading_after(lines, i) or "Appendix"
            starts.append((i, "appendix", None, title))
    return starts


def _stop_lines(lines: list[str]) -> set[int]:
    stops: set[int] = set()
    for i, line in enumerate(lines):
        if _is_heading(line) and STOP_RE.search(clean_heading(line)):
            stops.add(i)
    return stops


def extract_sections(markdown: str, book_id: str) -> list[BookSection]:
    """Extract chapters and appendices from Markdown while preserving section bodies."""
    lines = _without_frontmatter(markdown).splitlines()
    starts = _section_starts(lines)
    stops = _stop_lines(lines)
    sections: list[BookSection] = []

    for idx, (start, section_type, number, title) in enumerate(starts):
        later_starts = [s[0] for s in starts[idx + 1:]]
        later_stops = [line for line in stops if line > start]
        candidates = later_starts + later_stops + [len(lines)]
        end = min(candidates)
        body = "\n".join(lines[start:end]).strip()
        if not body:
            continue
        raw_id = (
            f"{book_id}-ch{number:02d}"
            if section_type == "chapter" and number is not None
            else f"{book_id}-appendix"
        )
        sections.append(
            BookSection(
                raw_id=raw_id,
                section_type=section_type,
                number=number,
                title=title,
                body=body,
            )
        )
    return sections


def build_raw_doc(book: Book, section: BookSection) -> RawDoc:
    section_key = f"ch{section.number:02d}" if section.number is not None else section.section_type
    fm = {
        "author": book.author,
        "book": book.book_id,
        "book_title": book.title,
        "created_at": book.published_date,
        "provenance": book.provenance,
        "section_title": section.title,
        "section_type": section.section_type,
        "source_path": book.source_path,
        "source_type": "book-chapter",
        "source_url": f"book://{book.book_id}/{section_key}",
        "topic": book.topic,
    }
    if section.number is not None:
        fm["chapter"] = section.number
    return RawDoc(
        topic=book.topic,
        id=section.raw_id,
        created_at=book.published_date,
        frontmatter=fm,
        body=section.body,
    )


def run_ingest(book: Book, writer) -> dict:
    """Split a configured book and write new raw chapter files."""
    source = Path(book.source_path).expanduser()
    text = source.read_text()
    sections = extract_sections(text, book.book_id)
    summary = {"seen": 0, "written": 0, "skipped": 0, "written_paths": []}
    for section in sections:
        summary["seen"] += 1
        path = writer.write(build_raw_doc(book, section))
        if path:
            summary["written"] += 1
            summary["written_paths"].append(str(path))
        else:
            summary["skipped"] += 1
    return summary
