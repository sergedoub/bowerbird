#!/usr/bin/env bash
# Compile using the explicit stage configured in config/models.toml.
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHONPATH=src python3 -m bowerbird.repo_boundary "compile raw into wiki" --repo-root "$ROOT"

NEW_RAW_COUNT="$(PYTHONPATH=src python3 bin/compile_manifest.py --count)"
echo "compile manifest: $NEW_RAW_COUNT uncompiled raw item(s)"
if [ "$NEW_RAW_COUNT" = "0" ]; then
  echo "No uncompiled raw items; skipping LLM compile."
  exit 0
fi

STAGE_ROUTE="$(PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
from bowerbird.model_config import parse_model_config
print(parse_model_config(Path("config/models.toml").read_text()).compile.route)
PY
)"
if [ "$STAGE_ROUTE" = "openrouter" ]; then
  PYTHONPATH=src python3 bin/controlled_compile.py
  exit 0
fi
if [ "$STAGE_ROUTE" != "direct" ]; then
  echo "unknown compile route '$STAGE_ROUTE'" >&2
  exit 64
fi

RUNNER="$(PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
from bowerbird.model_config import parse_model_config
print(parse_model_config(Path("config/models.toml").read_text()).compile.provider)
PY
)"
COMPILE_MODEL="$(PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
from bowerbird.model_config import parse_model_config
print(parse_model_config(Path("config/models.toml").read_text()).compile.model)
PY
)"
PROMPT="$(cat compile/PROMPT.md)$(PYTHONPATH=src python3 bin/compile_manifest.py --prompt)"

case "$RUNNER" in
  anthropic)
    command -v claude >/dev/null 2>&1 || npm install -g @anthropic-ai/claude-code
    CLAUDE_MODEL="${COMPILE_MODEL:-sonnet}"
    claude -p "$PROMPT" \
      --allowedTools "Read,Write,Edit,Bash,Glob,Grep" \
      --model "$CLAUDE_MODEL"
    ;;
  openai)
    command -v codex >/dev/null 2>&1 || npm install -g @openai/codex
    if [ -n "${OPENAI_API_KEY:-}" ]; then
      printenv OPENAI_API_KEY | codex login --with-api-key
    elif [ -n "${CODEX_ACCESS_TOKEN:-}" ]; then
      printenv CODEX_ACCESS_TOKEN | codex login --with-access-token
    fi
    CODEX_ARGS=(exec --dangerously-bypass-approvals-and-sandbox)
    if [ -n "$COMPILE_MODEL" ]; then
      CODEX_ARGS+=(-m "$COMPILE_MODEL")
    fi
    codex "${CODEX_ARGS[@]}" "$PROMPT"
    ;;
  gemini)
    command -v gemini >/dev/null 2>&1 || npm install -g @google/gemini-cli
    gemini --yolo -p "$PROMPT"
    ;;
  *)
    echo "unknown direct provider '$RUNNER' (expected: anthropic | openai | gemini)" >&2
    exit 64
    ;;
esac
