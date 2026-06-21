"""ProvenanceLinter: the citation invariant — frontmatter, citations, resolvable links."""
from kb.linter import lint, okf_conformance


def _wiki(tmp_path, sources: dict, concepts: dict):
    (tmp_path / "sources").mkdir(parents=True)
    (tmp_path / "concepts").mkdir(parents=True)
    for name, text in sources.items():
        (tmp_path / "sources" / name).write_text(text)
    for name, text in concepts.items():
        (tmp_path / "concepts" / name).write_text(text)
    return tmp_path


VALID_SOURCE = "---\nauthor: alice\nurl: https://x.com/x/status/1\ndate: 2026-01-01\n---\n\nKey claim.\n"


def test_valid_wiki_has_no_violations(tmp_path):
    wiki = _wiki(
        tmp_path,
        sources={"a-thread.md": VALID_SOURCE},
        concepts={"pricing.md": "Charge more.\n\nSee [[a-thread]].\n"},
    )
    assert lint(wiki) == []


def test_source_missing_frontmatter_is_flagged(tmp_path):
    wiki = _wiki(
        tmp_path,
        sources={"a-thread.md": "---\nauthor: alice\n---\n\nNo url or date.\n"},
        concepts={"pricing.md": "Charge more. [[a-thread]]\n"},
    )
    kinds = {(v.kind) for v in lint(wiki)}
    assert "missing_frontmatter" in kinds


def test_uncited_concept_is_flagged(tmp_path):
    wiki = _wiki(
        tmp_path,
        sources={"a-thread.md": VALID_SOURCE},
        concepts={"pricing.md": "Just my opinion, no citation.\n"},
    )
    kinds = {v.kind for v in lint(wiki)}
    assert "uncited_concept" in kinds


def test_broken_link_is_flagged(tmp_path):
    wiki = _wiki(
        tmp_path,
        sources={"a-thread.md": VALID_SOURCE},
        concepts={"pricing.md": "Charge more. [[does-not-exist]]\n"},
    )
    broken = [v for v in lint(wiki) if v.kind == "broken_link"]
    assert len(broken) == 1
    assert "does-not-exist" in broken[0].message


# --- raw_id resolution (only checked when repo_root is passed) ---

def _repo(tmp_path, topic="marketing", raws=(), account_raws=None, book_raws=()):
    """Build a tiny repo skeleton: raw/{bookmarks,accounts,books}/ plus wiki/<topic>/."""
    topic_raw = tmp_path / "raw" / "bookmarks" / topic
    topic_raw.mkdir(parents=True)
    for fname in raws:
        (topic_raw / fname).write_text("raw body")
    book_raw = tmp_path / "raw" / "books" / topic
    book_raw.mkdir(parents=True)
    for fname in book_raws:
        (book_raw / fname).write_text("raw body")
    if account_raws:
        for handle, files in account_raws.items():
            d = tmp_path / "raw" / "accounts" / handle
            d.mkdir(parents=True)
            for fname in files:
                (d / fname).write_text("raw body")
    wiki = tmp_path / "wiki" / topic
    (wiki / "sources").mkdir(parents=True)
    (wiki / "concepts").mkdir(parents=True)
    return tmp_path, wiki


def test_raw_id_resolves_for_bookmark_source(tmp_path):
    root, wiki = _repo(tmp_path, raws=["2026-01-01__999.md"])
    (wiki / "sources" / "x.md").write_text(
        "---\nauthor: a\nurl: u\ndate: 2026-01-01\nraw_id: \"999\"\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[x]]\n")
    assert lint(wiki, repo_root=root) == []


def test_raw_id_missing_for_bookmark_is_flagged(tmp_path):
    root, wiki = _repo(tmp_path, raws=[])  # no raw file for id 999
    (wiki / "sources" / "x.md").write_text(
        "---\nauthor: a\nurl: u\ndate: 2026-01-01\nraw_id: \"999\"\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[x]]\n")
    v = lint(wiki, repo_root=root)
    assert any(x.kind == "missing_raw" and "999" in x.message for x in v)


def test_raw_id_resolves_via_mirror_for_account_source(tmp_path):
    root, wiki = _repo(
        tmp_path,
        raws=[],  # no bookmark raw exists; must resolve via raw/accounts/
        account_raws={"bcherny": ["2026-05-24__555.md"]},
    )
    (wiki / "sources" / "y.md").write_text(
        "---\nauthor: '@bcherny'\nurl: u\ndate: 2026-05-24\nraw_id: \"555\"\n"
        "mirror: accounts/bcherny\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[y]]\n")
    assert lint(wiki, repo_root=root) == []


def test_raw_id_missing_in_account_mirror_is_flagged(tmp_path):
    root, wiki = _repo(tmp_path, account_raws={"bcherny": []})  # mirror dir exists, file doesn't
    (wiki / "sources" / "y.md").write_text(
        "---\nauthor: '@bcherny'\nurl: u\ndate: 2026-05-24\nraw_id: \"555\"\n"
        "mirror: accounts/bcherny\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[y]]\n")
    v = lint(wiki, repo_root=root)
    assert any(x.kind == "missing_raw" and "raw/accounts/bcherny" in x.message for x in v)


def test_raw_id_resolves_for_book_chapter_source(tmp_path):
    root, wiki = _repo(tmp_path, book_raws=["2016-05-16__never-split-the-difference-ch01.md"])
    (wiki / "sources" / "book.md").write_text(
        "---\nauthor: Chris Voss\nurl: book://never-split-the-difference/ch01\n"
        "date: 2016-05-16\nraw_id: never-split-the-difference-ch01\n"
        "source_type: book-chapter\nbook: never-split-the-difference\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[book]]\n")
    assert lint(wiki, repo_root=root) == []


def test_raw_id_missing_for_book_chapter_is_flagged_under_books_root(tmp_path):
    root, wiki = _repo(tmp_path, book_raws=[])
    (wiki / "sources" / "book.md").write_text(
        "---\nauthor: Chris Voss\nurl: book://never-split-the-difference/ch01\n"
        "date: 2016-05-16\nraw_id: never-split-the-difference-ch01\n"
        "source_type: book-chapter\nbook: never-split-the-difference\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[book]]\n")
    v = lint(wiki, repo_root=root)
    assert any(x.kind == "missing_raw" and "raw/books/marketing" in x.message for x in v)


def test_raw_path_resolves_generic_note_source(tmp_path):
    root, wiki = _repo(tmp_path, raws=[])
    raw = root / "raw" / "notes" / "marketing"
    raw.mkdir(parents=True)
    (raw / "2026-06-17__obsidian-note.md").write_text("raw body")
    (wiki / "sources" / "note.md").write_text(
        "---\nauthor: me\nurl: obsidian://open?vault=demo&file=x\ndate: 2026-06-17\n"
        "raw_path: raw/notes/marketing/2026-06-17__obsidian-note.md\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[note]]\n")
    assert lint(wiki, repo_root=root) == []


def test_raw_path_missing_file_is_flagged(tmp_path):
    root, wiki = _repo(tmp_path, raws=[])
    (wiki / "sources" / "note.md").write_text(
        "---\nauthor: me\nurl: u\ndate: 2026-06-17\n"
        "raw_path: raw/notes/marketing/2026-06-17__missing.md\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[note]]\n")
    v = lint(wiki, repo_root=root)
    assert any(x.kind == "missing_raw" and "raw_path" in x.message for x in v)


def test_invalid_raw_path_is_flagged(tmp_path):
    root, wiki = _repo(tmp_path, raws=[])
    (wiki / "sources" / "note.md").write_text(
        "---\nauthor: me\nurl: u\ndate: 2026-06-17\n"
        "raw_path: ../raw/notes/marketing/2026-06-17__x.md\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[note]]\n")
    v = lint(wiki, repo_root=root)
    assert any(x.kind == "invalid_raw_path" for x in v)


def test_unknown_raw_namespace_is_flagged(tmp_path):
    root, wiki = _repo(tmp_path, raws=[])
    raw = root / "raw" / "mystery" / "marketing"
    raw.mkdir(parents=True)
    (raw / "2026-06-17__x.md").write_text("raw body")
    (wiki / "sources" / "note.md").write_text(
        "---\nauthor: me\nurl: u\ndate: 2026-06-17\n"
        "raw_path: raw/mystery/marketing/2026-06-17__x.md\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[note]]\n")
    v = lint(wiki, repo_root=root)
    assert any(x.kind == "unknown_raw_namespace" for x in v)


def test_review_namespace_requires_reviewed_flag(tmp_path):
    root, wiki = _repo(tmp_path, raws=[])
    raw = root / "raw" / "pdfs" / "research"
    raw.mkdir(parents=True)
    (raw / "2026-06-17__paper-p12.md").write_text("raw body")
    (wiki / "sources" / "paper.md").write_text(
        "---\nauthor: a\nurl: file://paper.pdf\ndate: 2026-06-17\n"
        "raw_path: raw/pdfs/research/2026-06-17__paper-p12.md\n---\nbody\n"
    )
    (wiki / "concepts" / "c.md").write_text("[[paper]]\n")
    v = lint(wiki, repo_root=root)
    assert any(x.kind == "raw_not_compile_eligible" for x in v)

    (wiki / "sources" / "paper.md").write_text(
        "---\nauthor: a\nurl: file://paper.pdf\ndate: 2026-06-17\nreviewed: true\n"
        "raw_path: raw/pdfs/research/2026-06-17__paper-p12.md\n---\nbody\n"
    )
    assert lint(wiki, repo_root=root) == []


def test_raw_id_check_skipped_when_repo_root_not_provided(tmp_path):
    """Back-compat: lint(wiki) (no root) keeps the original three rules and nothing more."""
    wiki = _wiki(
        tmp_path,
        sources={"x.md": "---\nauthor: a\nurl: u\ndate: 2026-01-01\nraw_id: \"999\"\n---\n"},
        concepts={"c.md": "[[x]]\n"},
    )
    assert lint(wiki) == []  # no missing_raw violation because we didn't pass root


# --- OKF-native: markdown-link citations are accepted alongside legacy [[ ]] ---

def test_markdown_link_citation_counts_as_cited(tmp_path):
    wiki = _wiki(
        tmp_path,
        sources={"a-thread.md": VALID_SOURCE},
        concepts={"pricing.md": "Charge more. [a-thread](../sources/a-thread.md)\n"},
    )
    assert lint(wiki) == []


def test_broken_markdown_link_citation_is_flagged(tmp_path):
    wiki = _wiki(
        tmp_path,
        sources={"a-thread.md": VALID_SOURCE},
        concepts={"pricing.md": "Charge more. [gone](../sources/does-not-exist.md)\n"},
    )
    broken = [v for v in lint(wiki) if v.kind == "broken_link"]
    assert len(broken) == 1
    assert "does-not-exist" in broken[0].message


# --- OKF conformance floor: every non-reserved note carries a non-empty `type` ---

TYPED_SOURCE = "---\ntype: X Post\nauthor: a\nurl: https://x.com/x/status/1\ndate: 2026-01-01\n---\n\nClaim.\n"


def test_okf_conformance_flags_notes_missing_type(tmp_path):
    wiki = _wiki(
        tmp_path,
        sources={"a.md": VALID_SOURCE},  # VALID_SOURCE has no `type`
        concepts={"c.md": "[[a]]\n"},     # no frontmatter at all
    )
    violations = okf_conformance(wiki)
    assert {v.kind for v in violations} == {"missing_type"}
    assert len(violations) == 2  # the source and the concept


def test_okf_conformance_passes_when_typed_and_exempts_index(tmp_path):
    wiki = _wiki(
        tmp_path,
        sources={"a.md": TYPED_SOURCE},
        concepts={"c.md": "---\ntype: Concept\n---\n\n[a](../sources/a.md)\n"},
    )
    (wiki / "index.md").write_text("# Topic index\n")  # reserved file, exempt from type
    assert okf_conformance(wiki) == []
