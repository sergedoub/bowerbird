# Compile Runners

The compile step — the LLM that turns `raw/` files into `wiki/` notes — is
pluggable. The job it performs is agent-agnostic:

1. Run a coding agent headlessly inside the repo checkout.
2. Give it `compile/PROMPT.md` as the task (which points at the full contract
   in `compile/INSTRUCTIONS.md`).
3. The agent reads new raw files, writes wiki source notes and concept
   articles, and leaves its edits in the working tree.
4. `bin/lint.py` gates the result: the commit only ships if every claim cites
   a source and every link resolves — no matter which agent ran.

## Choosing a runner

Use `bowerbird models` or edit `config/models.toml` to write the provider
selection, then push the matching API key as a repository secret.
Setup should pick the provider that matches the active setup agent unless the
user chooses otherwise. No workflow edit is needed.

| Runner | CLI | Credentials (repo secrets) | Support level |
| --- | --- | --- | --- |
| `codex` | `@openai/codex` | `OPENAI_API_KEY` (`CODEX_ACCESS_TOKEN` for Enterprise automation) | Use when setup is run from Codex/OpenAI |
| `claude` | `@anthropic-ai/claude-code` | `ANTHROPIC_API_KEY` (`CLAUDE_CODE_OAUTH_TOKEN` remains a legacy option) | Tested, dogfooded |
| `gemini` | `@google/gemini-cli` | `GEMINI_API_KEY` | Best-effort smoke-tested |

"Best-effort" means the seam is verified to complete a compile and pass lint;
output *quality* (how well the agent follows the editorial contract in
`compile/INSTRUCTIONS.md`) varies by provider.
The linter guarantees provenance integrity for all runners; it cannot
guarantee prose quality.

For Codex in CI, `bin/compile.sh` signs the CLI in non-interactively before
`codex exec`: `OPENAI_API_KEY` is piped to `codex login --with-api-key`, or
`CODEX_ACCESS_TOKEN` is piped to `codex login --with-access-token`.

## Local smoke test

Run a compile on your machine with whichever CLI you have installed:

```bash
bowerbird models --provider openai --write
bash bin/compile.sh && python3 bin/lint.py
```

A passing smoke test = the agent terminated, the working tree contains new or
updated `wiki/` files for any uncompiled raw items, and lint prints
`provenance and recaps OK`.

## Adding a runner

`bin/compile.sh` is the seam. A new runner is one `case` branch that:

1. Installs the agent CLI if absent.
2. Invokes it headlessly (non-interactive, auto-approved file edits — the
   checkout is the sandbox) with `compile/PROMPT.md` as the prompt.
3. Exits non-zero on agent failure so the workflow fails before the lint gate.

Pass credentials through `.github/workflows/compile.yml` env (add your secret
name there). Please include a smoke-test transcript in the PR: a run of the
local command above against the seeded demo data, ending in
`provenance and recaps OK`.
