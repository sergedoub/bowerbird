import builtins
from types import SimpleNamespace

import pytest

from bin import init_wizard, push_secrets
from bowerbird.github_secrets import set_github_secret


def test_github_secret_value_is_sent_over_stdin_not_process_arguments(tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return type("Result", (), {"returncode": 0, "stderr": b""})()

    result = set_github_secret(
        "OPENAI_API_KEY",
        "super-secret-value",
        cwd=tmp_path,
        repo="owner/instance",
        runner=run,
    )

    command, kwargs = calls[0]
    assert command == [
        "gh", "secret", "set", "OPENAI_API_KEY", "--repo", "owner/instance",
    ]
    assert "super-secret-value" not in command
    assert kwargs["input"] == b"super-secret-value"
    assert kwargs["cwd"] == tmp_path
    assert kwargs["capture_output"] is True
    assert result.returncode == 0


@pytest.mark.parametrize("module,args", ((init_wizard, ("NAME", "secret")),
                                         (push_secrets, ("owner/repo", "NAME", "secret"))))
def test_secret_cli_entry_points_share_the_stdin_transport(monkeypatch, module, args):
    calls = []

    def safe_setter(name, value, **kwargs):
        calls.append((name, value, kwargs))
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(module, "set_github_secret", safe_setter)

    assert module.set_secret(*args) is True
    assert calls[0][0:2] == ("NAME", "secret")


def test_init_wizard_wires_secret_prompts_to_getpass(monkeypatch):
    captured = {}
    monkeypatch.setattr(init_wizard, "load_env_file", lambda _path: None)
    monkeypatch.setattr(builtins, "input", lambda _prompt: "visible")
    monkeypatch.setattr(init_wizard.getpass, "getpass", lambda _prompt: "hidden")

    def fake_run(io, _deps):
        captured["io"] = io
        return SimpleNamespace(aborted=False)

    monkeypatch.setattr(init_wizard, "run_wizard", fake_run)

    with pytest.raises(SystemExit) as exit_info:
        init_wizard.main()

    assert exit_info.value.code == 0
    assert captured["io"].ask("visible prompt") == "visible"
    assert captured["io"].secret("hidden prompt") == "hidden"
