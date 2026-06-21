# Bowerbird Local Dashboard

Local management and recap UI for your Bowerbird instance. It holds no data of
its own: everything it shows comes from your GitHub repo, and every change it
makes is a commit there.

The dashboard is the second half of setup. The agent prepares secrets and
`web/.env.local`, then the dashboard lets you connect X, keep or replace the
four starter AI accounts, map bookmark folders, inspect health, and preview the
recap feed. It also connects Slack delivery by saving an incoming webhook as
the `SLACK_WEBHOOK_URL` repo secret and sending a test/current recap.

## Local Setup

From the repo root, create `web/.env.local` without printing secret values:

```bash
grep '^X_CLIENT_ID=' bin/.env >> web/.env.local
grep '^X_CLIENT_SECRET=' bin/.env >> web/.env.local
printf 'GITHUB_REPO=%s\n' '<owner/fork>' >> web/.env.local
printf 'GITHUB_TOKEN=%s\n' "$(gh auth token)" >> web/.env.local
printf 'APP_URL=http://bowerbird.localhost:3000\n' >> web/.env.local
printf 'OWNER_X_USERNAME=%s\n' '<your-x-handle>' >> web/.env.local
printf 'SESSION_SECRET=%s\n' "$(openssl rand -hex 32)" >> web/.env.local
```

Then run:

```bash
cd web
npm install
npm test
npm run dev        # http://bowerbird.localhost:3000
```

`bowerbird.localhost` is local-only and needs no setup: browsers resolve
`*.localhost` to your machine.

## Environment Variables

| Variable | Required for | Purpose |
| --- | --- | --- |
| `GITHUB_REPO` | everything | Your instance repo, `owner/name`. |
| `GITHUB_TOKEN` | everything | Token for that repo: contents read/write, actions read, secrets read/write. |
| `GITHUB_BRANCH` | — | Defaults to `main`. |
| `APP_URL` | sign-in | Local URL, usually `http://bowerbird.localhost:3000`. |
| `X_CLIENT_ID` | sign-in | Your X developer app's OAuth2 client id. |
| `X_CLIENT_SECRET` | — | Only for confidential X clients. |
| `OWNER_X_USERNAME` | sign-in | Your X handle — the only account allowed to sign in. |
| `SESSION_SECRET` | sign-in | Random string (16+ chars) signing the session cookie. |
| `SLACK_WEBHOOK_URL` | recap delivery | Slack incoming webhook if you run local web-cron delivery. The dashboard connector stores this as a repo secret for the built-in `slack-recap` workflow. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | recap delivery | Enables LLM synthesis of the recap; without a matching key a mechanical summary is sent. |
| `RECAP_PROVIDER` | — | Optional provider override: `openai`, `anthropic`, `gemini`, or `none`. |
| `RECAP_MODEL` | — | Model for synthesis. Defaults come from `config/models.toml` / the dashboard Models section. |
| `RECAP_QUIET_MESSAGE` | — | `true` posts a quiet note on zero-new days; default silent. |
| `CRON_SECRET` | — | Bearer token guarding `/api/cron/recap` when you call it manually or from a local scheduler. |

Each page/route tells you what's missing rather than failing silently.

## What The Dashboard Does

- **Connect X** seeds the pipeline's `X_TOKENS` GitHub Actions secret.
- **Homepage** manages monitored accounts and bookmark-folder mappings with one
  staged save.
- **Slack recap** saves a Slack incoming webhook as a repo secret and posts a
  test/current recap to the chosen channel.
- **Health** shows feed freshness and workflow state.
- **Recap** previews `compile/recap-feed.json`, including the starter demo feed
  when your fork still contains the public sample output.

Signing in with X is also how you recover when the X refresh token expires.
