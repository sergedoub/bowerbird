# GitHub Actions

Five workflows live in `.github/workflows/`. Two are cron-triggered content pipelines, one is the LLM compile step, one writes the daily recap feed, and `ci.yml` runs the offline test suite + lint on code changes. The pipelines chain through `workflow_run` events because commits made with the default `GITHUB_TOKEN` do **not** fire `push` events (by design — GitHub avoids infinite loops).

## Workflow summary

| File | Trigger | Job |
|------|---------|-----|
| `pull.yml` | Daily cron `0 23 * * *` + manual | Runs `bin/pull.py` (all configured topics), persists rotated token to `X_TOKENS` via `GH_PAT`, commits new `raw/bookmarks/` files with `GITHUB_TOKEN`. Manual setup dispatch accepts `limit_per_folder=3`; full history requires explicit `import_all=true`. Scheduled runs require `BOWERBIRD_LIVE_INSTANCE=true` and use forward-only stop-at-existing behavior. |
| `account-dump.yml` | Daily cron `0 22 * * *` + manual | Runs `bin/dump_account.py --days ${DUMP_WINDOW_DAYS:-3}` for all configured accounts, or a targeted manual import with `handle`/`days` inputs. Scheduled runs require `BOWERBIRD_LIVE_INSTANCE=true`. Commits new `raw/accounts/` files with `GITHUB_TOKEN`. |
| `compile.yml` | `workflow_run` chained from **either** `pull-bookmarks` or `account-dump` (on success); `push` to `raw/**`; manual | Runs `bin/compile.sh` — installs and invokes the agent CLI selected by `config/models.toml` or the `COMPILE_RUNNER` repo variable (codex \| claude \| gemini) headlessly with `compile/PROMPT.md`, per the contract in `compile/INSTRUCTIONS.md`. Processes declared auto-compile raw namespaces. Runs `bin/lint.py` as guardrail. Commits `wiki/` updates. See `docs/compile-runners.md`. |
| `kb-recap-feed.yml` | Daily cron `30 0 * * *` + manual | Runs `bin/recap_feed.py`: writes `compile/recap-feed.json` from source notes added under `wiki/*/sources/` in the last 24 hours, grouped into account lanes and bookmark-folder topic lanes. |
| `ci.yml` | push/PR on code paths + manual | `pytest` (includes sample lint/feed checks) + `bin/lint.py`. |

## Chaining model

```
pull-bookmarks  ──┐
                  ├──▶ compile-wiki
account-dump    ──┘

kb-recap-feed ──▶ compile/recap-feed.json ──▶ connector agent ──▶ Slack
```

Either upstream pipeline completing successfully triggers `compile-wiki`. Workflows never post to Slack themselves — the once-daily recap is delivered by an external connector agent that consumes `compile/recap-feed.json`.

The compile job filters with `if: ${{ github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success' }}` — manual runs always fire; chained runs only fire on a green upstream.

The two scheduled import workflows also filter with `BOWERBIRD_LIVE_INSTANCE=true`.
Source repos carry the automation as product code, but only a live instance repo
should run paid, personal ingest jobs on a schedule. `bowerbird push-secrets`
and `bowerbird init` enable the variable once the required X/GitHub ingest
secrets are present.

## Recap feed lane grouping

The daily feed groups new source notes per lane:

- **Account lanes** — per account in `config/accounts.toml`: new source notes whose frontmatter `mirror: accounts/<handle>` matches the account.
- **Topic lanes** — per topic/bookmark folder: new source notes under `wiki/<topic>/sources/` that are *not* account-mirror sources (to avoid double-counting).

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

## Secrets

| Secret | Used by | Notes |
|--------|---------|-------|
| `X_TOKENS` | `pull.yml` | JSON dict containing OAuth2 user-context tokens. **Mutable** — `pull.py` rewrites it on every refresh via `GH_PAT`. |
| `X_BEARER_TOKEN` | `account-dump.yml` | Static app-only Bearer for the timeline endpoint. No rotation. |
| `GH_PAT` | `pull.yml` | Fine-grained PAT scoped to write the `X_TOKENS` repo secret. Required because `GITHUB_TOKEN` cannot write its own repo's secrets. |
| `OPENAI_API_KEY` | `compile.yml` | Credentials when the selected provider is Codex/OpenAI. |
| `CODEX_ACCESS_TOKEN` | `compile.yml` | Optional Enterprise Codex access token alternative. |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | `compile.yml` | Needed if the selected provider is Claude or Gemini. |
| `CLAUDE_CODE_OAUTH_TOKEN` | `compile.yml` | Legacy Claude Code credential; prefer `ANTHROPIC_API_KEY` for fresh setup. |

## Variables

| Variable | Used by | Notes |
|----------|---------|-------|
| `BOWERBIRD_LIVE_INSTANCE` | `pull.yml`, `account-dump.yml` | Set to `true` by setup after required ingest secrets exist. Missing/false means the repo is treated as source/template code: scheduled personal ingest jobs are skipped, while manual dispatch still works and fails clearly if secrets are absent. |
| `DUMP_WINDOW_DAYS` | `account-dump.yml` | Optional trailing window override; default is 3. |
| `X_USER_ID` | `pull.yml` | Optional numeric X user id; skips a `/users/me` lookup per pull run. |
| `COMPILE_RUNNER` / `COMPILE_MODEL` | `compile.yml` | Optional compile runner/model override; `config/models.toml` is preferred for fresh setup. |

## Operational gotchas

- A failed `pull.py` that fetched a new refresh token but crashed before persisting it **locks out future runs**. The workflow is structured so that persistence happens immediately after refresh; don't reorder.
- `compile.yml` has a `push:` trigger for `raw/**` so human/PAT-pushed notes and clips compile. GITHUB_TOKEN commits from upstream workflows still do not fire push events, so the X pipelines continue to chain through `workflow_run`.
- If `bin/lint.py` exits 1 inside compile, the LLM's commits do not ship and the workflow fails — read the run log to see which `Violation` kinds fired (`missing_frontmatter`, `uncited_concept`, `broken_link`, `missing_raw`).
- Renaming any workflow breaks the `workflow_run` chain (it matches by `workflows: ["pull-bookmarks"]` etc.). Update both the producer name and every consumer's `workflows:` array together.
- GitHub Actions never post Slack updates. If recap behavior changes, inspect the connector agent and `compile/recap-feed.json`, not the ingest or compile workflows.
