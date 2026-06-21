import tomllib

import pytest

from kb.accounts import add_account_to_text, slug_topic
from kb.config import ConfigError


def test_add_account_to_empty_config():
    text, added = add_account_to_text("", "@guinnesschen", topic="codex", label="Guinness")

    assert added is True
    parsed = tomllib.loads(text)
    assert parsed["handles"] == [{
        "handle": "guinnesschen",
        "topic": "codex",
        "off_topic": "skip",
        "label": "Guinness",
    }]


def test_add_account_preserves_existing_rows_and_is_idempotent():
    original = """
[[handles]]
handle = "bcherny"
topic = "ai"
off_topic = "skip"
label = "Boris"
"""
    first, added = add_account_to_text(original, "guinnesschen", topic="codex")
    second, added_again = add_account_to_text(first, "@guinnesschen", topic="other")

    assert added is True
    assert added_again is False
    parsed = tomllib.loads(second)
    assert [row["handle"] for row in parsed["handles"]] == ["bcherny", "guinnesschen"]
    assert parsed["handles"][0]["label"] == "Boris"
    assert parsed["handles"][1]["topic"] == "codex"


def test_add_account_validates_input():
    with pytest.raises(ConfigError):
        add_account_to_text("", "")
    with pytest.raises(ConfigError):
        add_account_to_text("", "x", off_topic="explode")


def test_slug_topic_normalizes_handles():
    assert slug_topic("AI Research!") == "ai-research"
    assert slug_topic(" @Guinness Chen ") == "guinness-chen"
