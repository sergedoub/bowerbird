from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_markdown_frontmatter_is_well_formed():
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT)
        if rel.parts and rel.parts[0] == ".git":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            continue
        closing = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
        assert closing is not None, f"{rel}: frontmatter opens but never closes"
        body = lines[1:closing]
        assert any(":" in line for line in body if line.strip()), f"{rel}: frontmatter has no key/value entries"
        assert not any(line.lstrip().startswith("#") for line in body), (
            f"{rel}: markdown heading found inside frontmatter"
        )
