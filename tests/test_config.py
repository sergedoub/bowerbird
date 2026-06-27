"""TopicsConfig + TopicRouter: validation and folder->topic routing."""
import pytest

from kb.config import AccountsConfig, BooksConfig, ConfigError, RecapsConfig, TopicsConfig
from kb.routing import TopicRouter


def test_loads_topics_and_maps_folders():
    cfg = TopicsConfig.from_dict(
        {"topics": {"marketing": {"folder_ids": ["1", "2"]}, "ios-dev": {"folder_ids": ["3"]}}}
    )
    assert cfg.folder_to_topic() == {"1": "marketing", "2": "marketing", "3": "ios-dev"}
    assert sorted(cfg.folder_ids()) == ["1", "2", "3"]


def test_topic_without_folders_is_an_error():
    with pytest.raises(ConfigError):
        TopicsConfig.from_dict({"topics": {"marketing": {"folder_ids": []}}})


def test_folder_in_two_topics_is_an_error():
    with pytest.raises(ConfigError):
        TopicsConfig.from_dict(
            {"topics": {"a": {"folder_ids": ["1"]}, "b": {"folder_ids": ["1"]}}}
        )


def test_router_maps_known_folder_and_drops_unsorted():
    cfg = TopicsConfig.from_dict({"topics": {"marketing": {"folder_ids": ["1"]}}})
    router = TopicRouter(cfg)
    assert router.route("1") == "marketing"
    assert router.route("999") is None      # folder not allowlisted
    assert router.route(None) is None       # unsorted -> not ingested (no classifier yet)


def test_router_uses_classifier_for_unsorted_when_provided():
    cfg = TopicsConfig.from_dict({"topics": {"marketing": {"folder_ids": ["1"]}}})
    router = TopicRouter(cfg, classifier=lambda text: "marketing" if "ads" in text else None)
    assert router.route(None, text="google ads tips") == "marketing"
    assert router.route(None, text="cat photos") is None


def test_accounts_config_normalizes_handles_and_carries_topic():
    cfg = AccountsConfig.from_dict({"handles": [
        {"handle": "account_one", "topic": "ai-updates"},
        {"handle": "@account_two", "topic": "research"},
    ]})
    assert [(a.handle, a.topic, a.off_topic) for a in cfg.accounts] == [
        ("account_one", "ai-updates", "skip"),   # default off_topic policy
        ("account_two", "research", "skip"),     # leading @ stripped
    ]


def test_accounts_config_respects_explicit_off_topic_policy():
    cfg = AccountsConfig.from_dict({"handles": [
        {"handle": "account_one", "topic": "ai-updates", "off_topic": "quarantine"},
    ]})
    assert cfg.accounts[0].off_topic == "quarantine"


def test_accounts_config_allows_no_accounts():
    assert AccountsConfig.from_dict({}).accounts == ()
    assert AccountsConfig.from_dict({"handles": []}).accounts == ()


def test_accounts_config_rejects_duplicates():
    with pytest.raises(ConfigError):
        # same account twice
        AccountsConfig.from_dict({"handles": [
            {"handle": "account_one", "topic": "ai-updates"},
            {"handle": "@account_one", "topic": "ai-updates"},
        ]})


def test_accounts_config_requires_topic():
    with pytest.raises(ConfigError):
        AccountsConfig.from_dict({"handles": [{"handle": "account_one"}]})


def test_accounts_config_rejects_unknown_off_topic_policy():
    with pytest.raises(ConfigError):
        AccountsConfig.from_dict({"handles": [
            {"handle": "account_one", "topic": "ai-updates", "off_topic": "explode"},
        ]})


def test_accounts_config_rejects_legacy_string_handles():
    """Legacy `handles = ["account_one"]` form no longer parses — explicit topic is now required."""
    with pytest.raises(ConfigError):
        AccountsConfig.from_dict({"handles": ["account_one"]})


def test_books_config_loads_books_and_gets_by_id():
    cfg = BooksConfig.from_dict({"books": [{
        "book_id": "never-split-the-difference",
        "topic": "negotiation",
        "title": "Never Split the Difference",
        "author": "Chris Voss",
        "published_date": "2016-05-16",
        "source_path": "~/Downloads/book.md",
    }]})
    book = cfg.get("never-split-the-difference")
    assert book.topic == "negotiation"
    assert book.provenance == "external-expert"


def test_books_config_rejects_missing_fields_bad_ids_and_duplicates():
    with pytest.raises(ConfigError):
        BooksConfig.from_dict({"books": []})
    with pytest.raises(ConfigError):
        BooksConfig.from_dict({"books": [{"book_id": "Bad ID"}]})
    with pytest.raises(ConfigError):
        BooksConfig.from_dict({"books": [
            {
                "book_id": "same",
                "topic": "a",
                "title": "A",
                "author": "A",
                "published_date": "2026-01-01",
                "source_path": "a.md",
            },
            {
                "book_id": "same",
                "topic": "b",
                "title": "B",
                "author": "B",
                "published_date": "2026-01-01",
                "source_path": "b.md",
            },
        ]})


def test_recaps_config_loads_profiles_selectors_and_deliveries():
    cfg = RecapsConfig.from_dict({"recaps": [{
        "name": "accounts-daily",
        "frequency": "daily",
        "accounts": ["@ACCOUNT_ONE", "account_two"],
        "prompt": "compile/recaps/default.md",
        "format": "slack_mrkdwn",
        "deliveries": [{"type": "slack", "destination": "#augur-updates"}],
    }]})
    profile = cfg.profiles[0]
    assert profile.name == "accounts-daily"
    assert profile.accounts == ("account_one", "account_two")
    assert profile.topics == ()
    assert profile.output_format == "slack_mrkdwn"
    assert profile.deliveries[0].kind == "slack"
    assert profile.deliveries[0].destination == "#augur-updates"


def test_recaps_config_supports_weekly_topic_profiles():
    cfg = RecapsConfig.from_dict({"recaps": [{
        "name": "marketing-weekly",
        "frequency": "weekly",
        "weekly_due_day": "friday",
        "topics": ["marketing"],
        "prompt": "compile/recaps/default.md",
        "format": "email_markdown",
    }]})
    profile = cfg.profiles[0]
    assert profile.frequency == "weekly"
    assert profile.weekly_due_day == "friday"
    assert profile.deliveries == ()


def test_recaps_config_rejects_bad_profiles():
    assert RecapsConfig.from_dict({}).profiles == ()
    with pytest.raises(ConfigError, match="lowercase slug"):
        RecapsConfig.from_dict({"recaps": [{
            "name": "Bad Profile",
            "frequency": "daily",
            "topics": ["marketing"],
            "prompt": "compile/recaps/default.md",
        }]})
    with pytest.raises(ConfigError, match="unknown frequency"):
        RecapsConfig.from_dict({"recaps": [{
            "name": "marketing",
            "frequency": "hourly",
            "topics": ["marketing"],
            "prompt": "compile/recaps/default.md",
        }]})
    with pytest.raises(ConfigError, match="compile/recaps"):
        RecapsConfig.from_dict({"recaps": [{
            "name": "marketing",
            "frequency": "daily",
            "topics": ["marketing"],
            "prompt": "compile/PROMPT.md",
        }]})
    with pytest.raises(ConfigError, match="at least one account or topic"):
        RecapsConfig.from_dict({"recaps": [{
            "name": "marketing",
            "frequency": "daily",
            "prompt": "compile/recaps/default.md",
        }]})
