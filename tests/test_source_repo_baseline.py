"""The source repo starts clean: config templates only, no generated Bowerbird data.

Generated `raw/`, `wiki/`, and `recaps/` output belongs in an installed fork or
the separate bowerbird-demo repository, not in the product source repo.
"""
import tomllib
from pathlib import Path

from bowerbird.repo_boundary import SOURCE_REPOSITORY
from bowerbird.config import AccountsConfig, RecapsConfig, TopicsConfig
from bowerbird.recaps import validate_recap_files

ROOT = Path(__file__).resolve().parents[1]


def test_source_repo_has_no_generated_bowerbird_data():
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


def test_public_package_name_matches_source_package():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "bowerbird"
    assert pyproject["project"]["scripts"]["bowerbird"] == "bowerbird.cli:main"
    assert (ROOT / "src" / "bowerbird").is_dir()
    assert not (ROOT / "src" / "kb").exists()


def test_mutating_workflows_cannot_run_in_source_repo():
    for name in ("pull.yml", "account-dump.yml", "compile.yml", "recap.yml"):
        workflow = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert f"github.repository != '{SOURCE_REPOSITORY}'" in workflow
        assert "vars.BOWERBIRD_LIVE_INSTANCE == 'true'" in workflow
