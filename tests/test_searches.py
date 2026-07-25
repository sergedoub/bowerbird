"""Search-monitor config editing and TOML rendering."""
import pytest

from bowerbird.config import ConfigError
from bowerbird.searches import add_search, add_search_to_text, load_search_rows, render_searches_toml


def test_blank_and_empty_search_config_load_as_no_rows():
    assert load_search_rows("") == []
    assert load_search_rows("# no monitors yet\n") == []


def test_load_and_render_preserve_values_and_escape_strings():
    text = r'''
[[searches]]
name = "agents"
topic = "ai-updates"
query = '"agent" lang:en'
label = 'Agent \ research'
lookback_hours = 12
max_results = 25
max_pages = 2
'''
    rows = load_search_rows(text)
    assert rows == [{
        "name": "agents", "topic": "ai-updates", "query": '"agent" lang:en',
        "label": "Agent \\ research", "lookback_hours": 12,
        "max_results": 25, "max_pages": 2,
    }]

    rendered = render_searches_toml(rows)
    assert load_search_rows(rendered) == rows
    assert 'label = "Agent \\\\ research"' in rendered
    assert 'query = "\\\"agent\\\" lang:en"' in rendered


def test_load_rejects_non_array_tables_and_non_table_entries():
    with pytest.raises(ConfigError, match=r"\[\[searches\]\]"):
        load_search_rows('[searches]\nname = "wrong"\n')
    with pytest.raises(ConfigError, match="entry must be a table"):
        load_search_rows('searches = ["wrong"]\n')


def test_add_search_uses_defaults_and_is_idempotent():
    rendered, added = add_search_to_text(
        "", " daily-ai ", topic=" ai-updates ", query=" from:example ", label=" Daily AI "
    )
    assert added is True
    assert load_search_rows(rendered) == [{
        "name": "daily-ai", "topic": "ai-updates", "query": "from:example",
        "label": "Daily AI", "lookback_hours": 24, "max_results": 10, "max_pages": 1,
    }]

    unchanged, added_again = add_search_to_text(
        rendered, "daily-ai", topic="other", query="different"
    )
    assert added_again is False
    assert load_search_rows(unchanged) == load_search_rows(rendered)


def test_add_search_validates_before_writing():
    with pytest.raises(ConfigError):
        add_search_to_text("", "bad name", topic="ai-updates", query="x")


def test_add_search_creates_parent_and_round_trips_file(tmp_path):
    path = tmp_path / "config" / "searches.toml"
    added, name = add_search(
        path, "papers", topic="research", query="paper lang:en", label="", max_results=20
    )
    assert (added, name) == (True, "papers")
    assert load_search_rows(path.read_text()) == [{
        "name": "papers", "topic": "research", "query": "paper lang:en",
        "lookback_hours": 24, "max_results": 20, "max_pages": 1,
    }]
