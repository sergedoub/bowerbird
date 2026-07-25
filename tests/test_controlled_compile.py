import pytest

from bowerbird.controlled_compile import CompileToolError, CompileTools, apply_plan, build_compile_prompt


def test_compiler_can_write_only_wiki(tmp_path):
    tools = CompileTools(tmp_path)
    apply_plan(tools, '{"operations":[{"tool":"write","path":"wiki/topic/note.md","content":"ok"}]}')
    assert (tmp_path / "wiki/topic/note.md").read_text() == "ok"


def test_compiler_rejects_raw_and_path_escape(tmp_path):
    tools = CompileTools(tmp_path)
    with pytest.raises(CompileToolError):
        apply_plan(tools, '{"operations":[{"tool":"write","path":"raw/x.md","content":"no"}]}')
    with pytest.raises(CompileToolError):
        tools.write("../escape", "no")


def test_compile_prompt_contains_only_manifest_selected_files(tmp_path):
    (tmp_path / "compile").mkdir()
    (tmp_path / "compile" / "INSTRUCTIONS.md").write_text("rules")
    raw = tmp_path / "raw" / "bookmarks" / "topic" / "2026-07-01__one.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("selected raw")
    unrelated = tmp_path / "raw" / "pdfs" / "other" / "2026-07-01__two.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("must not be sent")

    prompt = build_compile_prompt(tmp_path)

    assert "selected raw" in prompt
    assert "must not be sent" not in prompt
    assert '"new_raw"' in prompt
