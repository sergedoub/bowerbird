"""The shipped demo instance must stay valid: lint-clean wiki and recaps.

The public source repo carries synthetic topic and account-mirror data in the
real top-level pipeline paths. If the linter rules or recap contract change,
these tests force that demo instance to be regenerated alongside.
"""
from pathlib import Path

from kb.config import AccountsConfig, RecapsConfig, TopicsConfig
from kb.linter import lint, okf_conformance
from kb.recaps import validate_recap_files

ROOT = Path(__file__).resolve().parents[1]


def test_demo_wiki_passes_provenance_lint():
    topic_dirs = [p for p in (ROOT / "wiki").iterdir() if p.is_dir()]
    assert topic_dirs, "wiki has no demo topics"
    violations = []
    for topic in topic_dirs:
        violations += lint(topic, repo_root=ROOT)
        violations += okf_conformance(topic)
    assert violations == [], f"demo wiki has provenance/OKF violations: {violations}"


def test_demo_recaps_validate():
    assert validate_recap_files(ROOT) == []


def test_demo_configs_parse_with_real_validators():
    topics = TopicsConfig.load(ROOT / "config" / "topics.toml")
    assert topics.topics[0].name == "getting-started"

    accounts = AccountsConfig.load(ROOT / "config" / "accounts.toml")
    assert len(accounts.accounts) == 4
    assert all(a.label for a in accounts.accounts)

    recaps = RecapsConfig.load(ROOT / "config" / "recaps.toml")
    assert recaps.profiles[0].topics == ("getting-started",)

    account_profile = next(p for p in recaps.profiles if p.name == "ai-accounts-daily")
    assert set(account_profile.accounts) == {a.handle.lower() for a in accounts.accounts}
