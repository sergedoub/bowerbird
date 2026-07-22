#!/usr/bin/env python3
"""Display the explicit stage routing configuration."""
from __future__ import annotations
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from bowerbird.model_config import parse_model_config

def main() -> None:
    path = ROOT / "config" / "models.toml"
    if not path.exists(): raise SystemExit("config/models.toml is required; run `bowerbird init`.")
    try: config = parse_model_config(path.read_text())
    except ValueError as exc: raise SystemExit(f"model config error: {exc}")
    for stage in (config.compile, config.recap):
        print(f"{stage.name}: route={stage.route} model={stage.model}")
        if stage.provider: print(f"  provider={stage.provider}")
        if stage.fallback_models: print("  fallbacks=" + ", ".join(stage.fallback_models))

if __name__ == "__main__": main()
