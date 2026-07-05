from bowerbird.compile_plan import build_compile_manifest, manifest_prompt


def _write(path, text="body"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_manifest_lists_only_uncompiled_raw_paths(tmp_path):
    _write(tmp_path / "raw" / "bookmarks" / "marketing" / "2026-07-01__1.md")
    _write(tmp_path / "raw" / "bookmarks" / "marketing" / "2026-07-01__2.md")
    _write(
        tmp_path / "wiki" / "marketing" / "sources" / "compiled.md",
        "---\n"
        "author: a\n"
        "url: u\n"
        "date: 2026-07-01\n"
        "raw_path: raw/bookmarks/marketing/2026-07-01__1.md\n"
        "---\n",
    )
    _write(tmp_path / "wiki" / "marketing" / "concepts" / "growth.md")
    _write(tmp_path / "wiki" / "marketing" / "index.md")

    manifest = build_compile_manifest(tmp_path)

    assert manifest["total_new"] == 1
    assert manifest["new_raw"][0]["path"] == "raw/bookmarks/marketing/2026-07-01__2.md"
    assert manifest["new_raw"][0]["topic"] == "marketing"
    assert manifest["topics"] == [{
        "topic": "marketing",
        "relevant_files": [
            "wiki/marketing/index.md",
            "wiki/marketing/concepts/growth.md",
        ],
        "existing_source_count": 1,
        "existing_source_paths": ["wiki/marketing/sources/compiled.md"],
    }]


def test_manifest_bounds_existing_source_paths(tmp_path):
    _write(tmp_path / "raw" / "bookmarks" / "marketing" / "2026-07-01__new.md")
    for i in range(45):
        _write(tmp_path / "wiki" / "marketing" / "sources" / f"2026-07-{i + 1:02d}-old.md")

    manifest = build_compile_manifest(tmp_path)

    topic = manifest["topics"][0]
    assert topic["existing_source_count"] == 45
    assert len(topic["existing_source_paths"]) == 40
    assert topic["existing_source_paths"][0] == "wiki/marketing/sources/2026-07-06-old.md"


def test_manifest_routes_accounts_and_searches_through_config(tmp_path):
    _write(
        tmp_path / "config" / "accounts.toml",
        '[[handles]]\nhandle = "alice"\ntopic = "founder-notes"\n',
    )
    _write(
        tmp_path / "config" / "searches.toml",
        '[[searches]]\n'
        'name = "llm-wiki"\n'
        'topic = "llm-wiki"\n'
        'query = "\\"llm wiki\\" lang:en"\n',
    )
    _write(tmp_path / "raw" / "accounts" / "alice" / "2026-07-01__10.md")
    _write(tmp_path / "raw" / "accounts" / "unknown" / "2026-07-01__11.md")
    _write(tmp_path / "raw" / "searches" / "llm-wiki" / "2026-07-01__20.md")
    _write(tmp_path / "raw" / "searches" / "unmapped" / "2026-07-01__21.md")

    manifest = build_compile_manifest(tmp_path)

    assert [(item["path"], item["topic"]) for item in manifest["new_raw"]] == [
        ("raw/accounts/alice/2026-07-01__10.md", "founder-notes"),
        ("raw/searches/llm-wiki/2026-07-01__20.md", "llm-wiki"),
    ]


def test_manifest_skips_review_buckets_and_legacy_raw_id_matches(tmp_path):
    _write(tmp_path / "raw" / "notes" / "inbox" / "2026-07-01__note.md")
    _write(tmp_path / "raw" / "bookmarks" / "marketing" / "2026-07-01__99.md")
    _write(
        tmp_path / "wiki" / "marketing" / "sources" / "legacy.md",
        "---\n"
        "author: a\n"
        "url: u\n"
        "date: 2026-07-01\n"
        "raw_id: \"99\"\n"
        "---\n",
    )

    manifest = build_compile_manifest(tmp_path)

    assert manifest["total_new"] == 0
    assert manifest["new_raw"] == []
    assert manifest["topics"] == []


def test_manifest_prompt_embeds_bounded_scope():
    prompt = manifest_prompt({"version": 1, "total_new": 0, "new_raw": [], "topics": []})

    assert "Do not rescan raw/" in prompt
    assert '"total_new": 0' in prompt
