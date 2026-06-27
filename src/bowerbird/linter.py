"""ProvenanceLinter — the citation invariant, made executable.

The compile step is generative (an LLM writes the wiki), so it can't be unit-tested.
This linter is its guardrail: it turns "every claim must be attributable" into checks
that fail the run / get written to _health.md instead of shipping uncited knowledge.

Rules (over wiki/<topic>/):
  1. every source note (sources/*.md) has the required frontmatter keys;
  2. every concept article (concepts/*.md) cites at least one source ([[...]] link);
  3. every [[link]] resolves to an existing source note;
  4. when `repo_root` is provided, each source note's `raw_path` resolves to a real,
     compile-eligible raw file. Legacy notes without `raw_path` fall back to `raw_id`
     resolution in the original bookmark/account/book roots.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .raw_sources import (
    is_compile_eligible,
    namespace_for,
    parse_raw_path,
    reviewed_for_compile,
)

REQUIRED_SOURCE_FRONTMATTER = ("author", "url", "date")
WIKILINK = re.compile(r"\[\[([^\]\|#]+)(?:[#|][^\]]*)?\]\]")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
MIRROR_PREFIX = "accounts/"
BOOK_SOURCE_TYPES = {"book-chapter"}
RESERVED_FILENAMES = {"index.md", "log.md"}


@dataclass(frozen=True)
class Violation:
    path: str
    kind: str
    message: str


def _frontmatter_block(text: str) -> str | None:
    m = FRONTMATTER.match(text)
    return m.group(1) if m else None


def _frontmatter_pairs(text: str) -> dict[str, str]:
    """Return top-level frontmatter key->value pairs.

    Skips indented lines (list/dict values) and unquotes simple scalar values. Good
    enough for what we read (`raw_id`, `mirror`); not a general YAML parser.
    """
    block = _frontmatter_block(text)
    if not block:
        return {}
    pairs: dict[str, str] = {}
    for line in block.splitlines():
        if not line or line.startswith(" ") or line.startswith("\t"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        # strip simple matching quotes
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        pairs[k.strip()] = v
    return pairs


def _link_target_stem(path: str) -> str:
    """Basename of a markdown-link path, minus any #anchor/?query and the .md suffix."""
    p = path.split("#", 1)[0].split("?", 1)[0].strip()
    return Path(p).stem


def _raw_dir_for_source(source_type: str | None, mirror: str | None, bookmark_raw: Path,
                        repo_root: Path, topic: str) -> Path:
    if mirror and mirror.startswith(MIRROR_PREFIX):
        handle = mirror[len(MIRROR_PREFIX):].strip().strip("/")
        return repo_root / "raw" / "accounts" / handle
    if source_type in BOOK_SOURCE_TYPES:
        return repo_root / "raw" / "books" / topic
    return bookmark_raw


def _raw_id_resolves(raw_id: str, source_type: str | None, mirror: str | None,
                     bookmark_raw: Path, repo_root: Path, topic: str) -> bool:
    """Check that `<date>__<raw_id>.md` exists in the expected raw root.

    Bookmark source notes (no mirror, source_type not book-chapter) -> raw/bookmarks/<topic>/.
    Book chapter source notes (source_type = book-chapter) -> raw/books/<topic>/.
    Account-mirror source notes (mirror = accounts/<handle>) -> raw/accounts/<handle>/.
    """
    raw_dir = _raw_dir_for_source(source_type, mirror, bookmark_raw, repo_root, topic)
    if not raw_dir.exists():
        return False
    # Filenames are deterministic <YYYY-MM-DD>__<raw_id>.md, but we glob to be
    # tolerant of any date prefix variation.
    return any(raw_dir.glob(f"*__{raw_id}.md"))


def _raw_path_violations(source_path: Path, raw_path: str, root: Path,
                         reviewed: bool) -> list[Violation]:
    info = parse_raw_path(raw_path)
    if info is None:
        return [
            Violation(
                str(source_path),
                "invalid_raw_path",
                f"raw_path '{raw_path}' must be repo-relative raw/<namespace>/<bucket>/<file>.md",
            )
        ]

    namespace = namespace_for(info.namespace)
    if namespace is None:
        return [
            Violation(
                str(source_path),
                "unknown_raw_namespace",
                f"raw_path namespace '{info.namespace}' is not declared",
            )
        ]

    violations: list[Violation] = []
    if not is_compile_eligible(namespace, reviewed=reviewed):
        state = namespace.compile_state
        violations.append(
            Violation(
                str(source_path),
                "raw_not_compile_eligible",
                f"raw namespace '{info.namespace}' is {state}; do not compile it unattended",
            )
        )

    if not (root / raw_path).exists():
        violations.append(
            Violation(
                str(source_path),
                "missing_raw",
                f"raw_path '{raw_path}' does not resolve to a file",
            )
        )
    return violations


def lint(wiki_dir: str | Path, repo_root: str | Path | None = None) -> list[Violation]:
    wiki = Path(wiki_dir)
    sources_dir = wiki / "sources"
    concepts_dir = wiki / "concepts"
    root = Path(repo_root) if repo_root is not None else None
    bookmark_raw = (root / "raw" / "bookmarks" / wiki.name) if root is not None else None

    source_stems = {p.stem for p in sources_dir.glob("*.md")} if sources_dir.exists() else set()
    violations: list[Violation] = []

    # Rule 1: source notes must carry required frontmatter.
    # Rule 4 (when root provided): raw_path resolves, with legacy raw_id fallback.
    for src in sorted(sources_dir.glob("*.md")) if sources_dir.exists() else []:
        text = src.read_text()
        fm = _frontmatter_pairs(text)
        keys = set(fm)
        missing = [k for k in REQUIRED_SOURCE_FRONTMATTER if k not in keys]
        if missing:
            violations.append(
                Violation(str(src), "missing_frontmatter",
                          f"source note missing frontmatter: {', '.join(missing)}")
            )
        if root is not None:
            raw_path = fm.get("raw_path", "").strip()
            raw_id = fm.get("raw_id", "").strip()
            mirror = fm.get("mirror") or None
            source_type = fm.get("source_type") or None
            if raw_path:
                violations.extend(
                    _raw_path_violations(
                        src,
                        raw_path,
                        root,
                        reviewed_for_compile(fm.get("reviewed")),
                    )
                )
            elif not raw_id:
                violations.append(
                    Violation(str(src), "missing_frontmatter",
                              "source note missing frontmatter: raw_path or raw_id")
                )
            elif not _raw_id_resolves(raw_id, source_type, mirror, bookmark_raw, root, wiki.name):
                raw_dir = _raw_dir_for_source(source_type, mirror, bookmark_raw, root, wiki.name)
                where = str(raw_dir.relative_to(root)) + "/"
                violations.append(
                    Violation(str(src), "missing_raw",
                              f"raw_id '{raw_id}' does not resolve to a file under {where}")
                )

    # Rules 2 & 3: concept articles must cite, and citations must resolve.
    # A citation is either a legacy [[stem]] wikilink or an OKF-native markdown link
    # into sources/ (e.g. [text](../sources/<stem>.md)). Both are accepted: the wiki is
    # migrated to markdown links, but the linter stays liberal in what it counts so an
    # Obsidian-style [[ ]] never silently drops a concept's provenance.
    for concept in sorted(concepts_dir.glob("*.md")) if concepts_dir.exists() else []:
        text = concept.read_text()
        wikilinks = WIKILINK.findall(text)
        # A markdown link into sources/ is an intended source citation (counts toward
        # "is cited" even if its target is wrong — a wrong one is a broken_link, exactly
        # like a broken [[ ]]).
        md_source_links = [p for p in MD_LINK.findall(text)
                           if p.endswith(".md") and "sources/" in p]
        if not wikilinks and not md_source_links:
            violations.append(
                Violation(str(concept), "uncited_concept",
                          "concept article has no source citations")
            )
        for target in wikilinks:
            if Path(target.strip()).stem not in source_stems:
                violations.append(
                    Violation(str(concept), "broken_link",
                              f"citation [[{target}]] does not resolve to a source note")
                )
        for p in md_source_links:
            if _link_target_stem(p) not in source_stems:
                violations.append(
                    Violation(str(concept), "broken_link",
                              f"citation [{p}] does not resolve to a source note")
                )
    return violations


def okf_conformance(wiki_dir: str | Path) -> list[Violation]:
    """OKF v0.1 floor check — added BENEATH the provenance lint, never replacing it.

    OKF's own conformance is deliberately weak (it tolerates missing fields and broken
    links). Bowerbird keeps the strict provenance rules in `lint()` and treats OKF
    `type`-presence as one additional minimum bar: every non-reserved note in the bundle
    (`sources/` + `concepts/`) must carry a non-empty `type` so any OKF consumer can
    route/filter/present it. Reserved files (index.md, log.md) are exempt by spec.
    """
    wiki = Path(wiki_dir)
    violations: list[Violation] = []
    for sub in ("sources", "concepts"):
        d = wiki / sub
        if not d.exists():
            continue
        for md in sorted(d.glob("*.md")):
            if md.name in RESERVED_FILENAMES:
                continue
            if not _frontmatter_pairs(md.read_text()).get("type", "").strip():
                violations.append(
                    Violation(str(md), "missing_type",
                              "OKF: note missing non-empty `type` frontmatter")
                )
    return violations


def _frontmatter_keys(text: str) -> set[str]:
    """Back-compat shim: return only the top-level frontmatter keys (no values)."""
    return set(_frontmatter_pairs(text))
