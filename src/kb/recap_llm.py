"""Hosted model calls for recap body generation.

This module is deliberately small and stdlib-only. The recap pipeline can inject
`deterministic_body` in tests; production runs call this provider edge.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

from .model_config import ModelConfig, provider_for


class RecapModelError(RuntimeError):
    pass


def generate_recap_body(
    config: ModelConfig,
    system_prompt: str,
    user_prompt: str,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    provider = provider_for(config.provider)
    runtime_env = os.environ if env is None else env
    api_key = runtime_env.get(provider.api_key_name, "").strip()
    if not api_key:
        raise RecapModelError(f"{provider.api_key_name} is required for recap generation")

    if provider.key == "openai":
        return _openai(config, api_key, system_prompt, user_prompt)
    if provider.key == "anthropic":
        return _anthropic(config, api_key, system_prompt, user_prompt)
    if provider.key == "gemini":
        return _gemini(config, api_key, system_prompt, user_prompt)
    raise RecapModelError(f"unsupported recap model provider: {provider.key}")


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RecapModelError(f"model API error {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RecapModelError(f"model API request failed: {exc}") from exc


def _openai(config: ModelConfig, api_key: str, system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": config.recap_model_effective,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
        "max_output_tokens": 1200,
        "store": False,
    }
    data = _post_json(
        "https://api.openai.com/v1/responses",
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    text = data.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    parts: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                parts.append(content["text"])
    if parts:
        return "\n".join(parts).strip()
    raise RecapModelError("OpenAI response did not include output text")


def _anthropic(config: ModelConfig, api_key: str, system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": config.recap_model_effective,
        "max_tokens": 1200,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    parts = [
        item.get("text", "")
        for item in data.get("content", [])
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    text = "\n".join(part for part in parts if part).strip()
    if text:
        return text
    raise RecapModelError("Anthropic response did not include text content")


def _gemini(config: ModelConfig, api_key: str, system_prompt: str, user_prompt: str) -> str:
    model = config.recap_model_effective
    model_path = model if model.startswith("models/") else f"models/{model}"
    quoted_model = urllib.parse.quote(model_path, safe="/")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"{quoted_model}:generateContent?key={urllib.parse.quote(api_key)}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"maxOutputTokens": 1200},
    }
    data = _post_json(url, payload, {"Content-Type": "application/json"})
    parts: list[str] = []
    for candidate in data.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content", {})
        if not isinstance(content, dict):
            continue
        for part in content.get("parts", []):
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
    text = "\n".join(parts).strip()
    if text:
        return text
    raise RecapModelError("Gemini response did not include text content")
