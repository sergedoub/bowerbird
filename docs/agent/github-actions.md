# GitHub Actions

Six workflows live in `.github/workflows/`. Two are cron-triggered content pipelines, one is the LLM compile step, one writes the daily recap feed, one delivers that feed to Slack when configured, and `ci.yml` runs the offline test suite + lint on code changes. The pipelines chain through `workflow_run` events because commits made with the default `GITHUB_TOKEN` do **not** fire `push` events (by design — GitHub avoids infinite loops).

## Workflow summary

| File | Trigger | Job |
|------|---------|-----|
| `pull.yml` | Daily cron `0 23 * * *` + manual | Runs `bin/pull.py` (all configured topics), persists rotated token to `X_TOKENS` via `GH_PAT`, commits new `raw/bookmarks/` files with `GITHUB_TOKEN`. Manual setup dispatch accepts `limit_per_folder=3`; full history requires explicit `import_all=true`. Scheduled runs use forward-only stop-at-existing behavior. |
| `account-dump.yml` | Daily cron `0 22 * * *` + manual | Runs `bin/dump_account.py --days ${DUMP_WINDOW_DAYS:-3}` for all configured accounts, or a targeted manual import with `handle`/`days` inputs. Commits new `raw/accounts/` files with `GITHUB_TOKEN`. |
| `compile.yml` | `workflow_run` chained from **either** `pull-bookmarks` or `account-dump` (on success); `push` to `raw/**`; manual | Runs `bin/compile.sh` — installs and invokes the agent CLI selected by `config/models.toml` or the `COMPILE_RUNNER` repo variable (codex \| claude \| gemini) headlessly with `compile/PROMPT.md`, per the contract in `compile/INSTRUCTIONS.md`. Processes declared auto-compile raw namespaces. Runs `bin/lint.py` as guardrail. Commits `wiki/` updates. See `docs/compile-runners.md`. |
| `kb-recap-feed.yml` | Daily cron `30 0 * * *` + manual | Runs `bin/recap_feed.py`: writes `compile/recap-feed.json` from source notes added under `wiki/*/sources/` in the last 24 hours, grouped into account lanes and topic lanes. |
| `slack-recap.yml` | `workflow_run` chained from `kb-recap-feed` (on success) + manual | Runs `bin/slack_recap.py`: posts the fresh recap feed to Slack when `SLACK_WEBHOOK_URL` is configured; exits quietly when Slack is not connected. |
| `ci.yml` | push/PR on code paths + manual | `pytest` (includes sample lint/feed checks) + `bin/lint.py`. |

## Chaining model

```
pull-bookmarks  ──┐
                  ├──▶ compile-wiki
account-dump    ──┘

kb-recap-feed ──▶ compile/recap-feed.json ──▶ slack-recap
```

Either upstream pipeline completing successfully triggers `compile-wiki`. `kb-recap-feed` then computes the one-file delivery contract, and `slack-recap` posts it when the Slack connector has stored `SLACK_WEBHOOK_URL`. Hosted web app cron delivery via `/api/cron/recap` remains a compatible alternate consumer.

The compile job filters with `if: ${{ github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success' }}` — manual runs always fire; chained runs only fire on a green upstream.

## Recap feed lane grouping

The daily feed groups new source notes per lane:

- **Account lanes** — per account in `config/accounts.toml`: new source notes whose frontmatter `mirror: accounts/<handle>` matches the account.
- **Topic lanes** — per wiki topic: new source notes under `wiki/<topic>/sources/` that are *not* account-mirror sources (to avoid double-counting).

Concept and index file changes are deliberately not counted — they're compile bookkeeping, not new claims.

## Concurrency

Each workflow uses a named concurrency group (`pull-bookmarks`, `account-dump`, `compile-wiki`, etc.) with `cancel-in-progress: false` so back-to-back runs queue rather than abort each other.

## Permissions

| Workflow | `contents` | other |
|----------|-----------|-------|
| `pull.yml` | `write` | — (uses `GH_PAT` separately for `X_TOKENS` secret writeback) |
| `account-dump.yml` | `write` | — |
| `compile.yml` | `write` | — |
| `kb-recap-feed.yml` | `write` | — |
| `slack-recap.yml` | `read` | — |

## Secrets

| Secret | Used by | Notes |
|--------|---------|-------|
| `X_TOKENS` | `pull.yml` | JSON dict containing OAuth2 user-context tokens. **Mutable** — `pull.py` rewrites it on every refresh via `GH_PAT`. |
| `X_BEARER_TOKEN` | `account-dump.yml` | Static app-only Bearer for the timeline endpoint. No rotation. |
| `GH_PAT` | `pull.yml` | Fine-grained PAT scoped to write the `X_TOKENS` repo secret. Required because `GITHUB_TOKEN` cannot write its own repo's secrets. |
| `OPENAI_API_KEY` | `compile.yml`, web recap cron | Credentials when the selected provider is Codex/OpenAI. |
| `CODEX_ACCESS_TOKEN` | `compile.yml` | Optional Enterprise Codex access token alternative. |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | `compile.yml`, web recap cron | Needed if the selected provider is Claude or Gemini. |
| `CLAUDE_CODE_OAUTH_TOKEN` | `compile.yml` | Legacy Claude Code credential; prefer `ANTHROPIC_API_KEY` for fresh setup. |
| `SLACK_WEBHOOK_URL` | `slack-recap.yml`, web recap cron | Incoming webhook for the chosen Slack channel. Set by the dashboard Slack connector. |

## Operational gotchas

- A failed `pull.py` that fetched a new refresh token but crashed before persisting it **locks out future runs**. The workflow is structured so that persistence happens immediately after refresh; don't reorder.
- `compile.yml` has a `push:` trigger for `raw/**` so human/PAT-pushed notes and clips compile. GITHUB_TOKEN commits from upstream workflows still do not fire push events, so the X pipelines continue to chain through `workflow_run`.
- If `bin/lint.py` exits 1 inside compile, the LLM's commits do not ship and the workflow fails — read the run log to see which `Violation` kinds fired (`missing_frontmatter`, `uncited_concept`, `broken_link`, `missing_raw`).
- Renaming any workflow breaks the `workflow_run` chain (it matches by `workflows: ["pull-bookmarks"]` etc.). Update both the producer name and every consumer's `workflows:` array together.
- Slack delivery must stay a feed consumer. Do not make import or compile workflows post status messages; `slack-recap.yml` should only post the daily recap from `compile/recap-feed.json`.
