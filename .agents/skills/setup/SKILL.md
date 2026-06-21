---
name: setup
description: Set up this Bowerbird instance end to end — credentials, X app, OAuth, folder mapping, GitHub Actions secrets, first pull, local dashboard, recap feed. Use when the user wants to set up, configure, install, or onboard this freshly cloned repository.
---

# Bowerbird setup (guided, in-session)

You are setting up this clone for the user, who is present and can do browser
steps when asked. `docs/setup.md` is the source of truth — read it before
acting and follow its order. Go ONE STEP AT A TIME: do a step, verify it,
show the evidence, then move on.

## Interaction rules

- When the user must choose between options (which folders to watch, which
  accounts to follow, whether to keep the starter AI accounts), prefer a
  structured user-choice tool such as AskUserQuestion or request_user_input
  when it is actually callable in the current mode. If the tool is unavailable
  or rejected, immediately ask the same question as a concise numbered list
  and continue from the user's reply.
- Anything interactive or secret-bearing that you cannot do safely, the user
  runs themselves: tell them the exact command with the `!` prefix and wait.
- Browser control is strongly preferred. If running in Codex, first check for
  Browser/Chrome tooling and use it when available; if it is missing, tell the
  user how to enable it before falling back to manual click-by-click setup. In
  Claude Code, use `claude --chrome` or `/chrome`. The user handles login,
  payment, and permission screens; you drive ordinary navigation and Copy
  buttons.
- If ordinary browser UI blocks progress, try standard browser escape hatches
  before pausing: press Escape, click outside the overlay, or click a visible
  close/cancel/not-now control. This includes 1Password, autofill, cookie,
  save-password, and help/chat overlays. Do not inspect 1Password item
  contents, choose/fill stored secrets, or use desktop automation for
  credential values. Native 1Password unlock and OS prompts remain
  user-owned.
- Clipboard rule (only when you have browser control): for EVERY credential
  behind a Copy/reveal control (X console values, the GitHub fine-grained
  PAT, and the selected model-provider API key), click Copy yourself and pipe the
  clipboard into the gitignored bin/.env under the exact key name:
  `(umask 177; touch bin/.env); printf 'GH_PAT=%s\n' "$(pbpaste)" >> bin/.env`
  (Linux: `xclip -o`). Keys: X_CLIENT_ID, X_CLIENT_SECRET, X_BEARER_TOKEN,
  GH_PAT, and one of OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY.
  NEVER let a secret value into your
  context: no DOM text reads of credential fields, no screenshots while a
  secret is revealed on screen, no cat of bin/.env, no echoing values.
  While a secret is visible, locate the Copy control via the
  interactive-element / accessibility tree only (labels and roles, never
  page text or field values) and click it by reference. Verify by key name
  only (`grep -c '^GH_PAT=' bin/.env`).
- After credentials are verified, clean up browser state. Once `bin/.env`
  has the expected key names, `bowerbird push-secrets` has run, and
  `gh secret list` shows the expected Actions secret names, close setup-only
  tabs you opened: X developer portal/console tabs, GitHub PAT or repo-secret
  pages, model-provider API-key pages, OAuth callback leftovers, and setup
  docs/search tabs opened only for credential work. Keep the Bowerbird
  dashboard/recap/health tabs open. Never inspect secret values during this
  cleanup, and leave unrelated user browsing alone if a tab is not clearly
  part of Bowerbird setup.
- Onboarding questions speak the user's language: "watch a folder",
  "follow an account", "added to your knowledge base". Internals — file
  names, workflow names, "mirror", "dump", "topic mapping" — belong in
  your status output after decisions, never in the questions themselves.
- After setup, account-add requests use the fast path. Run
  `bowerbird accounts add <handle> --topic <topic>`, commit/push the config,
  dispatch a targeted three-day import with
  `gh workflow run account-dump.yml -f handle=<handle> -f days=3`, and keep
  workflow polling out of the user's chat. If the trailing-window import
  completes in-session, respond in this shape:
  "Account added. Last 3 days of posts imported. Cost $0.011. Recap of posts
  will be available shortly." Replace the cost with the dump summary's actual
  approximate cost. If the import/compile is still running, use a background
  subagent or thread monitor and only follow up on success or failure; do not
  narrate config edits, commit hashes, raw paths, workflow names, or lint
  output unless the user asks for evidence.
- Explain the demo boundary clearly: the public repo includes four starter AI
  account lanes plus generated sample wiki/recap output. The user's fork starts
  with that snapshot; connecting X and running workflows turns it into their
  live instance.
- Never touch raw/ or wiki/ by hand; never force-push; never commit secrets.

## The journey

1. **Prerequisites** — python3 (3.11+), node + npm, git, gh CLI installed
   AND authenticated (`gh auth status`); confirm `origin` points at the
   user's fork and the branch is `main`. Report gaps with install
   instructions before continuing.

2. **Install** — virtualenv, `pip install -e '.[dev]'`, then
   `python3 -m pytest` and `bowerbird lint` must pass; `git status` clean.

3. **X developer app** — create a NEW app dedicated to Bowerbird (names
   are globally unique; suggest `bowerbird-<handle>`). Pay-as-you-go
   billing, OAuth 2.0 user auth, and only these local redirect URIs:
   `http://bowerbird.localhost:8080/callback` and
   `http://bowerbird.localhost:3000/api/auth/callback`. Do not add plain
   `localhost` web callbacks; the setup uses `bowerbird.localhost` as the
   canonical local origin. Follow the
   click-by-click appendix in
   `docs/setup.md` (covers the old portal and the new console.x.com).
   Stage the three credentials per the clipboard rule.

4. **Remaining credentials** — stage into bin/.env, then push:
   a. GH_PAT: fine-grained, this repo, "Secrets: read and write"; suggest
      a longer expiration than the 30-day default (the pipeline uses it
      on every run). Clipboard rule applies.
   b. Model provider key: default to the active agent's provider. In Codex,
      use OpenAI/Codex: `bowerbird models --provider openai --write`, open
      https://platform.openai.com/api-keys, create a Bowerbird API key, and
      stage it as OPENAI_API_KEY per the clipboard rule. If the user selects
      Claude or Gemini instead, use `bowerbird models --provider anthropic
      --write` plus ANTHROPIC_API_KEY or `bowerbird models --provider gemini
      --write` plus GEMINI_API_KEY. Hosted CI cannot use a local app
      subscription directly; it needs the API key secret.
   c. Run `bowerbird push-secrets` (X_TOKENS shows as skipped — the web
      sign-in seeds it next). Verify names with `gh secret list`.

5. **Localhost control panel** — onboarding moves to the browser. Build
   web/.env.local shell-side (values never enter your context): copy the
   X_CLIENT_ID and X_CLIENT_SECRET lines from bin/.env via grep >>,
   GITHUB_REPO=<the fork>, GITHUB_TOKEN via
   printf 'GITHUB_TOKEN=%s\n' "$(gh auth token)" >> web/.env.local,
   APP_URL=http://bowerbird.localhost:3000, OWNER_X_USERNAME=<ask the user>,
   SESSION_SECRET via "$(openssl rand -hex 32)". Then
   `cd web && npm install && npm test && npm run dev` (background) and
   send the user to http://bowerbird.localhost:3000, where they:
   - Sign in with X (one click — this ALSO seeds the pipeline's X_TOKENS
     Actions secret automatically);
   - inspect the sample recap/output if present;
   - keep or replace the four starter AI accounts on the homepage;
   - choose which folders Bowerbird watches on the homepage.
   Saves are commits to the repo — `git pull` afterwards, then confirm
   `gh secret list` now includes X_TOKENS. Fallback if web sign-in
   misbehaves: `bowerbird auth`, then ask the watch/follow questions in
   chat using the structured-question rule above (plain language — no file
   names, no "mirror"/"dump"; wiki section and recap label default from the
   folder/account names), write the TOMLs, push-secrets again.
   After confirming X_TOKENS, close any remaining setup-only credential tabs
   per the cleanup rule; keep http://bowerbird.localhost:3000 and recap/health
   tabs open for the user.
   Once the dashboard shows the starter accounts and visible folders, use this
   deterministic handoff:
   "Setup complete! You can now look at an example of four monitored X
   accounts and look at their recap: http://bowerbird.localhost:3000/recap. We also
   have access to your bookmark folders, and it is up to you to say which
   folders you want monitored and ingested into your wiki. Once selected, we
   will run the first import from each selected folder for the latest three
   pieces of content by default, then keep ingesting new items going forward.
   If you want the full folder history instead, say import all; I can first
   run a count estimate with `bowerbird folders --counts`. Budget up to
   $0.005 per post read for X calls."

6. **First pull** — commit/push anything still local, ensure Actions are
   enabled, dispatch `pull-bookmarks` with a setup cap and `account-dump`
   (`gh workflow run pull.yml -f limit_per_folder=3`; then
   `gh workflow run account-dump.yml`; watch quietly or via a background
   monitor). The setup pull imports only the latest three items from each
   watched folder. If the user explicitly
   chooses "import all", run `bowerbird folders --counts` first, report the
   count/cost estimate, and only then dispatch
   `gh workflow run pull.yml -f import_all=true`. Normal scheduled pulls use
   forward-only stop-at-existing behavior, so they pick up newer items without
   draining old folder history. The first compile may need re-dispatching to
   clear the backlog — it's idempotent. Confirm `compile-wiki` chains green,
   new files land in raw/ and wiki/, and `bowerbird lint` passes. The
   Bowerbird Health page is the live status surface. Keep user-facing updates
   terse; gather detailed workflow evidence internally. Troubleshoot from
   `docs/setup.md`.

7. **Slack consumer** — ask whether the user wants daily recaps posted to
   Slack now. If yes, use the Chrome extension bridge for Slack setup pages.
   The user handles Slack login/workspace prompts. Create or open a Slack app
   with incoming webhooks, choose the channel, and use only the page's Copy
   control for the webhook URL. Do not read, print, screenshot, or paste the
   webhook in chat. Paste it into the dashboard's Slack recap field and click
   "Save and send test recap". Confirm the dashboard reports Slack connected
   and a test/current recap was posted. Then verify by secret name only that
   `gh secret list` includes `SLACK_WEBHOOK_URL`; the daily `slack-recap`
   workflow will consume `compile/recap-feed.json`.

8. **Wrap-up** — status table: what works (tests, lint, each workflow,
   local dashboard, recap feed, Slack delivery if configured), what the user
   chose (watched folders, followed accounts, Slack channel if configured),
   what remains optional (model provider via `bowerbird models`,
   DUMP_WINDOW_DAYS, cron times per docs/upgrading.md). Remind them the
   wiki fills as the daily crons run.
