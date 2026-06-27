"""The source repo starts clean: config templates only, no generated KB data.

Generated `raw/`, `wiki/`, and `recaps/` output belongs in an installed fork or
the separate bowerbird-demo repository, not in the product source repo.
"""
from pathlib import Path

from kb.config import AccountsConfig, RecapsConfig, TopicsConfig
from kb.recaps import validate_recap_files

ROOT = Path(__file__).resolve().parents[1]


def test_source_repo_has_no_generated_kb_data():
    for path in ("raw", "wiki", "recaps"):
        root = ROOT / path
        assert not root.exists() or not any(p.is_file() for p in root.rglob("*")), (
            f"{path}/ should not contain generated files"
        )


def test_empty_recaps_validate():
    assert validate_recap_files(ROOT) == []


def test_source_config_templates_parse_with_real_validators():
    topics = TopicsConfig.load(ROOT / "config" / "topics.toml")
    assert topics.topics == ()

    accounts = AccountsConfig.load(ROOT / "config" / "accounts.toml")
    assert accounts.accounts == ()

    recaps = RecapsConfig.load(ROOT / "config" / "recaps.toml")
    assert recaps.profiles == ()
