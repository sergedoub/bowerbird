# Setup Guide

From fork to a working instance: bookmarks flowing in daily, a compiled wiki,
and a local dashboard for setup, health, and recap preview. Expect 30–45
minutes, most of it on the X developer portal.

> Using a coding agent? Start with Codex if you have it. The intended browser
> path is the Codex Chrome extension, not macOS System Events/Desktop UI
> fallback. Already cloned — ask the agent to run Bowerbird setup from this
> repo. Not cloned yet — paste the prompt from
> [docs/setup-prompt.md](setup-prompt.md) into an agent session anywhere.

The public repo is not empty. It ships as a living demo snapshot with four
starter AI accounts (`thsottiaux`, `bcherny`, `OfficialLoganK`, and
`santiagomed`) and generated wiki/recap output. Your fork inherits that sample
content; connecting X and enabling workflows turns the fork into your own
running instance.

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
  - OAuth 2.0 user authentication set up with only these local redirect URIs:
    `http://bowerbird.localhost:8080/callback` and
    `http://bowerbird.localhost:3000/api/auth/callback`, scopes
    `bookmark.read tweet.read users.read offline.access`;
  - the OAuth2 **client id** (and secret, for confidential clients);
  - the app-only **bearer token**.
- LLM credentials for hosted automation. Setup should default to the model
  provider of the agent doing the setup: Codex uses `OPENAI_API_KEY` from
  <https://platform.openai.com/api-keys>, Claude Code uses
  `ANTHROPIC_API_KEY`, and Gemini uses `GEMINI_API_KEY`. See
  [compile runners](compile-runners.md).
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

The recommended agent path is slightly different from the old terminal-only
wizard: the agent stages secrets, launches the local dashboard, and lets the
dashboard handle X sign-in and source choices.

Secrets stay out of chat. With extension-backed browser control, the agent
should click portal Copy buttons and pipe clipboard values directly into the
gitignored `bin/.env` under the right key names. It must not read secret
fields from the DOM, take screenshots while secrets are visible, `cat` secret
files, echo values, or ask you to paste credentials into chat. Verification is
by key presence only, for example `grep -c '^X_CLIENT_ID=' bin/.env`.

The first secret you must mint by hand is `GH_PAT`: a fine-grained personal
access token that can write this repo's secrets
(<https://github.com/settings/personal-access-tokens/new>; repository
permission "Secrets: read and write"). The pipeline uses it to persist the
rotating X token after each run.

The second is the model-provider key selected during setup. A local app
subscription does not automatically authenticate GitHub Actions, so hosted
runs need the matching API key secret.

Use `bowerbird models` any time to inspect or change `config/models.toml`.
After `bin/.env` is staged, run `bowerbird push-secrets`. `X_TOKENS` will be
missing at this point; the local dashboard sign-in seeds it next. The workflows
live in every checkout as product code, but scheduled personal ingest stays off
until setup has the required ingest secrets and marks the repo live with
`BOWERBIRD_LIVE_INSTANCE=true`.

After `bowerbird push-secrets`, verify secret storage by name only: local
presence checks such as `grep -c '^X_CLIENT_ID=' bin/.env`, and
`gh secret list` for Actions secret names. Do not print or inspect values.
Once names are verified, close credential tabs opened just for setup: X
developer portal/console tabs, GitHub PAT or repo-secret pages, model-provider
API-key pages, OAuth callback leftovers, and setup docs/search tabs. Leave
unrelated browsing alone, and keep Bowerbird dashboard/recap/health tabs open.

## 2. Local dashboard

Create `web/.env.local` without printing secret values:

```bash
grep '^X_CLIENT_ID=' bin/.env >> web/.env.local
grep '^X_CLIENT_SECRET=' bin/.env >> web/.env.local
printf 'GITHUB_REPO=%s\n' '<your-fork-owner/name>' >> web/.env.local
printf 'GITHUB_TOKEN=%s\n' "$(gh auth token)" >> web/.env.local
printf 'APP_URL=http://bowerbird.localhost:3000\n' >> web/.env.local
printf 'OWNER_X_USERNAME=%s\n' '<your-x-handle>' >> web/.env.local
printf 'SESSION_SECRET=%s\n' "$(openssl rand -hex 32)" >> web/.env.local
```

Then run the dashboard:

```bash
cd web
npm install
npm test
npm run dev
```

Open <http://bowerbird.localhost:3000>. Browsers resolve `*.localhost` to your
own machine, so this gives Bowerbird a nicer local URL without any OS changes.
The homepage shows the starter demo recap when a feed exists, but setup is not
complete until you connect X. Click **Connect X** to seed `X_TOKENS`, then
manage monitored accounts and bookmark mappings from the homepage. Saves are
commits to your repo; run `git pull` afterwards so the clone has the dashboard
commits. After X sign-in, verify `gh secret list` includes `X_TOKENS`, then
close any remaining setup-only credential or OAuth tabs while leaving the
dashboard open.

## 3. Commit config and enable Actions

```bash
git add config && git commit -m "config: my topics and accounts" && git push
```

On GitHub: **Actions tab → enable workflows**. Then dispatch `pull-bookmarks`
once with `limit_per_folder` set to `3`, and dispatch `account-dump` once
manually (Run workflow). The setup bookmark import reads only the latest three
items from each selected folder. To import full folder history instead, first
run `bowerbird folders --counts` for a count/cost estimate, then dispatch
`pull-bookmarks` with `import_all` set to `true`. Scheduled runs use
forward-only stop-at-existing behavior, so they pick up newer items without
draining old folder history. Green runs mean raw posts are landing in `raw/`;
the `compile-wiki` workflow chains automatically and writes `wiki/`, gated by
the provenance linter.

Verify locally any time:

```bash
bowerbird pull          # should print written/skipped counts and search_mode
bowerbird lint          # must print: provenance OK
```

To add one account after setup, use the fast path:

```bash
bowerbird accounts add guinnesschen --topic codex
git add config/accounts.toml && git commit -m "config: follow guinnesschen" && git push
gh workflow run account-dump.yml -f handle=guinnesschen -f days=3
```

When the three-day import finishes, use the cost printed by the run log and
keep the user-facing update short: "Account added. Last 3 days of posts
imported. Cost $0.011. Recap of posts will be available shortly." Compile and
recap can continue in the background; Health is the status surface.

## 4. Recap feed and Slack

The `kb-recap-feed` workflow writes `compile/recap-feed.json` daily — the
machine-readable "what's new" feed. The local dashboard previews it and uses
Health to show freshness and workflow status. Any other local consumer of the
[feed contract](slack-recap.md) can send the recap elsewhere.

To post the daily recap to Slack, use the dashboard's **Slack recap** section:
create or open a Slack app with incoming webhooks enabled, choose a channel,
paste the webhook URL, and click **Save and send test recap**. Bowerbird posts
the current recap/test message immediately and stores the webhook as the
`SLACK_WEBHOOK_URL` repo secret for the `slack-recap` workflow.

## 5. Local web app

The local web app is the setup/control surface. It gives you:

- **Sign in with X** — which also (re)seeds the pipeline's `X_TOKENS` secret
  and marks the repo as a live instance when the other required secrets exist;
  this is the recovery path when the refresh token expires after long
  inactivity.
- **Folders** — map bookmark folders to topics by name.
- **Homepage** — manage monitored accounts and bookmark folder mappings; saves
  are commits.
- **Slack recap** — connect a Slack incoming webhook and send a test/current
  recap to the chosen channel.
- **Health** — feed freshness and per-workflow status; the page that catches
  silent failures.
- **Recap** — preview today's feed.

## 6. Customization

| What | Where |
| --- | --- |
| Compile and recap provider/model override | `config/models.toml`, `bowerbird models`, or the dashboard Models section |
| Compile agent (codex / claude / gemini) | `COMPILE_RUNNER` repository variable |
| Live-instance scheduled ingest | `BOWERBIRD_LIVE_INSTANCE=true`, set by setup after required ingest secrets exist |
| Account-mirror window | `DUMP_WINDOW_DAYS` repository variable |
| Cron times | Workflow files — the one accepted fork edit, see [upgrading](upgrading.md) |
| Recap labels per account | `label` field in `config/accounts.toml` |
| Slack delivery | `SLACK_WEBHOOK_URL` GitHub Actions secret, set by the dashboard |
| Recap provider/model / quiet days | `RECAP_PROVIDER`, `RECAP_MODEL`, `RECAP_QUIET_MESSAGE` in local web env / repo variables |

## Troubleshooting

- **`pull-bookmarks` fails with 401 after weeks of inactivity** — the X
  refresh token expired. Sign in with X on the web app (or run
  `bowerbird auth` locally and update the `X_TOKENS` secret).
- **Threads stop reconstructing** — check the run log's `search_mode`; if your
  API plan rejects full-archive search the pull automatically falls back to
  the 7-day recent search.
- **Compile fails the lint gate** — read the violation list in the run log;
  the compile agent is required to fix violations before committing, so
  repeated failures usually mean a malformed raw file or an interrupted run.
  Re-dispatch `compile-wiki`.
- **Recap silent** — the web app's Health page shows feed freshness and which
  workflow broke.

## Appendix: the X developer app, click by click

X has no API for creating developer apps, so this is the one manual stretch.
Use extension-backed browser control if your agent has it. In Codex, first
attach to the Chrome extension bridge and verify Chrome shows it is being
controlled/debugged by Codex. If extension attach fails, or macOS asks for
System Events/Desktop UI control, pause and ask the user to reconnect/restart
the extension instead of silently falling back. In Claude Code, use
`claude --chrome` or `/chrome` with the Chrome extension. The user handles
login and any payment step. The portal UI shifts occasionally; if a button has
moved, the *values* below are what matter.

If ordinary browser UI blocks the setup, the agent should try the normal
browser escape hatches before pausing: press Escape, click outside the overlay,
or click a visible close/cancel/not-now control. This covers 1Password,
autofill, cookie, save-password, and help/chat overlays. The agent must not
inspect 1Password item contents, choose/fill stored secrets, or use desktop
automation for credential values; native 1Password unlock and OS prompts stay
with the user.

After the agent has verified local key names and Actions secret names, it
should close any setup-only X console, GitHub PAT/secrets, model-provider
key, OAuth leftover, and setup-doc tabs it opened. It should keep Bowerbird
dashboard, recap, and health tabs open, and leave unrelated user tabs alone.

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
   - Callback / Redirect URIs — register only these local values:
     `http://bowerbird.localhost:8080/callback` (CLI fallback auth) and
     `http://bowerbird.localhost:3000/api/auth/callback` (the local web app's
     sign-in). Do not add plain `localhost` callbacks; `bowerbird.localhost`
     is the canonical local dashboard URL.
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
