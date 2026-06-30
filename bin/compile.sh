#!/usr/bin/env bash
# Pluggable compile runner seam.
#
# The compile job is agent-agnostic: run a coding agent headlessly in the repo with
# compile/PROMPT.md as the task; the provenance linter (bin/lint.py) gates the result
# afterwards, regardless of which agent ran. COMPILE_RUNNER selects the agent:
#
#   codex    needs OPENAI_API_KEY in CI
#   claude   needs ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN
#   gemini   needs GEMINI_API_KEY
#
# Adding a runner = adding a case below that installs the CLI and invokes it headlessly
# with full file-edit permissions inside the checkout. See docs/compile-runners.md.
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHONPATH=src python3 -m bowerbird.repo_boundary "compile raw into wiki" --repo-root "$ROOT"

CONFIG_RUNNER="$(PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
try:
    from bowerbird.model_config import parse_model_config
    p = Path("config/models.toml")
    if p.exists():
        print(parse_model_config(p.read_text()).compile_runner)
except Exception:
    pass
PY
)"
CONFIG_MODEL="$(PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
try:
    from bowerbird.model_config import parse_model_config
    p = Path("config/models.toml")
    if p.exists():
        print(parse_model_config(p.read_text()).compile_model_effective)
except Exception:
    pass
PY
)"
RUNNER="${COMPILE_RUNNER:-$CONFIG_RUNNER}"
COMPILE_MODEL="${COMPILE_MODEL:-$CONFIG_MODEL}"
PROMPT="$(cat compile/PROMPT.md)"

if [ -z "$RUNNER" ]; then
  echo "no compile runner configured; run \`bowerbird models --provider <openai|anthropic|gemini> --write\` during setup" >&2
  exit 64
fi

echo "compile runner: $RUNNER"

case "$RUNNER" in
  claude)
    command -v claude >/dev/null 2>&1 || npm install -g @anthropic-ai/claude-code
    CLAUDE_MODEL="${COMPILE_MODEL:-sonnet}"
    claude -p "$PROMPT" \
      --allowedTools "Read,Write,Edit,Bash,Glob,Grep" \
      --model "$CLAUDE_MODEL"
    ;;
  codex)
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
    echo "unknown COMPILE_RUNNER '$RUNNER' (expected: claude | codex | gemini)" >&2
    exit 64
    ;;
esac
