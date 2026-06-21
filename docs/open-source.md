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
| `raw/bookmarks/` | Publish only if the imported posts and your curation choices are meant to be public. Otherwise replace with `samples/raw/`. |
| `raw/accounts/` | Publish only if mirrored accounts and selected handles are intentional public examples. |
| `raw/books/` | Do not publish copyrighted or private source material unless you have the rights to do so. |
| `wiki/` | Publish if you want the compiled knowledge base public; otherwise replace with `samples/wiki/`. |
| `compile/recap-feed.json` | Safe only if its note text and paths are safe. Otherwise replace with `samples/recap-feed.json`. |
| `config/*.toml` | Replace personal folder IDs and handles with `samples/config/` if needed. |
| `docs/reviews/` | Review for personal operational history before publishing. |
| Personal automation docs | Remove or generalize anything referencing private workspaces, trigger IDs, or Slack channel IDs. |

## Secrets

Do not publish any of these values:

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_TOKENS`
- `X_BEARER_TOKEN`
- `GH_PAT`
- `CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`
- Slack bot tokens or webhook URLs
- Web app deploy secrets (`SESSION_SECRET`, `CRON_SECRET`, `GITHUB_TOKEN`)

The repo ignores the local secret files:

```text
bin/.env
.env
*.x_tokens.json
bin/.x_tokens.json
```

Still check Git history before going public if secrets were ever committed.

## Suggested Public Shape

For a reusable open-source release, ship the `samples/` tree in place of your
personal data (`samples/README.md` documents the copy-into-place step), and
either keep personal config/data out of the public branch or document that the
repository intentionally includes your live personal knowledge base.

## GitHub Actions Setup For Users

Document the required setup in the repository settings:

1. Enable GitHub Actions write permissions for commits.
2. Add the X and Claude secrets listed in [Importing from X](importing-x.md).
3. Adjust cron times in `.github/workflows/`.
4. Manually run `pull-bookmarks` with `limit_per_folder=3`, then run `account-dump`.
   For a single account smoke, dispatch `account-dump` with `handle=<handle>` and `days=3`.
5. Confirm `compile-wiki` runs and `python3 bin/lint.py` passes.
6. Confirm `kb-recap-feed` writes a fresh `compile/recap-feed.json`.
7. Configure exactly one Slack delivery path from [Daily Slack recap](slack-recap.md).

## Public Positioning

The shortest useful description:

> A file-first personal knowledge-base pipeline that imports X bookmarks and
> selected X accounts, compiles them into a cited markdown wiki, and emits a
> daily recap feed for Slack.

The important distinction is that this is a provenance-preserving compile
pipeline, not a chatbot memory store.
