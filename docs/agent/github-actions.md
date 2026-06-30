# GitHub Actions

Six workflows live in `.github/workflows/`. Three are cron-triggered content
pipelines, one is the LLM compile step, one writes file-first recaps, and
`ci.yml` runs the offline test suite + lint on code, docs, and compile-contract
changes. The pipelines
chain through `workflow_run` events because commits made with the default
`GITHUB_TOKEN` do **not** fire `push` events (by design — GitHub avoids
infinite loops).

## Workflow summary

| File | Trigger | Job |
|------|---------|-----|
| `pull.yml` | Daily cron `0 23 * * *` + manual | Runs `bin/pull.py` (all configured topics), persists rotated token to `X_TOKENS` via `GH_PAT`, commits new `raw/bookmarks/` files with `GITHUB_TOKEN`. Manual setup dispatch accepts `limit_per_folder=3`; full history requires explicit `import_all=true`. Scheduled runs require `BOWERBIRD_LIVE_INSTANCE=true` and use forward-only stop-at-existing behavior. |
| `account-dump.yml` | Daily cron `0 22 * * *` + manual | Runs `bin/dump_account.py --days ${DUMP_WINDOW_DAYS:-3}` for all configured accounts, or a targeted manual import with `handle`/`days` inputs. Scheduled runs require `BOWERBIRD_LIVE_INSTANCE=true`. Commits new `raw/accounts/` files with `GITHUB_TOKEN`. |
| `search-dump.yml` | Every 4 hours `0 */4 * * *` + manual | Runs `bin/dump_search.py` for configured X Recent Search monitors in `config/searches.toml`. Uses `X_BEARER_TOKEN`, commits new `raw/searches/` files with `GITHUB_TOKEN`, and keeps per-monitor caps for cost control. Scheduled runs require `BOWERBIRD_LIVE_INSTANCE=true`. |
| `compile.yml` | `workflow_run` chained from `pull-bookmarks`, `account-dump`, or `search-dump` (on success); `push` to `raw/**`; manual | Runs `bin/compile.sh` — installs and invokes the agent CLI selected by `config/models.toml` or the `COMPILE_RUNNER` repo variable (codex \| claude \| gemini) headlessly with `compile/PROMPT.md`, per the contract in `compile/INSTRUCTIONS.md`. Processes declared auto-compile raw namespaces. Runs `bin/lint.py` as guardrail. Commits `wiki/` updates. See `docs/compile-runners.md`. |
| `recap.yml` | Daily cron `30 1 * * *`; `workflow_run` from `compile-wiki`; manual | Runs `bin/recap.py`: reads `config/recaps.toml`, generates due daily/hourly/weekly `recaps/<profile>/<label>.md` and `recaps/manifests/<run-label>.json`, commits only `recaps/`, then runs the bundled Slack adapter for manifest-listed Slack deliveries. |
| `ci.yml` | push/PR on code, docs, and compile-contract paths + manual | `pytest` + `bin/lint.py`. |

## Chaining model

```
pull-bookmarks  ──┐
                  ├──▶ compile-wiki
account-dump    ──┤
search-dump     ──┘

recap ──▶ recaps/<profile>/<label>.md
      └─▶ recaps/manifests/<run-label>.json ──▶ delivery adapters
```

Any upstream ingest pipeline completing successfully triggers `compile-wiki`.
`recap.yml` can run after a successful compile or on its own schedule. The
generation step writes files; delivery adapters consume the manifest. Slack
delivery runs after the commit, so a Slack failure marks delivery unhealthy
without removing the generated recap files.

Mutating workflows fail closed unless both conditions are true:

- `github.repository != 'sergedoub/bowerbird'`
- `BOWERBIRD_LIVE_INSTANCE=true`

That rule applies to manual dispatch as well as scheduled and chained runs.
For chained runs, the upstream import must also have succeeded. The public
source repo carries the workflow definitions as product code, but it must not
run personal ingest, compile, recap, or delivery jobs. `bowerbird push-secrets`
and `bowerbird init` enable the live-instance variable once the required
X/GitHub ingest secrets are present.

## Recap lane selection

Recap profiles select new source notes per lane:

- **Account lanes** — per account in `config/accounts.toml`: new source notes whose frontmatter `mirror: accounts/<handle>` matches the account.
- **Topic lanes** — per topic/bookmark folder: new source notes under `wiki/<topic>/sources/` that are *not* account-mirror sources (to avoid double-counting).

Concept and index file changes are deliberately not counted — they're compile
bookkeeping, not new claims. Prompt files live under `compile/recaps/`; generated
outputs live under `recaps/`.

## Concurrency

Each workflow uses a named concurrency group (`pull-bookmarks`, `account-dump`, `compile-wiki`, etc.) with `cancel-in-progress: false` so back-to-back runs queue rather than abort each other.

During setup, `compile-wiki` may spend several minutes in the model step. Watch
it by run id (`gh run list --workflow compile.yml --limit 5`, then
`gh run watch <run-id> --exit-status`) rather than treating a quiet step as a
stall. If two imports landed close together, an older compile can pass compile
and lint but fail at the final push because a newer raw commit already advanced
`main`; in that case, watch the queued newer compile before declaring a real
compile failure. Setup can do non-mutating prep while compile runs, but recap
or Slack verification should wait until a green compile commit is pulled
locally.

## Permissions

| Workflow | `contents` | other |
|----------|-----------|-------|
| `pull.yml` | `write` | — (uses `GH_PAT` separately for `X_TOKENS` secret writeback) |
| `account-dump.yml` | `write` | — |
| `search-dump.yml` | `write` | — |
| `compile.yml` | `write` | — |
| `recap.yml` | `write` | `SLACK_BOT_TOKEN` for bundled Slack delivery |

GitHub's default `GITHUB_TOKEN` cannot update repository secrets, so the
current public workflow uses `GH_PAT` for `X_TOKENS` writeback. For lower
setup-failure risk, future hardening should prefer a GitHub App installed on
the instance repo with `Secrets: write`; workflows can then generate short-lived
installation tokens programmatically instead of depending on a human-created
PAT.

## Secrets

| Secret | Used by | Notes |
|--------|---------|-------|
| `X_TOKENS` | `pull.yml` | JSON dict containing OAuth2 user-context tokens. **Mutable** — `pull.py` rewrites it on every refresh via `GH_PAT`. |
| `X_BEARER_TOKEN` | `account-dump.yml`, `search-dump.yml` | Static app-only Bearer for timeline and Recent Search endpoints. No rotation. |
| `GH_PAT` | `pull.yml` | Fine-grained PAT scoped to write the `X_TOKENS` repo secret. Required because `GITHUB_TOKEN` cannot write its own repo's secrets. |
| `OPENAI_API_KEY` | `compile.yml`, `recap.yml` | Credentials when the selected provider is Codex/OpenAI. |
| `CODEX_ACCESS_TOKEN` | `compile.yml` | Optional Enterprise Codex access token alternative. |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | `compile.yml`, `recap.yml` | Needed if the selected provider is Claude or Gemini. |
| `SLACK_BOT_TOKEN` | `recap.yml` | Bot User OAuth Token for the dedicated Bowerbird Slack app. Required when `config/recaps.toml` has Slack delivery targets. |
| `CLAUDE_CODE_OAUTH_TOKEN` | `compile.yml` | Legacy Claude Code credential; prefer `ANTHROPIC_API_KEY` for fresh setup. |

## Variables

| Variable | Used by | Notes |
|----------|---------|-------|
| `BOWERBIRD_LIVE_INSTANCE` | `pull.yml`, `account-dump.yml`, `search-dump.yml`, `compile.yml`, `recap.yml` | Set to `true` by setup after required ingest secrets exist. Missing/false means the repo is treated as source/template code: personal ingest, compile, and recap jobs are skipped, including manual dispatch. |
| `DUMP_WINDOW_DAYS` | `account-dump.yml` | Optional trailing window override; default is 3. |
| `X_USER_ID` | `pull.yml` | Optional numeric X user id; skips a `/users/me` lookup per pull run. |
| `COMPILE_RUNNER` / `COMPILE_MODEL` | `compile.yml` | Optional compile runner/model override; `config/models.toml` is preferred for fresh setup. |

## Operational gotchas

- A failed `pull.py` that fetched a new refresh token but crashed before persisting it **locks out future runs**. The workflow is structured so that persistence happens immediately after refresh; don't reorder.
- `compile.yml` has a `push:` trigger for `raw/**` so human/PAT-pushed notes and clips compile once `BOWERBIRD_LIVE_INSTANCE=true`. GITHUB_TOKEN commits from upstream workflows still do not fire push events, so the X pipelines continue to chain through `workflow_run`.
- If `bin/lint.py` exits 1 inside compile, the LLM's commits do not ship and the workflow fails — read the run log to see which `Violation` kinds fired (`missing_frontmatter`, `uncited_concept`, `broken_link`, `missing_raw`).
- Renaming any workflow breaks the `workflow_run` chain (it matches by `workflows: ["pull-bookmarks"]` etc.). Update both the producer name and every consumer's `workflows:` array together.
- GitHub Actions generate recap files. If Slack delivery changes, inspect the
  delivery adapter and `recaps/manifests/`, not the ingest or compile workflows.
