import pytest

from bowerbird.repo_boundary import (
    BoundaryError,
    SOURCE_REPOSITORY,
    is_source_repository,
    normalize_repository,
    require_instance_repository,
)


def test_normalize_repository_accepts_github_urls():
    assert normalize_repository("https://github.com/SergeDoub/bowerbird.git") == SOURCE_REPOSITORY
    assert normalize_repository("git@github.com:sergedoub/bowerbird-serge.git") == (
        "sergedoub/bowerbird-serge"
    )
    assert normalize_repository("sergedoub/bowerbird-serge") == "sergedoub/bowerbird-serge"


def test_source_repository_detection():
    assert is_source_repository("https://github.com/sergedoub/bowerbird.git")
    assert not is_source_repository("https://github.com/sergedoub/bowerbird-serge.git")


def test_require_instance_repository_rejects_source_repo(tmp_path):
    with pytest.raises(BoundaryError, match="public source repo"):
        require_instance_repository(tmp_path, "compile", explicit_repo=SOURCE_REPOSITORY)


def test_require_instance_repository_allows_instance_repo(tmp_path):
    repo = require_instance_repository(
        tmp_path,
        "compile",
        explicit_repo="https://github.com/sergedoub/bowerbird-serge.git",
    )

    assert repo == "sergedoub/bowerbird-serge"


def test_require_instance_repository_fails_closed_without_identity(tmp_path):
    with pytest.raises(BoundaryError, match="could not resolve"):
        require_instance_repository(tmp_path, "compile", env={})
