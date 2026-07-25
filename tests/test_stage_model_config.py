import pytest

from bowerbird.model_config import ModelConfig, StageConfig, model_config_toml, parse_model_config


def test_stage_config_round_trip_and_openrouter_fallbacks():
    config = ModelConfig(
        StageConfig("compile", "openrouter", "openai/gpt-5", fallback_models=("anthropic/claude-sonnet",)),
        StageConfig("recap", "direct", "gpt-5-mini", "openai"),
    )
    assert parse_model_config(model_config_toml(config)) == config
    assert config.compile.api_key_name == "OPENROUTER_API_KEY"


def test_legacy_config_is_rejected():
    with pytest.raises(ValueError, match="legacy"):
        parse_model_config('[model]\nprovider = "openai"\n')
