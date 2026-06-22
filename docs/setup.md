# Setup Guide

From fork to a working instance: bookmarks flowing in daily, a compiled wiki,
and a recap in Slack. Expect 30–45 minutes, most of it on the X developer
portal.

> Using a coding agent? Two zero-effort paths: already cloned — run the
> repo's guided setup skill; not cloned yet — paste the prompt from
> [docs/setup-prompt.md](setup-prompt.md) into an agent session anywhere.

## 0. Prerequisites

- A GitHub account and a fork of this repository (your fork is your knowledge
  base — data commits land in it daily).
- Python 3.11+ locally.
- An **X developer app** with pay-as-you-go billing enabled
  (<https://developer.x.com/en/portal/dashboard>). This is the one step nothing
  can fully automate (X has no app-provisioning API) — see the
  [appendix](#appendix-the-x-developer-app-click-by-click) for the
  click-by-click. Create a **new app dedicated to Bowerbird** (even if you
  have others): separate credentials you can revoke independently, and its
  own usage line on your X bill. You need:
  - OAuth 2.0 user authentication set up, redirect URI
    `http://bowerbird.localhost:8080/callback`, scopes
    `bookmark.read tweet.read users.read offline.access`;
  - the OAuth2 **client id** (and secret, for confidential clients);
  - the app-only **bearer token**.
- LLM credentials for the compile. Setup should default to the active setup
  agent's provider: OpenAI/Codex when setup is run from Codex,
  Anthropic/Claude when setup is run from Claude, or Gemini if selected. Hosted
  GitHub Actions need a provider API key; a local app subscription is not enough
  for CI. See [compile runners](compile-runners.md).
- Optional but recommended: the [`gh` CLI](https://cli.github.com), logged in —
  the wizard then sets your Actions secrets for you.

## 1. Run the wizard

```bash
git clone https://github.com/<you>/<your-fork>.git && cd <your-fork>
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -e '.[dev]'
bowerbird init
```

(The virtualenv matters: modern macOS/Linux Pythons are "externally managed"
and reject bare `pip install` outside one.)

The wizard collects credentials into a gitignored `bin/.env`, opens the X
OAuth flow in your browser, lists your bookmark folders so you can choose
which ones Bowerbird watches (anything you bookmark into a watched folder
becomes part of your knowledge base), asks which accounts to follow, writes
`config/topics.toml` and `config/accounts.toml`, and pushes the GitHub
Actions secrets. If `gh` is absent, it prints the secret names you still need
to set manually; values stay in `bin/.env` and `bin/.x_tokens.json`. It ends
with a checklist of anything left.

The one secret you must mint by hand is `GH_PAT`: a fine-grained personal
access token that can write this repo's secrets
(<https://github.com/settings/personal-access-tokens/new>; repository
permission "Secrets: read and write"). The pipeline uses it to persist the
rotating X token after each run.

Agent-native alternative to the wizard: each wizard sub-step also exists as
its own non-interactive command, so a coding agent can run the whole setup
from chat — `bowerbird auth` (browser OAuth, no terminal input),
`bowerbird folders` (list folders for mapping), write the config TOMLs
directly, then `bowerbird push-secrets` (pushes everything staged in
`bin/.env` plus the token file to Actions secrets without printing a value).
Stage one compile credential for the provider you plan to use:
`OPENAI_API_KEY` for `codex`, `ANTHROPIC_API_KEY` for `claude`, or
`GEMINI_API_KEY` for `gemini`. `bowerbird models --provider <provider> --write`
records the provider in `config/models.toml`; no workflow edit is needed.

## 2. Commit config and enable Actions

```bash
git add config && git commit -m "config: my topics and accounts" && git push
```

On GitHub: **Actions tab → enable workflows**. Then dispatch `pull-bookmarks`
once with `limit_per_folder=3` and `account-dump` once manually (Run workflow).
Green runs mean raw posts are landing in `raw/`; the `compile-wiki` workflow
chains automatically and writes `wiki/`, gated by the provenance linter.

That first bookmark import is intentionally capped. Normal scheduled bookmark
pulls are forward-only: they read newest-first and stop when they hit an
already-ingested bookmark. If you explicitly want full folder history later,
first run `bowerbird folders --counts` for a count/cost estimate, then dispatch
`pull-bookmarks` with `import_all=true`.

Verify locally any time:

```bash
bowerbird pull          # should print written/skipped counts and search_mode
bowerbird lint          # must print: provenance OK
bowerbird doctor        # config, recap feed, and lint health
```

## 3. Recap delivery

The `kb-recap-feed` workflow writes `compile/recap-feed.json` daily — the
machine-readable "what's new" feed. To get it in Slack, configure the
[Slack connector](../connectors/slack/README.md). The connector agent reads
that feed, checks freshness, synthesizes one recap, and sends it to the
channel or DM you choose.

## 4. Check health

Run the text-first health command any time:

```bash
bowerbird doctor
bowerbird doctor --json
```

It reports config presence, recap-feed validity and freshness, and the local
provenance lint result. For X token recovery, run `bowerbird auth`, then
`bowerbird push-secrets` to update the `X_TOKENS` Actions secret.

## 5. Customization

| What | Where |
| --- | --- |
| Compile agent (claude / codex / gemini) | `COMPILE_RUNNER` repository variable |
| Account-mirror window | `DUMP_WINDOW_DAYS` repository variable |
| Live-instance scheduled ingest | `BOWERBIRD_LIVE_INSTANCE=true`, set by setup after required ingest secrets exist |
| Cron times | Workflow files — the one accepted fork edit, see [upgrading](upgrading.md) |
| Recap labels per account | `label` field in `config/accounts.toml` |
| Recap delivery | Connector agent configuration, starting with `connectors/slack/` |

## Troubleshooting

- **`pull-bookmarks` fails with 401 after weeks of inactivity** — the X
  refresh token expired. Run `bowerbird auth` locally, then
  `bowerbird push-secrets` to update the `X_TOKENS` secret.
- **Threads stop reconstructing** — check the run log's `search_mode`; if your
  API plan rejects full-archive search the pull automatically falls back to
  the 7-day recent search.
- **Compile fails the lint gate** — read the violation list in the run log;
  the compile agent is required to fix violations before committing, so
  repeated failures usually mean a malformed raw file or an interrupted run.
  Re-dispatch `compile-wiki`.
- **Recap silent** — run `bowerbird doctor`, inspect the `kb-recap-feed`
  workflow run, and check the connector agent's last run/logs.

## Appendix: the X developer app, click by click

X has no API for creating developer apps, so this is the one manual stretch.
(If your coding agent has browser control, it can drive these pages with you
while you stay logged in; you handle login and any payment step.) The portal UI
shifts occasionally; if a button has moved, the
*values* below are what matter.

Create a **new app dedicated to Bowerbird** even if you already have X apps —
keeping it separate means its credentials revoke independently and its API
usage shows up as its own line on your bill.

X is migrating from the old developer portal to a redesigned console
(console.x.com) — you may land on either. The old portal organizes things as
Project → App; the new console has Apps directly, with
Development/Staging/Production environments (Development is fine for a
personal pipeline). The values below are what matter in both.

1. **Portal + billing** — sign in at
   <https://developer.x.com/en/portal/dashboard>. Enable **pay-as-you-go**
   billing on your account (payment method required; reads cost
   ~$0.001–0.005/post — see [the cost table](importing-x.md)).
2. **Create the app** — app names are globally unique across all of X, so
   plain "bowerbird" will be taken; use something like
   `bowerbird-<your-handle>`. In the new console the creation dialog shows
   credentials **once**: copy the **Bearer Token** (starts `AAAA…`) into a
   password manager right away — that's `X_BEARER_TOKEN`. The OAuth 1.0a
   Consumer Key/Secret shown next to it are NOT used by Bowerbird; the OAuth
   2.0 client id/secret come from the user-authentication step below.
3. **Configure user authentication** — on the app's settings page, find
   **User authentication settings → Set up / Edit**:
   - App permissions: **Read** is enough.
   - Type of app: **Web App, Automated App or Bot** (confidential client) —
     this gives you a client *secret*; the **Native/Public** option works too
     but has no secret (leave `X_CLIENT_SECRET` empty then).
   - Callback / Redirect URI — register `http://bowerbird.localhost:8080/callback`
     for CLI auth.
   - Website URL: anything real (your GitHub fork's URL is fine).
4. **Collect the three values** (the wizard asks for them; don't paste them
   into chats — though an agent with browser control may pipe a Copy-button
   value from the clipboard into the gitignored `bin/.env` without ever
   reading it, and the wizard will pick it up as a saved default):
   - **OAuth 2.0 Client ID** — under the app's "Keys and tokens", a
     mixed-case string ending in `:1:ci` or similar.
   - **OAuth 2.0 Client Secret** — same page (confidential clients only).
     Shown once; regenerate if lost.
   - **Bearer Token** — same page, the app-only token, a long string
     starting with `AAAA`. Used for account mirrors and thread search. (In
     the new console this was already shown once at app creation; regenerate
     it here if you missed it.)
5. **Scopes** are requested at sign-in time by Bowerbird itself
   (`bookmark.read tweet.read users.read offline.access`) — you don't
   configure them in the portal, but the OAuth consent screen will list
   them; `offline.access` is what keeps the pipeline running unattended.
