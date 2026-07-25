"""Stage-oriented LLM routing configuration.

This intentionally replaces the former global provider configuration.  A stage is
always explicit: it either calls a direct provider or OpenRouter.
"""

from __future__ import annotations

import tomllib
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProvider:
    key: str
    label: str
    api_key_name: str
    api_key_url: str
    default_model: str


PROVIDERS = {
    "openai": ModelProvider(
        "openai", "OpenAI", "OPENAI_API_KEY", "https://platform.openai.com/api-keys", "gpt-5.4-mini"
    ),
    "anthropic": ModelProvider(
        "anthropic",
        "Anthropic",
        "ANTHROPIC_API_KEY",
        "https://console.anthropic.com/settings/keys",
        "claude-opus-4-8",
    ),
    "gemini": ModelProvider(
        "gemini",
        "Google Gemini",
        "GEMINI_API_KEY",
        "https://aistudio.google.com/app/apikey",
        "gemini-2.5-flash",
    ),
}
ALIASES = {
    "codex": "openai",
    "claude": "anthropic",
    "google": "gemini",
    **{key: key for key in PROVIDERS},
}
OPENROUTER_KEY = "OPENROUTER_API_KEY"


def provider_for(value: str) -> ModelProvider:
    key = ALIASES.get(value.strip().lower(), "")
    if key not in PROVIDERS:
        raise ValueError(
            f"unknown direct provider '{value}' (expected openai, anthropic, or gemini)"
        )
    return PROVIDERS[key]


@dataclass(frozen=True)
class StageConfig:
    name: str
    route: str
    model: str
    provider: str = ""
    fallback_models: tuple[str, ...] = ()
    allow_provider_fallbacks: bool = True

    def __post_init__(self) -> None:
        if self.route not in ("direct", "openrouter"):
            raise ValueError(f"{self.name}: route must be direct or openrouter")
        if not self.model.strip():
            raise ValueError(f"{self.name}: model is required")
        if self.route == "direct":
            if not self.provider:
                raise ValueError(f"{self.name}: direct route requires provider")
            provider_for(self.provider)
            if self.fallback_models:
                raise ValueError(f"{self.name}: fallback_models require the openrouter route")
        elif self.provider:
            raise ValueError(f"{self.name}: openrouter route must not set provider")

    @property
    def api_key_name(self) -> str:
        return (
            OPENROUTER_KEY
            if self.route == "openrouter"
            else provider_for(self.provider).api_key_name
        )


@dataclass(frozen=True, init=False)
class ModelConfig:
    compile: StageConfig
    recap: StageConfig

    def __init__(
        self,
        compile: StageConfig | None = None,
        recap: StageConfig | None = None,
        *,
        provider: str = "openai",
        model: str = "",
        compile_model: str = "",
        recap_model: str = "",
    ) -> None:
        # Constructor compatibility is intentionally kept for in-process callers;
        # the persisted TOML format remains breaking and stage-oriented.
        direct = provider_for(provider)
        object.__setattr__(
            self,
            "compile",
            compile
            or StageConfig(
                "compile", "direct", compile_model or model or direct.default_model, direct.key
            ),
        )
        object.__setattr__(
            self,
            "recap",
            recap
            or StageConfig(
                "recap", "direct", recap_model or model or direct.default_model, direct.key
            ),
        )

    def stage(self, name: str) -> StageConfig:
        if name == "compile":
            return self.compile
        if name == "recap":
            return self.recap
        raise ValueError(f"unknown LLM stage '{name}'")

    # Compatibility for recap artifact rendering; these describe its configured,
    # not resolved, route.  Runtime metadata records the resolved selection.
    @property
    def provider(self) -> str:
        return self.recap.route if self.recap.route == "openrouter" else self.recap.provider

    @property
    def recap_model_effective(self) -> str:
        return self.recap.model

    @property
    def compile_model_effective(self) -> str:
        return self.compile.model

    @property
    def api_key_name(self) -> str:
        return self.recap.api_key_name


def default_model_config(provider: str = "openai") -> ModelConfig:
    direct = provider_for(provider)
    return ModelConfig(
        StageConfig("compile", "direct", direct.default_model, direct.key),
        StageConfig("recap", "direct", direct.default_model, direct.key),
    )


def detect_setup_provider(env: dict[str, str] | None = None) -> str:
    values = os.environ if env is None else env
    if values.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if values.get("GEMINI_API_KEY"):
        return "gemini"
    return "openai"


def _stage(name: str, data: object) -> StageConfig:
    if not isinstance(data, dict):
        raise ValueError(f"stages.{name} is required")
    route = str(data.get("route") or "")
    provider = str(data.get("provider") or "")
    model = str(data.get("model") or "")
    fallbacks = data.get("fallback_models", [])
    if not isinstance(fallbacks, list) or not all(
        isinstance(value, str) and value.strip() for value in fallbacks
    ):
        raise ValueError(f"stages.{name}.fallback_models must be a list of model ids")
    enabled = data.get("allow_provider_fallbacks", True)
    if not isinstance(enabled, bool):
        raise ValueError(f"stages.{name}.allow_provider_fallbacks must be boolean")
    return StageConfig(name, route, model, provider, tuple(fallbacks), enabled)


def parse_model_config(text: str) -> ModelConfig:
    data = tomllib.loads(text)
    stages = data.get("stages")
    if not isinstance(stages, dict):
        raise ValueError(
            "config/models.toml must use [stages.compile] and [stages.recap]; legacy [model] config is unsupported"
        )
    return ModelConfig(
        _stage("compile", stages.get("compile")), _stage("recap", stages.get("recap"))
    )


def model_config_toml(config: ModelConfig) -> str:
    lines = ["# LLM routing. Every stage is explicit; managed by `bowerbird models`.", ""]
    for stage in (config.compile, config.recap):
        lines += [f"[stages.{stage.name}]", f'route = "{stage.route}"']
        if stage.provider:
            lines.append(f'provider = "{stage.provider}"')
        lines.append(f'model = "{stage.model}"')
        if stage.route == "openrouter":
            rendered = ", ".join(f'"{value}"' for value in stage.fallback_models)
            lines += [
                f"fallback_models = [{rendered}]",
                f"allow_provider_fallbacks = {str(stage.allow_provider_fallbacks).lower()}",
            ]
        lines.append("")
    return "\n".join(lines)
