"""Content-free LLM gateway shared by all configured stages."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

from .model_config import StageConfig


class ModelGatewayError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelResult:
    text: str
    requested_route: str
    requested_model: str
    resolved_model: str
    resolved_provider: str = ""

    def metadata(self) -> dict[str, str]:
        return {
            "model_route": self.requested_route,
            "model_requested": self.requested_model,
            "model_resolved": self.resolved_model,
            "model_provider": self.resolved_provider,
        }


def _url(stage: StageConfig) -> str:
    if stage.route == "openrouter":
        return "https://openrouter.ai/api/v1/chat/completions"
    if stage.provider == "openai":
        return "https://api.openai.com/v1/chat/completions"
    raise ModelGatewayError(
        f"{stage.name}: controlled gateway currently supports OpenAI-compatible direct providers only"
    )


def complete(
    stage: StageConfig,
    system: str,
    user: str,
    *,
    env: Mapping[str, str] | None = None,
    post: Any | None = None,
    max_tokens: int | None = None,
) -> ModelResult:
    runtime = os.environ if env is None else env
    key = runtime.get(stage.api_key_name, "").strip()
    if not key:
        raise ModelGatewayError(f"{stage.api_key_name} is required for {stage.name}")
    payload: dict[str, Any] = {
        "model": stage.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if stage.route == "openrouter":
        payload["models"] = list(stage.fallback_models)
        payload["provider"] = {
            "allow_fallbacks": stage.allow_provider_fallbacks,
            "data_collection": "allow",
        }
    request = urllib.request.Request(
        _url(stage),
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        if post is None:
            # The request URL is selected only by _url from a validated stage route.
            with urllib.request.urlopen(request, timeout=120) as response:  # nosec B310
                data = json.loads(response.read().decode())
        else:
            data = post(request)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200].strip()
        suffix = f": {detail}" if detail else ""
        raise ModelGatewayError(
            f"model request failed: HTTP {exc.code} {exc.reason}{suffix}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ModelGatewayError(f"model request failed: {exc}") from exc
    try:
        text = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ModelGatewayError("model response did not include text") from exc
    provider = str(
        data.get("provider") or data.get("openrouter_metadata", {}).get("provider") or ""
    )
    return ModelResult(
        text, stage.route, stage.model, str(data.get("model") or stage.model), provider
    )
