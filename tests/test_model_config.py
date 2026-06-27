import pytest

from bowerbird.model_config import (
    ModelConfig,
    detect_setup_provider,
    model_config_toml,
    parse_model_config,
    provider_for,
)


def test_provider_aliases_and_detection_default_to_openai():
    assert provider_for("codex").key == "openai"
    assert provider_for("claude").key == "anthropic"
    assert detect_setup_provider({}) == "openai"
    assert detect_setup_provider({"CODEX_HOME": "/tmp/codex"}) == "openai"
    assert detect_setup_provider({"ANTHROPIC_API_KEY": "key"}) == "anthropic"


def test_model_config_round_trips():
    original = ModelConfig(provider="openai", model="gpt-5.4")
    parsed = parse_model_config(model_config_toml(original))
    assert parsed == original
    assert parsed.compile_runner == "codex"
    assert parsed.api_key_name == "OPENAI_API_KEY"
    assert parsed.compile_model_effective == "gpt-5.4"
    assert parsed.recap_model_effective == "gpt-5.4"


def test_parse_rejects_split_compile_and_recap_providers():
    with pytest.raises(ValueError, match="recap provider"):
        parse_model_config(
            """
[model]
provider = "openai"

[recap]
provider = "anthropic"
model = "claude-opus-4-8"
"""
        )
