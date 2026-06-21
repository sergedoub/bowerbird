#!/usr/bin/env python3
"""One-time, idempotent migration: make wiki/ a native Open Knowledge Format (OKF) v0.1 bundle.

What it does (wiki/ only — it never reads or writes raw/):

  1. Stamp a `type` on every source + concept note (OKF's one required field).
     Sources map from `source_type` (book-chapter -> "Book Chapter", else "X Post");
     concepts get "Concept".
  2. Convert legacy [[stem]] wikilinks into OKF-native relative markdown links that
     resolve to the cited source note (e.g. [stem](../sources/<stem>.md)).
  3. Strip frontmatter from each per-topic index.md (OKF reserves index.md as
     frontmatter-free).
  4. Write wiki/index.md — the bundle-root index — declaring `okf_version: "0.1"`
     (the only place OKF permits frontmatter on an index).

Re-running is a no-op (notes that already carry `type` and files with no `[[ ]]` are
skipped). Use --dry-run to preview counts without writing.

    python3 bin/migrate_okf.py --dry-run
    python3 bin/migrate_okf.py
    python3 bin/migrate_okf.py samples/wiki      # migrate the public launch seed too
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WIKI = ROOT / "wiki"

WIKILINK = re.compile(r"\[\[([^\]\|#]+)(?:[#|][^\]]*)?\]\]")
FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_block_or_None, remainder_including_leading_newline)."""
    m = FRONTMATTER.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def stamp_type(text: str, layer: str) -> str | None:
    """Return text with a `type` line added, or None if it already has one.

    layer is "concept" or "source"; sources derive the value from `source_type`.
    """
    fm, rest = split_frontmatter(text)
    if fm is not None and re.search(r"(?m)^type\s*:", fm):
        return None  # idempotent
    if layer == "concept":
        type_value = "Concept"
    elif fm and re.search(r"(?m)^source_type\s*:\s*['\"]?book-chapter", fm):
        type_value = "Book Chapter"
    else:
        type_value = "X Post"
    if fm is None:
        return f"---\ntype: {type_value}\n---\n\n{text.lstrip()}"
    return f"---\ntype: {type_value}\n{fm}\n---{rest}"


def convert_links(text: str, base_dir: Path, source_paths: dict[str, Path]) -> tuple[str | None, list[str]]:
    """Rewrite [[stem]] -> [stem](<relpath-to-source>). Returns (new_text|None, unresolved)."""
    if "[[" not in text:
        return None, []
    unresolved: list[str] = []

    def repl(m: re.Match) -> str:
        target = re.split(r"[#|]", m.group(1).strip())[0].strip()
        src = source_paths.get(target)
        if src is None:
            unresolved.append(target)
            return m.group(0)  # leave untouched; lint will surface it
        rel = os.path.relpath(src, base_dir)
        return f"[{target}]({rel})"

    new = WIKILINK.sub(repl, text)
    return (new if new != text else None), unresolved


def strip_frontmatter_block(text: str) -> str | None:
    """Remove a leading --- frontmatter block (for index.md). None if there is none."""
    fm, rest = split_frontmatter(text)
    if fm is None:
        return None
    return rest.lstrip("\n")


def build_root_index(topics: list[str]) -> str:
    lines = [
        "---",
        'okf_version: "0.1"',
        "---",
        "",
        "# Knowledge Base",
        "",
        "An Open Knowledge Format (OKF) v0.1 bundle: plain markdown notes with YAML "
        "frontmatter, organized per topic into faithful `sources/` and synthesized "
        "`concepts/`, where every concept claim cites a source.",
        "",
        "## Topics",
        "",
    ]
    lines += [f"* [{t}]({t}/index.md)" for t in topics]
    return "\n".join(lines) + "\n"


def main() -> None:
    dry = "--dry-run" in sys.argv
    # Optional positional arg: a wiki bundle root to migrate (default: <repo>/wiki).
    # Used to also migrate samples/wiki, the public launch seed.
    positional = [a for a in sys.argv[1:] if not a.startswith("-")]
    wiki_root = Path(positional[0]).resolve() if positional else WIKI
    assert wiki_root.name == "wiki" and wiki_root.is_dir(), f"expected a wiki/ dir at {wiki_root}"

    counts = {"type_sources": 0, "type_concepts": 0, "files_relinked": 0,
              "links_converted": 0, "indexes_stripped": 0}
    unresolved: list[tuple[str, str]] = []

    def write(path: Path, new_text: str) -> None:
        if not dry:
            path.write_text(new_text)

    topics = sorted(p.name for p in wiki_root.iterdir() if p.is_dir())
    for topic in topics:
        topic_dir = wiki_root / topic
        sources_dir = topic_dir / "sources"
        concepts_dir = topic_dir / "concepts"
        source_paths = {p.stem: p for p in sources_dir.glob("*.md")} if sources_dir.exists() else {}

        # 1. Stamp `type`.
        for sp in sorted(source_paths.values()):
            new = stamp_type(sp.read_text(), "source")
            if new is not None:
                write(sp, new)
                counts["type_sources"] += 1
        for cp in sorted(concepts_dir.glob("*.md")) if concepts_dir.exists() else []:
            new = stamp_type(cp.read_text(), "concept")
            if new is not None:
                write(cp, new)
                counts["type_concepts"] += 1

        # 2. Convert wikilinks in concepts and sources (links resolve within the topic).
        link_files = []
        if concepts_dir.exists():
            link_files += sorted(concepts_dir.glob("*.md"))
        link_files += sorted(source_paths.values())
        for f in link_files:
            text = f.read_text()
            n_before = len(WIKILINK.findall(text))
            new, missing = convert_links(text, f.parent, source_paths)
            unresolved += [(str(f.relative_to(ROOT)), s) for s in missing]
            if new is not None:
                write(f, new)
                counts["files_relinked"] += 1
                counts["links_converted"] += n_before - len(missing)

        # 3. Strip frontmatter from the per-topic index.md.
        idx = topic_dir / "index.md"
        if idx.exists():
            stripped = strip_frontmatter_block(idx.read_text())
            if stripped is not None:
                write(idx, stripped)
                counts["indexes_stripped"] += 1

    # 4. Bundle-root index with okf_version.
    root_index = wiki_root / "index.md"
    root_existed = root_index.exists()
    write(root_index, build_root_index(topics))

    tag = "DRY RUN — no files written" if dry else "applied"
    print(f"OKF migration ({tag}):")
    print(f"  type stamped:      {counts['type_sources']} sources, {counts['type_concepts']} concepts")
    print(f"  wikilinks->md:     {counts['links_converted']} links across {counts['files_relinked']} files")
    print(f"  index frontmatter: {counts['indexes_stripped']} topic indexes stripped")
    print(f"  bundle-root index: wiki/index.md {'(updated)' if root_existed else '(created)'} with okf_version 0.1")
    if unresolved:
        print(f"\n  WARNING: {len(unresolved)} wikilink(s) did not resolve to a source note "
              f"(left untouched — lint will flag):")
        for path, stem in unresolved[:20]:
            print(f"    {path}: [[{stem}]]")


if __name__ == "__main__":
    main()
