#!/usr/bin/env python3
"""View or update Bowerbird's model provider selection."""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from kb.model_config import (  # noqa: E402
    ModelConfig,
    PROVIDERS,
    detect_setup_provider,
    model_config_toml,
    parse_model_config,
    provider_for,
)

CONFIG_PATH = os.path.join(ROOT, "config", "models.toml")


def read_current() -> ModelConfig:
    if not os.path.exists(CONFIG_PATH):
        return ModelConfig(provider=detect_setup_provider())
    return parse_model_config(open(CONFIG_PATH).read())


def write_current(config: ModelConfig) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        f.write(model_config_toml(config))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=os.environ.get("BOWERBIRD_PROG", "bowerbird models"),
        description="Choose the model provider used by compile and recap automation.",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        help="provider to write to config/models.toml",
    )
    parser.add_argument("--compile-model", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--recap-model", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--model", default=None, help="optional model override used by compile and recap")
    parser.add_argument(
        "--write",
        action="store_true",
        help="write config/models.toml; without this, only display the resolved settings",
    )
    args = parser.parse_args()

    current = read_current()
    provider_key = provider_for(args.provider or current.provider).key
    provider = provider_for(provider_key)
    updated = ModelConfig(
        provider=provider.key,
        model=current.model if args.model is None else args.model,
        compile_model=current.compile_model if args.compile_model is None else args.compile_model,
        recap_model=(
            current.recap_model
            if args.recap_model is None
            else args.recap_model
        ),
    )
    if args.write:
        write_current(updated)

    action = "wrote" if args.write else "current"
    print(f"{action} model config:")
    print(f"  provider:       {provider.label} ({provider.key})")
    print(f"  compile runner: {provider.compile_runner}")
    print(f"  model override: {updated.model or '(provider default)'}")
    if updated.compile_model or updated.recap_model:
        print(f"  compile model:  {updated.compile_model or updated.model or '(provider default)'}")
        print(f"  recap model:    {updated.recap_model or updated.model or provider.default_model}")
    print(f"  API key secret: {provider.api_key_name}")
    print(f"  key page:       {provider.api_key_url}")
    print()
    print("providers:")
    for p in PROVIDERS.values():
        print(f"  {p.key:<9} {p.label:<20} secret={p.api_key_name}")


if __name__ == "__main__":
    main()
