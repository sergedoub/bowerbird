# Open-Source Checklist

This repo can be open sourced, but a personal instance may contain private
content, private automation details, and source-specific configuration. Review
these items before switching repository visibility.

## Keep

These parts are generally safe and useful to publish:

- `src/kb/`
- `bin/`
- `tests/`
- `compile/INSTRUCTIONS.md`
- `.github/workflows/*.yml`, after reviewing cron times and secrets
- Public setup docs under `docs/`
- Agent docs under `docs/agent/`, after removing private workspace identifiers

## Review Or Replace

These may be personal, sensitive, or too specific for a reusable public repo:

| Path | Decision |
| --- | --- |
| `raw/bookmarks/` | Publish only if the imported posts and your curation choices are meant to be public. Otherwise replace with sanitized demo raw files or remove before publishing. |
| `raw/accounts/` | Publish only if mirrored accounts and selected handles are intentional public examples. |
| `raw/books/` | Do not publish copyrighted or private source material unless you have the rights to do so. |
| `wiki/` | Publish if you want the compiled knowledge base public; otherwise replace with a sanitized demo wiki or remove before publishing. |
| `recaps/` | Publish only if generated recap bodies, source note paths, and destinations are safe. Otherwise replace with sanitized demo recap files or remove before publishing. |
| `config/*.toml` | Replace personal folder IDs, handles, recap destinations, and model choices with sanitized demo config if needed. |
| Personal automation docs | Remove or generalize anything referencing private workspaces, trigger IDs, or Slack channel IDs. |

## Secrets

Do not publish any of these values:

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_TOKENS`
- `X_BEARER_TOKEN`
- `GH_PAT`
- `CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`
- Slack bot tokens, webhook URLs, or connector-runtime service credentials

The repo ignores the local secret files:

```text
bin/.env
.env
*.x_tokens.json
bin/.x_tokens.json
```

Still check Git history before going public if secrets were ever committed.

## Suggested Public Shape

For a reusable open-source release, ship a runnable demo instance in the real
top-level paths: `config/`, `raw/`, `wiki/`, and `recaps/`. The demo content
should be synthetic or intentionally public. Avoid a separate sample tree:
duplicated layouts drift and make setup less clear.

## GitHub Actions Setup For Users

Document the required setup in the repository settings:

1. Enable GitHub Actions write permissions for commits.
2. Add the X and compile-runner secrets listed in [Importing from X](importing-x.md).
3. Adjust cron times in `.github/workflows/`.
4. Manually run `pull-bookmarks` and `account-dump`.
5. Confirm `compile-wiki` runs and `python3 bin/lint.py` passes.
6. Confirm `recap` writes `recaps/<profile>/<date>.md` and `recaps/manifests/<run-date>.json`.
7. Configure Slack from [connectors/slack](../connectors/slack/README.md):
   `SLACK_BOT_TOKEN` in Actions secrets, non-secret destinations in
   `config/recaps.toml`, and one verified bot post with a Slack timestamp.

## Public Positioning

The shortest useful description:

> A file-first personal knowledge-base pipeline that imports X bookmarks and
> selected X accounts, compiles them into a cited markdown wiki, and emits
> durable recap files for Slack and other delivery adapters.

The important distinction is that this is a provenance-preserving compile
pipeline, not a chatbot memory store.
