import datetime as dt
import json

from kb.health import HealthCheck, LintStatus, report_to_text


def _write_valid_repo(root, generated="2026-06-21"):
    (root / "config").mkdir()
    (root / "compile").mkdir()
    (root / "config" / "topics.toml").write_text(
        '[topics.marketing]\nfolder_ids = ["123"]\n'
    )
    (root / "config" / "accounts.toml").write_text(
        '[[handles]]\nhandle = "bcherny"\ntopic = "claude-code"\n'
    )
    (root / "compile" / "recap-feed.json").write_text(json.dumps({
        "generated": generated,
        "window_hours": 24,
        "accounts": {},
        "topics": {},
        "summary": {"total_new": 3, "account_lanes": 1, "topic_lanes": 1},
    }))


def test_health_report_is_ok_for_valid_repo(tmp_path):
    _write_valid_repo(tmp_path)
    report = HealthCheck(stale_after_days=2).check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert report.ok
    assert report.issues == ()
    assert report.to_dict()["items"][2]["details"]["total_new"] == 3
    assert "OK    lint: provenance OK" in report_to_text(report)


def test_stale_feed_is_warning_not_error(tmp_path):
    _write_valid_repo(tmp_path, generated="2026-06-01")
    report = HealthCheck(stale_after_days=2).check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert report.ok
    assert any("20 day(s) old" in warning for warning in report.warnings)


def test_missing_config_is_error(tmp_path):
    (tmp_path / "compile").mkdir()
    (tmp_path / "compile" / "recap-feed.json").write_text(json.dumps({
        "generated": "2026-06-21",
        "summary": {"total_new": 0, "account_lanes": 0, "topic_lanes": 0},
    }))
    report = HealthCheck().check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert not report.ok
    assert any("config/topics.toml missing" in issue for issue in report.issues)
    assert any("config/accounts.toml missing" in issue for issue in report.issues)


def test_topics_use_canonical_validation(tmp_path):
    _write_valid_repo(tmp_path)
    (tmp_path / "config" / "topics.toml").write_text(
        '[topics.marketing]\nfolder_ids = ["123"]\n'
        '[topics.ai]\nfolder_ids = ["123"]\n'
    )
    report = HealthCheck().check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert not report.ok
    assert any("folder 123 is mapped to both" in issue for issue in report.issues)


def test_accounts_use_canonical_validation(tmp_path):
    _write_valid_repo(tmp_path)
    (tmp_path / "config" / "accounts.toml").write_text(
        '[[handles]]\nhandle = "bcherny"\ntopic = "claude-code"\noff_topic = "explode"\n'
    )
    report = HealthCheck().check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert not report.ok
    assert any("unknown off_topic policy" in issue for issue in report.issues)


def test_lint_failure_is_error(tmp_path):
    _write_valid_repo(tmp_path)
    report = HealthCheck().check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(1, "bad citation\nsecond line"),
    )
    assert not report.ok
    assert "bad citation" in report.issues[-1]


def test_invalid_recap_summary_is_error(tmp_path):
    _write_valid_repo(tmp_path)
    (tmp_path / "compile" / "recap-feed.json").write_text(json.dumps({
        "generated": "2026-06-21",
        "summary": {"total_new": "many", "account_lanes": 0, "topic_lanes": 1},
    }))
    report = HealthCheck().check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert not report.ok
    assert report.issues == ("compile/recap-feed.json has invalid summary counts",)
