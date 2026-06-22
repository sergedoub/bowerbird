---
name: setup
description: Set up this Bowerbird instance end to end — credentials, X app, OAuth, folder mapping, GitHub Actions secrets, first pull, doctor, and Slack connector recap. Use when the user wants to set up, configure, install, or onboard this freshly cloned repository.
---

# Bowerbird setup (guided, in-session)

You are setting up this clone for the user, who is present and can do browser
steps when asked. `docs/setup.md` is the source of truth — read it before
acting and follow its order. Go ONE STEP AT A TIME: do a step, verify it,
show the evidence, then move on.

## Interaction rules

- When the user must choose between options (which folders to watch, which
  accounts to follow, quiet-day recap preference), prefer a structured
  user-choice tool when it is actually callable in the current session. If the
  tool is unavailable or rejected, immediately ask the same choice as a
  concise numbered list and continue from the user's reply.
- Anything interactive or secret-bearing that you cannot do safely, the user
  runs themselves: tell them the exact command with the `!` prefix and wait.
- Browser control is opt-in. If you have a browser tool, offer to drive the X
  developer portal, GitHub PAT pages, model-provider key pages, and Slack app
  setup with the user's logged-in session — they handle login and payment
  screens. If you do not have safe browser control, fall back to click-by-click
  instructions.
- Clipboard rule (only when you have browser control): for EVERY credential
  behind a Copy/reveal control (X console values, the GitHub fine-grained
  PAT, and the compile-runner credential), click Copy yourself and pipe the
  clipboard into the gitignored bin/.env under the exact key name:
  `(umask 177; touch bin/.env); printf 'GH_PAT=%s\n' "$(pbpaste)" >> bin/.env`
  (Linux: `xclip -o`). Keys: X_CLIENT_ID, X_CLIENT_SECRET, X_BEARER_TOKEN,
  GH_PAT, and exactly one compile key: OPENAI_API_KEY for codex,
  ANTHROPIC_API_KEY for claude, or GEMINI_API_KEY for gemini. NEVER let a
  secret value into your
  context: no DOM text reads of credential fields, no screenshots while a
  secret is revealed on screen, no cat of bin/.env, no echoing values.
  While a secret is visible, locate the Copy control via the
  interactive-element / accessibility tree only (labels and roles, never
  page text or field values) and click it by reference. Verify by key name
  only (`grep -c '^GH_PAT=' bin/.env`).
- After credentials are verified, clean up browser state. Once `bin/.env` has
  the expected key names, `bowerbird push-secrets` has run, and
  `gh secret list` shows the expected Actions secret names, close only
  setup-only tabs you opened: X developer portal/console tabs, GitHub PAT or
  repo-secret pages, model-provider API-key pages, OAuth callback leftovers,
  Slack app setup tabs, and setup docs/search tabs opened only for credential
  work. Never inspect secret values during this cleanup, and leave unrelated
  user browsing alone.
- Onboarding questions speak the user's language: "watch a folder",
  "follow an account", "added to your knowledge base". Internals — file
  names, workflow names, "mirror", "dump", "topic mapping" — belong in
  your status output after decisions, never in the questions themselves.
- Never touch raw/ or wiki/ by hand; never force-push; never commit secrets.

## The journey

1. **Prerequisites** — python3 (3.11+), git, gh CLI installed AND
   authenticated (`gh auth status`); confirm `origin` points at the user's
   fork and the branch is `main`. Report gaps with install instructions
   before continuing.

2. **Install** — virtualenv, `pip install -e '.[dev]'`, then
   `python3 -m pytest` and `bowerbird lint` must pass; `git status` clean.

3. **X developer app** — create a NEW app dedicated to Bowerbird (names
   are globally unique; suggest `bowerbird-<handle>`). Pay-as-you-go
   billing, OAuth 2.0 user auth, and redirect URI
   `http://bowerbird.localhost:8080/callback`. Follow the click-by-click appendix in
   `docs/setup.md` (covers the old portal and the new console.x.com). Stage
   the three credentials per the clipboard rule.

4. **Remaining credentials** — stage into bin/.env, then push:
   a. GH_PAT: fine-grained, this repo, "Secrets: read and write"; suggest
      a longer expiration than the 30-day default (the pipeline uses it
      on every run). Clipboard rule applies.
   b. Model provider key: default to the active setup agent's provider unless
      the user chooses otherwise. In Codex, use OpenAI/Codex:
      `bowerbird models --provider openai --write`, open
      https://platform.openai.com/api-keys, create a Bowerbird API key, and
      stage it as OPENAI_API_KEY per the clipboard rule. If the user selects
      Claude or Gemini instead, use `bowerbird models --provider anthropic
      --write` plus ANTHROPIC_API_KEY, or `bowerbird models --provider gemini
      --write` plus GEMINI_API_KEY. Hosted CI cannot use a local app
      subscription directly; it needs the API key secret.
   c. Run `bowerbird auth` to create `bin/.x_tokens.json`, then run
      `bowerbird push-secrets`. Verify names with `gh secret list`; it
      should include `X_TOKENS` and the compile key the user chose.
      `BOWERBIRD_LIVE_INSTANCE=true` should be set once required ingest
      secrets are present.

5. **Watch folders and follow accounts** — run `bowerbird folders`, then
   ask the user which folders to watch and which accounts to follow. Use
   plain language: "watch a folder", "follow an account", "wiki section",
   and "recap label". Write `config/topics.toml` and
   `config/accounts.toml` directly, then commit the config changes.

6. **First pull** — commit/push anything still local, ensure Actions are
   enabled, dispatch `pull-bookmarks` with `limit_per_folder=3` and
   dispatch `account-dump` (`gh workflow run`, watch with `gh run watch`).
   The default first bookmark import is capped to the latest 3 items per
   selected folder. If the user explicitly asks to import all folder history,
   first run `bowerbird folders --counts`, explain the count/cost estimate,
   then dispatch `pull-bookmarks` with `import_all=true`. Confirm
   `compile-wiki` chains green, new files land in raw/ and wiki/, and
   `bowerbird lint` passes. Run `bowerbird doctor` for the text-first health
   surface.

7. **Slack connector** — follow `connectors/slack/README.md`: create or
   configure the Slack app with the user present, store the bot token in the
   connector runtime secret store, choose a channel/DM/App Home target, set
   the external connector schedule, and manually verify one delivery.

8. **Wrap-up** — status table: what works (tests, lint, doctor, each
   workflow, Slack connector), what the user chose (watched folders,
   followed accounts, Slack destination), what remains optional
   (COMPILE_RUNNER, DUMP_WINDOW_DAYS, cron times per docs/upgrading.md).
   Remind them the wiki fills as the daily crons run.
