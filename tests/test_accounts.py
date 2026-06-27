import tomllib

import pytest

from bowerbird.accounts import add_account_to_text, slug_topic
from bowerbird.config import ConfigError


def test_add_account_to_empty_config():
    text, added = add_account_to_text("", "@account_two", topic="codex", label="Guinness")

    assert added is True
    parsed = tomllib.loads(text)
    assert parsed["handles"] == [{
        "handle": "account_two",
        "topic": "codex",
        "off_topic": "skip",
        "label": "Guinness",
    }]


def test_add_account_preserves_existing_rows_and_is_idempotent():
    original = """
[[handles]]
handle = "account_one"
topic = "ai"
off_topic = "skip"
label = "Account One"
"""
    first, added = add_account_to_text(original, "account_two", topic="codex")
    second, added_again = add_account_to_text(first, "@account_two", topic="other")

    assert added is True
    assert added_again is False
    parsed = tomllib.loads(second)
    assert [row["handle"] for row in parsed["handles"]] == ["account_one", "account_two"]
    assert parsed["handles"][0]["label"] == "Account One"
    assert parsed["handles"][1]["topic"] == "codex"


def test_add_account_validates_input():
    with pytest.raises(ConfigError):
        add_account_to_text("", "")
    with pytest.raises(ConfigError):
        add_account_to_text("", "x", off_topic="explode")


def test_slug_topic_normalizes_handles():
    assert slug_topic("AI Research!") == "ai-research"
    assert slug_topic(" @Guinness Chen ") == "guinness-chen"
