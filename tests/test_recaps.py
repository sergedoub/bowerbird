import datetime as dt
import json

from bowerbird.config import DeliveryTarget, RecapProfile
from bowerbird.model_config import ModelConfig
from bowerbird.recaps import (
    RecapWindow,
    build_model_prompt,
    build_recap_artifact,
    deterministic_body,
    load_source_notes,
    manifest_for,
    manifest_path,
    select_notes,
    validate_recap_files,
    window_for,
)


def _profile(**overrides):
    values = {
        "name": "ai-accounts-daily",
        "frequency": "daily",
        "prompt_path": "compile/recaps/default.md",
        "output_format": "slack_mrkdwn",
        "accounts": ("account_one",),
        "topics": (),
        "deliveries": (DeliveryTarget("slack", "#augur-updates"),),
        "weekly_due_day": "monday",
        "interval_hours": 1,
        "include_urls": False,
    }
    values.update(overrides)
    return RecapProfile(**values)


def test_daily_and_weekly_calendar_windows():
    daily = _profile(frequency="daily")
    assert window_for(daily, dt.date(2026, 6, 24)) == RecapWindow(
        start=dt.date(2026, 6, 23),
        end=dt.date(2026, 6, 24),
        label="2026-06-23",
    )

    weekly = _profile(
        name="marketing-weekly",
        frequency="weekly",
        accounts=(),
        topics=("marketing",),
        weekly_due_day="monday",
    )
    assert window_for(weekly, dt.date(2026, 6, 8)) == RecapWindow(
        start=dt.date(2026, 6, 1),
        end=dt.date(2026, 6, 8),
        label="2026-06-07",
    )
    assert window_for(weekly, dt.date(2026, 6, 9)) is None

    hourly = _profile(
        name="llm-wiki",
        frequency="hourly",
        accounts=(),
        topics=("llm-wiki",),
        interval_hours=4,
    )
    assert window_for(hourly, dt.datetime(2026, 6, 30, 9, 42, tzinfo=dt.UTC)) == RecapWindow(
        start=dt.datetime(2026, 6, 30, 8, 0, tzinfo=dt.UTC),
        end=dt.datetime(2026, 6, 30, 12, 0, tzinfo=dt.UTC),
        label="2026-06-30T08-00Z",
    )


def test_load_source_notes_and_selectors_split_accounts_from_topics():
    files = {
        "wiki/ai-updates/sources/2026-06-21-account-one.md": """---
date: 2026-06-21
mirror: accounts/account_one
---

Account One shipped a coding-agent update.
""",
        "wiki/marketing/sources/2026-06-21-positioning.md": """---
date: 2026-06-21
topic: marketing
---

Positioning note.
""",
    }
    notes = load_source_notes(list(files), files.__getitem__, account_labels={"account_one": "Account One"})
    account_profile = _profile(accounts=("account_one",), topics=())
    topic_profile = _profile(
        name="marketing-daily",
        accounts=(),
        topics=("marketing",),
        output_format="markdown",
    )

    selected_account = select_notes(account_profile, notes)
    selected_topic = select_notes(topic_profile, notes)

    assert [note.path for note in selected_account] == [
        "wiki/ai-updates/sources/2026-06-21-account-one.md"
    ]
    assert selected_account[0].label == "Account One"
    assert [note.path for note in selected_topic] == [
        "wiki/marketing/sources/2026-06-21-positioning.md"
    ]


def test_build_recap_artifact_frontmatter_and_manifest():
    profile = _profile()
    files = {
        "wiki/ai-updates/sources/2026-06-21-account-one.md": """---
date: 2026-06-21
mirror: accounts/account_one
---

Account One shipped a coding-agent update.
""",
    }
    notes = load_source_notes(list(files), files.__getitem__, account_labels={"account_one": "Account One"})
    artifact = build_recap_artifact(
        profile,
        notes,
        window=RecapWindow(dt.date(2026, 6, 21), dt.date(2026, 6, 22), "2026-06-21"),
        read_prompt=lambda _path: "Write a short recap.",
        synthesize=deterministic_body,
        model=ModelConfig(provider="openai", recap_model="gpt-5.4-mini"),
        generated_at="2026-06-22T00:00:00+00:00",
    )

    assert artifact is not None
    assert artifact.path == "recaps/ai-accounts-daily/2026-06-21.md"
    assert "type: Recap" in artifact.content
    assert 'profile: "ai-accounts-daily"' in artifact.content
    assert 'prompt_path: "compile/recaps/default.md"' in artifact.content
    assert '  - "wiki/ai-updates/sources/2026-06-21-account-one.md"' in artifact.content
    assert 'destination: "#augur-updates"' in artifact.content
    assert artifact.manifest_entry["deliveries"] == [
        {"type": "slack", "destination": "#augur-updates"}
    ]
    assert "*Knowledge Base - daily recap - 2026-06-21*" in artifact.content
    assert "*Account One:* Account One shipped a coding-agent update." in artifact.content
    assert "_1 new note | 1 account lane_" in artifact.content

    manifest = manifest_for(
        [artifact],
        run_date=dt.date(2026, 6, 22),
        generated_at="2026-06-22T00:00:00+00:00",
    )
    assert manifest["type"] == "RecapManifest"
    assert manifest["recaps"][0]["file"] == artifact.path
    assert manifest_path(dt.date(2026, 6, 22)) == "recaps/manifests/2026-06-22.json"


def test_model_prompt_uses_compact_lane_recap_contract():
    profile = _profile()
    files = {
        "wiki/ai-updates/sources/2026-06-21-account-one.md": """---
date: 2026-06-21
mirror: accounts/account_one
---

Account One shipped a coding-agent update.
""",
    }
    notes = load_source_notes(list(files), files.__getitem__, account_labels={"account_one": "Account One"})
    artifact = build_recap_artifact(
        profile,
        notes,
        window=RecapWindow(dt.date(2026, 6, 21), dt.date(2026, 6, 22), "2026-06-21"),
        read_prompt=lambda _path: "Write a short recap.",
        synthesize=lambda p, prompt, lanes, window: build_model_prompt(p, prompt, lanes, window)[1],
        model=ModelConfig(provider="openai"),
        generated_at="2026-06-22T00:00:00+00:00",
    )
    assert artifact is not None
    assert "Date label: 2026-06-21" in artifact.content
    assert "Total new source notes: 1" in artifact.content
    assert "Use one tight line per lane" in artifact.content
    assert "compact footer with total counts" in artifact.content
    assert "Do not include source citations or frontmatter." in artifact.content


def test_model_prompt_can_include_source_urls():
    profile = _profile(
        name="llm-wiki",
        accounts=(),
        topics=("llm-wiki",),
        include_urls=True,
    )
    files = {
        "wiki/llm-wiki/sources/2026-06-30-alice.md": """---
date: 2026-06-30
url: https://x.com/alice/status/100
topic: llm-wiki
---

Alice asked for LLM wiki examples.
""",
    }
    notes = load_source_notes(list(files), files.__getitem__)
    artifact = build_recap_artifact(
        profile,
        notes,
        window=RecapWindow(dt.date(2026, 6, 30), dt.date(2026, 7, 1), "2026-06-30"),
        read_prompt=lambda _path: "Include URLs.",
        synthesize=lambda p, prompt, lanes, window: build_model_prompt(p, prompt, lanes, window)[1],
        model=ModelConfig(provider="openai"),
        generated_at="2026-06-30T00:00:00+00:00",
    )
    assert artifact is not None
    assert "url=https://x.com/alice/status/100" in artifact.content


def test_validate_recap_files_checks_frontmatter_and_manifest(tmp_path):
    recap = tmp_path / "recaps" / "demo" / "2026-06-21.md"
    recap.parent.mkdir(parents=True)
    recap.write_text(
        """---
type: Recap
profile: demo
frequency: daily
format: markdown
window_start: 2026-06-21
window_end: 2026-06-22
generated_at: 2026-06-22T00:00:00+00:00
model_provider: openai
model: gpt-5.4-mini
prompt_path: compile/recaps/default.md
---

Body.
""",
        encoding="utf-8",
    )
    manifest = tmp_path / "recaps" / "manifests" / "2026-06-22.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"type": "RecapManifest", "recaps": []}), encoding="utf-8")
    assert validate_recap_files(tmp_path) == []

    recap.write_text("---\ntype: Note\n---\n\nBad.\n", encoding="utf-8")
    issues = validate_recap_files(tmp_path)
    assert any("expected 'Recap'" in issue or "missing frontmatter" in issue for issue in issues)
