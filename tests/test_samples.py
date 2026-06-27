"""The shipped sample data must stay valid: lint-clean wiki and recap artifacts.

Samples double as CI fixtures. If the linter rules or recap contract change,
these tests force the samples to be regenerated alongside.
"""
from pathlib import Path

from kb.config import AccountsConfig, RecapsConfig, TopicsConfig
from kb.linter import lint, okf_conformance
from kb.recaps import validate_recap_files

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_sample_wiki_passes_provenance_lint():
    topic_dirs = [p for p in (SAMPLES / "wiki").iterdir() if p.is_dir()]
    assert topic_dirs, "samples/wiki has no topics"
    violations = []
    for topic in topic_dirs:
        violations += lint(topic, repo_root=SAMPLES)
        violations += okf_conformance(topic)
    assert violations == [], f"sample wiki has provenance/OKF violations: {violations}"


def test_sample_recaps_validate():
    assert validate_recap_files(SAMPLES) == []


def test_sample_configs_parse_with_real_validators():
    topics = TopicsConfig.load(SAMPLES / "config" / "topics.toml")
    assert topics.topics[0].name == "getting-started"

    accounts = AccountsConfig.load(SAMPLES / "config" / "accounts.toml")
    assert len(accounts.accounts) == 4
    assert all(a.label for a in accounts.accounts)

    recaps = RecapsConfig.load(SAMPLES / "config" / "recaps.toml")
    assert recaps.profiles[0].topics == ("getting-started",)
