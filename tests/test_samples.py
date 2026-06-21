"""The shipped sample data must stay valid: lint-clean wiki, contract-true feed.

Samples double as CI fixtures — if the linter rules or feed contract change, these
tests force the samples to be regenerated alongside.
"""
import json
from pathlib import Path

from kb.linter import lint, okf_conformance
from kb.recap_feed import build_feed

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def _sample_source_paths():
    return sorted(
        str(p.relative_to(SAMPLES))
        for p in (SAMPLES / "wiki").glob("*/sources/*.md")
    )


def test_sample_wiki_passes_provenance_lint():
    topic_dirs = [p for p in (SAMPLES / "wiki").iterdir() if p.is_dir()]
    assert topic_dirs, "samples/wiki has no topics"
    violations = []
    for topic in topic_dirs:
        violations += lint(topic, repo_root=SAMPLES)
        violations += okf_conformance(topic)
    assert violations == [], f"sample wiki has provenance/OKF violations: {violations}"


def test_sample_feed_matches_what_the_builder_produces():
    added = _sample_source_paths()
    expected = build_feed(
        added,
        lambda p: (SAMPLES / p).read_text(encoding="utf-8"),
        today="2026-06-05",
    )
    actual = json.loads((SAMPLES / "recap-feed.json").read_text())
    assert actual == expected


def test_sample_configs_parse_with_real_validators():
    from kb.config import AccountsConfig, TopicsConfig

    topics = TopicsConfig.load(SAMPLES / "config" / "topics.toml")
    assert topics.topics[0].name == "getting-started"

    accounts = AccountsConfig.load(SAMPLES / "config" / "accounts.toml")
    assert len(accounts.accounts) == 4
    assert all(a.label for a in accounts.accounts)
