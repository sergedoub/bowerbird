"""Model provider configuration shared by setup, compile, and recap surfaces."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProvider:
    key: str
    label: str
    compile_runner: str
    api_key_name: str
    api_key_url: str
    default_model: str


PROVIDERS: dict[str, ModelProvider] = {
    "openai": ModelProvider(
        key="openai",
        label="OpenAI / Codex",
        compile_runner="codex",
        api_key_name="OPENAI_API_KEY",
        api_key_url="https://platform.openai.com/api-keys",
        default_model="gpt-5.4-mini",
    ),
    "anthropic": ModelProvider(
        key="anthropic",
        label="Anthropic / Claude",
        compile_runner="claude",
        api_key_name="ANTHROPIC_API_KEY",
        api_key_url="https://console.anthropic.com/settings/keys",
        default_model="claude-opus-4-8",
    ),
    "gemini": ModelProvider(
        key="gemini",
        label="Google Gemini",
        compile_runner="gemini",
        api_key_name="GEMINI_API_KEY",
        api_key_url="https://aistudio.google.com/app/apikey",
        default_model="gemini-2.5-flash",
    ),
}

ALIASES = {
    "codex": "openai",
    "openai": "openai",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "google": "gemini",
}


@dataclass(frozen=True)
class ModelConfig:
    provider: str = "openai"
    model: str = ""
    compile_model: str = ""
    recap_model: str = ""

    @property
    def compile_runner(self) -> str:
        return provider_for(self.provider).compile_runner

    @property
    def api_key_name(self) -> str:
        return provider_for(self.provider).api_key_name

    @property
    def compile_model_effective(self) -> str:
        return self.compile_model.strip() or self.model.strip()

    @property
    def recap_model_effective(self) -> str:
        return (
            self.recap_model.strip()
            or self.model.strip()
            or provider_for(self.provider).default_model
        )


def provider_for(value: str | None) -> ModelProvider:
    key = ALIASES.get((value or "").strip().lower(), "")
    if key not in PROVIDERS:
        raise ValueError(f"unknown model provider '{value}' (expected openai, anthropic, or gemini)")
    return PROVIDERS[key]


def detect_setup_provider(env: dict[str, str] | None = None) -> str:
    env = dict(os.environ if env is None else env)
    override = env.get("BOWERBIRD_MODEL_PROVIDER") or env.get("BOWERBIRD_SETUP_PROVIDER")
    if override:
        return provider_for(override).key
    if env.get("CODEX_HOME") or env.get("OPENAI_API_KEY"):
        return "openai"
    if env.get("ANTHROPIC_API_KEY") or env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return "anthropic"
    if env.get("GEMINI_API_KEY"):
        return "gemini"
    return "openai"


def parse_model_config(text: str) -> ModelConfig:
    if not text.strip():
        return ModelConfig()
    data = tomllib.loads(text)
    model_data = data.get("model", {})
    compile_data = data.get("compile", {})
    recap_data = data.get("recap", {})
    provider = provider_for(
        str(
            model_data.get("provider")
            or compile_data.get("provider")
            or recap_data.get("provider")
            or "openai"
        )
    ).key
    for section, section_data in (("compile", compile_data), ("recap", recap_data)):
        section_provider = section_data.get("provider")
        if section_provider and provider_for(str(section_provider)).key != provider:
            raise ValueError(f"{section} provider must match model provider in config/models.toml")
    return ModelConfig(
        provider=provider,
        model=str(model_data.get("model") or ""),
        compile_model=str(compile_data.get("model") or ""),
        recap_model=str(recap_data.get("model") or ""),
    )


def model_config_toml(config: ModelConfig) -> str:
    provider = provider_for(config.provider)
    model = config.model.strip()
    compile_model = config.compile_model.strip()
    recap_model = config.recap_model.strip()
    lines = [
        "# Model provider selection. Managed by `bowerbird models`, `bowerbird init`,",
        "# or by editing this file directly.",
        "",
        "[model]",
        f'provider = "{provider.key}"',
    ]
    if model:
        lines.append(f'model = "{model}"')
    if compile_model:
        lines += ["", "[compile]", f'model = "{compile_model}"']
    if recap_model:
        lines += ["", "[recap]", f'model = "{recap_model}"']
    lines.append("")
    return "\n".join(lines)
