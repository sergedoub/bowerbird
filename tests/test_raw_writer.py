"""RawWriter: deterministic naming, real frontmatter+body, and idempotent re-writes."""
import pytest

from bowerbird.models import RawAddress, RawDoc
from bowerbird.raw_writer import RawWriter


def _doc():
    return RawDoc(
        topic="marketing",
        id="2010013060333769098",
        created_at="2026-01-10T15:37:12.000Z",
        frontmatter={"author": "346563175", "source": "x-bookmark", "title": "the: formula"},
        body="I'm ready to share my formula.\n\nLet's go.",
    )


def test_path_is_deterministic(tmp_path):
    w = RawWriter(tmp_path)
    p = w.path_for(_doc())
    assert p == tmp_path / "marketing" / "2026-01-10__2010013060333769098.md"


def test_path_can_use_raw_address_namespace_and_bucket(tmp_path):
    doc = RawDoc(
        topic="claude-code",
        id="obsidian-agent-loop-8f31c2a9",
        created_at="2026-06-17T10:00:00Z",
        frontmatter={"source_type": "markdown-note"},
        body="body",
        address=RawAddress(namespace="notes", bucket="claude-code"),
    )
    p = RawWriter(tmp_path).path_for(doc)
    assert p == tmp_path / "notes" / "claude-code" / "2026-06-17__obsidian-agent-loop-8f31c2a9.md"


def test_write_creates_file_with_frontmatter_and_body(tmp_path):
    w = RawWriter(tmp_path)
    p = w.write(_doc())
    assert p is not None
    text = p.read_text()
    assert text.startswith("---\n")
    assert "author: 346563175" in text
    assert 'title: "the: formula"' in text  # value with ':' gets quoted
    assert "I'm ready to share my formula." in text


def test_write_quotes_yaml_indicator_prefixes(tmp_path):
    doc = RawDoc(
        topic="accounts/trq212",
        id="2053559397654348159",
        created_at="2026-05-10T19:34:48.000Z",
        frontmatter={"account": "@trq212"},
        body="body",
    )
    p = RawWriter(tmp_path).write(doc)

    assert p is not None
    assert 'account: "@trq212"' in p.read_text()


def test_rewrite_is_idempotent(tmp_path):
    w = RawWriter(tmp_path)
    first = w.write(_doc())
    before = first.read_text()
    second = w.write(_doc())  # same id -> no-op
    assert second is None
    assert first.read_text() == before  # untouched


@pytest.mark.parametrize("field,value", [
    ("topic", "../escape"),
    ("topic", "/tmp/escape"),
    ("topic", "one/two/three"),
    ("topic", "unknown/bucket"),
    ("namespace", "../escape"),
    ("namespace", "/tmp/escape"),
    ("bucket", "../../escape"),
    ("bucket", "a/b"),
    ("id", "../../escape"),
    ("id", "/tmp/escape"),
])
def test_path_rejects_unsafe_components(tmp_path, field, value):
    original = _doc()
    address = None
    topic = original.topic
    raw_id = original.id
    if field in {"namespace", "bucket"}:
        address = RawAddress(
            namespace=value if field == "namespace" else "notes",
            bucket=value if field == "bucket" else "marketing",
        )
    elif field == "topic":
        topic = value
    else:
        raw_id = value
    doc = RawDoc(
        topic=topic,
        id=raw_id,
        created_at=original.created_at,
        frontmatter=original.frontmatter,
        body=original.body,
        address=address,
    )

    with pytest.raises(ValueError, match=f"raw {field}"):
        RawWriter(tmp_path).path_for(doc)


def test_path_rejects_undeclared_namespace(tmp_path):
    original = _doc()
    doc = RawDoc(
        topic=original.topic,
        id=original.id,
        created_at=original.created_at,
        frontmatter=original.frontmatter,
        body=original.body,
        address=RawAddress(namespace="unknown", bucket="marketing"),
    )

    with pytest.raises(ValueError, match="not declared"):
        RawWriter(tmp_path).path_for(doc)


@pytest.mark.parametrize("created_at", ["", "../../../../escape", "/tmp/escape", "2026-02-30"])
def test_path_rejects_invalid_or_unsafe_created_at(tmp_path, created_at):
    original = _doc()
    doc = RawDoc(
        topic=original.topic,
        id=original.id,
        created_at=created_at,
        frontmatter=original.frontmatter,
        body=original.body,
    )

    with pytest.raises(ValueError, match="raw created_at"):
        RawWriter(tmp_path).path_for(doc)


def test_path_rejects_existing_symlink_that_escapes_root(tmp_path):
    raw_root = tmp_path / "raw"
    outside = tmp_path / "outside"
    raw_root.mkdir()
    outside.mkdir()
    (raw_root / "marketing").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside the configured raw root"):
        RawWriter(raw_root).path_for(_doc())


def test_path_accepts_existing_id_shapes(tmp_path):
    for raw_id in ("2010013060333769098", "obsidian-agent-loop-8f31c2a9", "id.v2_test-1"):
        doc = RawDoc(
            topic="marketing",
            id=raw_id,
            created_at="2026-01-10T00:00:00Z",
            frontmatter={},
            body="body",
        )
        assert RawWriter(tmp_path).path_for(doc).name == f"2026-01-10__{raw_id}.md"
