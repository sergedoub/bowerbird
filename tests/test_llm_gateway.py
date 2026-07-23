from __future__ import annotations

import io
import urllib.error

import pytest

from bowerbird.llm_gateway import ModelGatewayError, complete
from bowerbird.model_config import StageConfig


def test_complete_preserves_upstream_http_error_detail() -> None:
    stage = StageConfig("recap", "openrouter", "deepseek/deepseek-v4-flash")

    def fail(_request: object) -> object:
        raise urllib.error.HTTPError(
            "https://openrouter.ai/api/v1/chat/completions",
            402,
            "Payment Required",
            {},
            io.BytesIO(b'{"error":{"message":"Insufficient credits"}}'),
        )

    with pytest.raises(ModelGatewayError) as error:
        complete(stage, "system", "user", env={"OPENROUTER_API_KEY": "test"}, post=fail)

    assert "HTTP 402 Payment Required" in str(error.value)
    assert "Insufficient credits" in str(error.value)
