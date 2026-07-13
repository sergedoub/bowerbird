import sys

from bin import dump_search


def test_dump_search_without_config_or_bearer_is_a_successful_noop(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(dump_search, "ROOT", str(tmp_path))
    monkeypatch.setattr(dump_search, "load_local_env", lambda: None)
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["dump_search.py"])

    dump_search.main()

    assert capsys.readouterr().out == "No searches configured in config/searches.toml.\n"
