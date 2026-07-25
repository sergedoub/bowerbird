"""Top-level CLI routing stays thin while preserving verb arguments and help."""
from pathlib import Path

import pytest

from bowerbird import cli


def _script_tree(tmp_path: Path, name: str) -> Path:
    script = tmp_path / "bin" / name
    script.parent.mkdir()
    script.write_text("# test script\n", encoding="utf-8")
    return script


def test_routes_arguments_to_the_selected_script(monkeypatch, tmp_path):
    script = _script_tree(tmp_path, "pull.py")
    calls = []
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli.runpy, "run_path", lambda *args, **kwargs: calls.append((args, kwargs)))

    cli.main(["pull", "--topic", "marketing"])

    assert calls == [((str(script),), {"run_name": "__main__"})]
    assert cli.sys.argv == [str(script), "--topic", "marketing"]
    assert cli.os.environ["BOWERBIRD_PROG"] == "bowerbird pull"


def test_bare_auth_supplies_auth_subcommand(monkeypatch, tmp_path):
    script = _script_tree(tmp_path, "x_auth_spike.py")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli.runpy, "run_path", lambda *_args, **_kwargs: None)

    cli.main(["auth"])

    assert cli.sys.argv == [str(script), "auth"]


def test_static_help_does_not_execute_non_argparse_script(monkeypatch, tmp_path, capsys):
    _script_tree(tmp_path, "lint.py")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(
        cli.runpy,
        "run_path",
        lambda *_args, **_kwargs: pytest.fail("help must not execute lint.py"),
    )

    cli.main(["lint", "--help"])

    assert capsys.readouterr().out.strip() == cli.SYNOPSES["lint"]


def test_missing_checkout_script_has_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "ROOT", tmp_path)

    with pytest.raises(SystemExit, match="must run from a repo checkout"):
        cli.main(["doctor"])


def test_unknown_verb_is_rejected_by_argument_parser():
    with pytest.raises(SystemExit) as exc:
        cli.main(["unknown"])
    assert exc.value.code == 2
