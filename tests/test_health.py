import datetime as dt

from bowerbird.health import HealthCheck, LintStatus, report_to_text


def _write_valid_repo(root):
    (root / "config").mkdir()
    (root / "compile" / "recaps").mkdir(parents=True)
    (root / "config" / "topics.toml").write_text(
        '[topics.marketing]\nfolder_ids = ["123"]\n'
    )
    (root / "config" / "accounts.toml").write_text(
        '[[handles]]\nhandle = "account_one"\ntopic = "ai-updates"\n'
    )
    (root / "config" / "recaps.toml").write_text(
        '[[recaps]]\n'
        'name = "marketing-daily"\n'
        'frequency = "daily"\n'
        'topics = ["marketing"]\n'
        'prompt = "compile/recaps/default.md"\n'
        'format = "markdown"\n'
        '[[recaps.deliveries]]\n'
        'type = "slack"\n'
        'destination = "#updates"\n'
    )
    (root / "compile" / "recaps" / "default.md").write_text("Write a recap.\n")


def test_health_report_is_ok_for_valid_repo(tmp_path):
    _write_valid_repo(tmp_path)
    report = HealthCheck(stale_after_days=2).check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert report.ok
    assert report.issues == ()
    assert report.to_dict()["items"][2]["details"]["profiles"] == 1
    assert "OK    lint: provenance OK" in report_to_text(report)


def test_missing_config_is_error(tmp_path):
    (tmp_path / "compile" / "recaps").mkdir(parents=True)
    report = HealthCheck().check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert not report.ok
    assert any("config/topics.toml missing" in issue for issue in report.issues)
    assert any("config/accounts.toml missing" in issue for issue in report.issues)
    assert any("config/recaps.toml missing" in issue for issue in report.issues)


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
        '[[handles]]\nhandle = "account_one"\ntopic = "ai-updates"\noff_topic = "explode"\n'
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


def test_missing_recap_prompt_is_error(tmp_path):
    _write_valid_repo(tmp_path)
    (tmp_path / "compile" / "recaps" / "default.md").unlink()
    report = HealthCheck().check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert not report.ok
    assert report.issues == ("recap prompt file missing: compile/recaps/default.md",)


def test_invalid_recap_file_is_error(tmp_path):
    _write_valid_repo(tmp_path)
    (tmp_path / "recaps" / "demo").mkdir(parents=True)
    (tmp_path / "recaps" / "demo" / "2026-06-21.md").write_text(
        "---\ntype: Note\n---\n\nWrong type.\n"
    )
    report = HealthCheck().check(
        tmp_path,
        today=dt.date(2026, 6, 21),
        lint_status=LintStatus(0, "provenance OK"),
    )
    assert not report.ok
    assert any("missing frontmatter" in issue or "expected 'Recap'" in issue for issue in report.issues)
