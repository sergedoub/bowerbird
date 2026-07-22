#!/usr/bin/env python3
"""Execute a bounded, model-produced wiki write plan."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT / "src"))
from bowerbird.controlled_compile import CompileTools, apply_plan, build_compile_prompt
from bowerbird.llm_gateway import complete
from bowerbird.model_config import parse_model_config

def main() -> None:
    config = parse_model_config((ROOT / "config/models.toml").read_text())
    prompt = build_compile_prompt(ROOT)
    result = complete(config.compile, "You compile only the supplied Bowerbird scope.", prompt)
    apply_plan(CompileTools(ROOT), result.text)
    print("compile route=" + result.requested_route + " resolved=" + result.resolved_model)

if __name__ == "__main__": main()
