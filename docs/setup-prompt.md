# AI-Guided Setup

Have a coding agent set Bowerbird up for you, end to end. You don't need to
clone anything first — paste the prompt below into an agent session running
**anywhere** (any folder, any project) and it takes it from there: forking,
cloning, credentials, first pull, and Slack connector setup.

Heads-up before you start:

- You'll need roughly 30–45 minutes and a payment method on the X developer
  portal (pay-as-you-go; a normal day of use costs cents).
- Secrets stay out of the chat: the agent will ask you to run the interactive
  credential steps yourself. If your agent has a shell escape, run commands in
  the session terminal (for example, Claude Code uses `! <command>`).
- Want the agent to drive the X developer portal for you? Browser control is
  opt-in. Enable your agent's browser-control mode before starting if you want
  help with the portal; the prompt below then tells the agent to use it
  directly at credential steps instead of asking again. Without browser
  control, the agent falls back to click-by-click instructions.

---

Copy everything below into the agent:

```text
Set up Bowerbird for me, end to end. You're hearing about it for the first
time: Bowerbird turns my X (Twitter) bookmarks and selected X accounts into a
personal, LLM-compiled markdown knowledge base with a daily Slack recap. It
lives at https://github.com/sergedoub/bowerbird — my fork of it will be both
the code and my data, and its GitHub Actions are the compute. I may be in a
completely unrelated directory right now; treat this as a brand-new project
and I am present for browser steps when you ask.

Ground rules:
- Once cloned, the repo's docs/setup.md is the source of truth — follow its
  order, don't improvise. Re-read README.md and docs/setup.md before acting.
- Go ONE STEP AT A TIME: do a step, verify it worked, show me the evidence
  (command output, file created, green run), then move on. If something
  fails, stop and troubleshoot before continuing.
- I run anything interactive or secret-bearing myself unless browser-control
  tooling is enabled in this session. When browser control is not available,
  tell me the exact command to run with the `!` prefix (e.g. `! bowerbird
  init`) and wait for me to report back. When browser control is available,
  use it for credential pages by default: attach to the browser, navigate the
  page, and pause only for login, billing/payment, CAPTCHA, or a credential
  page where the safe Copy-button workflow is not possible. Never ask me to
  paste tokens or secrets into this chat, never write them into any file other
  than the repo's gitignored bin/.env, and never commit them.
- Clipboard rule when you have browser control — it applies to EVERY
  credential behind a Copy/reveal control in this journey (the X console
  values, the GitHub fine-grained PAT if this repo still requires one, and the
  compile-runner credential):
  click Copy yourself and pipe the clipboard into the repo's gitignored
  bin/.env under the exact key name, e.g.
  (umask 177; touch bin/.env); printf 'GH_PAT=%s\n' "$(pbpaste)" >> bin/.env
  (Linux: xclip -o instead of pbpaste). Keys: X_CLIENT_ID, X_CLIENT_SECRET,
  X_BEARER_TOKEN, GH_PAT, SLACK_BOT_TOKEN, and exactly one compile key:
  OPENAI_API_KEY for codex, ANTHROPIC_API_KEY for claude, or GEMINI_API_KEY
  for gemini. NEVER let a secret value
  into your context: no DOM text reads of credential fields, NO screenshots
  while a secret is revealed on screen (close or scroll past the dialog
  first), no cat of bin/.env, no echoing values. While a secret is visible,
  locate the Copy control by reading only the interactive-element /
  accessibility tree (button labels and roles, never page text or field
  values) and click it by reference — a real click populates the clipboard.
  Verify by key presence plus non-empty/value-shape only; never print values,
  and do not rely on `grep -c '^KEY='` alone because empty values can pass
  that check.
- After credentials are verified by key presence plus non-empty/value shape
  only, close only setup/credential tabs you opened: X developer portal/console
  tabs, GitHub PAT or repo-secret pages, model-provider API-key pages, OAuth
  callback leftovers, Slack app setup tabs, and setup docs/search tabs opened
  just for credential work. Do not inspect secret values, and do not close
  unrelated browsing.
- Parallel setup mode: if your agent can use subagents, use them only for
  non-browser work that cannot touch secrets: reading docs, checking repo
  health, preparing command lists, watching GitHub Actions, and drafting Slack
  connector checklists. One browser coordinator owns all GitHub/X/Slack/model
  provider pages. Do not let multiple agents control the same logged-in Chrome
  profile, clipboard, OAuth popup, or one-time credential modal. Credential
  copy sections must be serialized: one Copy click, immediate write to
  `bin/.env`, verify by key presence plus non-empty/value shape only, then
  continue.
- GitHub automation preference: use `gh` or GitHub APIs for every GitHub step
  they can handle: fork/clone, setting Actions secrets from staged files,
  setting variables, workflow dispatch, and run watching. Do not use Chrome for
  GitHub work when terminal auth can do it. GitHub does not offer an API to
  create a PAT; prefilled PAT URLs still require human web confirmation. If the
  repo supports a GitHub App installation-token path for secret writeback,
  prefer that over a PAT. If the current repo still requires `GH_PAT`, keep PAT
  creation as a minimal user-owned copy handoff, not a long browser-driving
  task.
- Never touch the repo's raw/ or wiki/ by hand, and never force-push.

The journey:

0. WORKSPACE — ask me where Bowerbird should live (suggest ~/bowerbird) and
   confirm before creating anything outside the current project.

1. PREREQUISITES — check python3 (3.11+), git, and the gh CLI
   (installed AND authenticated: gh auth status). Tell me what's missing and
   how to install it before going further. gh matters: it automates forking,
   secrets, and workflow runs.

2. FORK & CLONE — fork https://github.com/sergedoub/bowerbird to my account
   and clone it into the chosen directory (gh repo fork sergedoub/bowerbird
   --clone does both; without gh, walk me through forking in the browser and
   git clone). cd into it; confirm origin points at MY fork and the branch
   is main. My fork is where my knowledge base will accumulate.

3. INSTALL — create a virtualenv, pip install -e '.[dev]', then run
   python3 -m pytest and bowerbird lint. Both must pass. Confirm git status
   is clean.

3b. OPTIONAL PARALLEL PREP — after install is green, use subagents if they are
   available and helpful:
   - repo watcher: keep checking `git status`, `gh run list`, and later
     workflow runs, reporting only blockers or green evidence;
   - docs scout: keep README.md, docs/setup.md, docs/importing-x.md, and
     connectors/slack/README.md open conceptually and prepare the next exact
     command/checklist;
   - Slack prep: prepare the Slack app manifest for an app named `Bowerbird`,
     required bot scope (`chat:write`), destination questions, and acceptance
     test. The recap must post as the `Bowerbird` bot, not from my personal
     Slack account.
   These helpers must not drive Chrome credential pages, read secret files, or
   run setup commands that write credentials. The main agent remains the single
   setup coordinator.

4. X DEVELOPER APP — create a NEW app dedicated to Bowerbird, even if I
   already have other X apps (separate credentials I can revoke
   independently, and its own usage line on my X bill). Walk me through the
   portal at https://developer.x.com/en/portal/dashboard: pay-as-you-go
   billing enabled, a new project + app named for Bowerbird, OAuth 2.0 user
   authentication set up, and redirect URI registered:
   http://bowerbird.localhost:8080/callback. Scopes "bookmark.read tweet.read
   users.read offline.access". docs/setup.md has the click-by-click
   appendix.
   - If browser-control tooling is available, use it now: attach to my logged-in
     browser session, open the portal, and drive the setup with me. Do not end
     the turn asking whether to drive. Pause only for login, billing/payment,
     CAPTCHA, unavailable browser tooling, or a credential page where the safe
     Copy-button workflow is not possible.
   X's console can be slow to refresh after app creation. If a create flow
   shows credentials but the app is not immediately visible in the list, wait,
   refresh/reopen the Apps list, and verify whether it appeared before trying
   another create. Do not create duplicate apps just because the list is stale.
   Stage the three values per the clipboard rule (X_CLIENT_ID,
   X_CLIENT_SECRET, X_BEARER_TOKEN).

5. REMAINING CREDENTIALS — stage into bin/.env, then push:
   a. GitHub automation: first use existing `gh` authentication for everything
      terminal automation can do. `bowerbird push-secrets` sets initial Actions
      secrets from `bin/.env` through `gh secret set`; do not create a PAT just
      to push setup secrets. If the repo exposes a GitHub App setup path for
      scheduled writeback, prefer it: one human install/authorization step, then
      short-lived installation tokens generated programmatically. Only if this
      repo version still requires `GH_PAT`, create a fine-grained PAT scoped
      only to my Bowerbird fork with repository permission `Secrets: Read and
      write`. Do not try to API-create the PAT; GitHub requires its browser
      settings flow.
      Use a short name under 40 characters, verify exactly one selected repo
      and the final `Secrets: Read and write` permission, remove accidental
      adjacent permissions such as `Codespaces secrets`, then have me click
      Generate/Copy if browser automation is brittle. Stage `GH_PAT` from the
      clipboard and verify only presence plus non-empty/value shape.
   b. Model provider credential: default to the active setup agent's provider
      unless I choose otherwise. In Codex, choose OpenAI/Codex: run
      `bowerbird models --provider openai --write`, open
      https://platform.openai.com/api-keys, create a Bowerbird API key, and
      stage it as OPENAI_API_KEY per the clipboard rule. If browser control is
      available, open the API-key page and use the same Copy-button workflow
      without asking again. If I choose Claude or Gemini instead, run
      `bowerbird models --provider anthropic --write` plus ANTHROPIC_API_KEY,
      or `bowerbird models --provider gemini --write` plus GEMINI_API_KEY.
      Hosted GitHub Actions cannot use a local app subscription directly; it
      needs the API key secret.
   c. Run `bowerbird auth` to create the OAuth token file, then run
      `bowerbird push-secrets` — pushes everything staged to the repo's
      Actions secrets without printing a value and sets
      BOWERBIRD_LIVE_INSTANCE=true when the required ingest secrets are
      present. Verify names with `gh secret list`, including X_TOKENS and the
      compile key I chose.

6. WATCH FOLDERS AND FOLLOW ACCOUNTS — run `bowerbird folders`, then ask me
   which folders to watch and which accounts to follow. Use plain language:
   "watch a folder", "follow an account", "wiki section", and "recap
   label". If I do not know what account to mirror yet, offer the four public
   example accounts from the setup wizard as an opt-in starter set; explain
   that their posts are not pre-ingested in the source repo and that pulling
   them will spend X API reads. Write `config/topics.toml`, optional
   `config/accounts.toml`, and `config/recaps.toml` directly. For each watched
   topic, ask whether to create a daily or weekly recap profile; if account
   mirrors are selected, ask whether to create a daily account recap profile.
   Commit the config changes, and push.

7. FIRST PULL — make sure Actions
   are enabled on the repo (walk me through the Actions tab if needed),
   then run the first import workflows serially to avoid branch-race push
   failures: if account mirrors are configured, dispatch `account-dump` first
   with `days=1` and a small `max_posts` cap for the setup smoke, watch it
   green, and pull the resulting commit locally. Then dispatch `pull-bookmarks`
   with `limit_per_folder=3` and watch it green. The default first bookmark
   import is capped to the latest 3 items per selected folder.
   If I explicitly ask to import all folder history, first run
   `bowerbird folders --counts`, explain the count/cost estimate, then dispatch
   `pull-bookmarks` with `import_all=true`. Both importers must go green;
   confirm compile-wiki chains green and new files land in raw/ and wiki/.
   Compile can take a few minutes in the model step; do not treat a quiet
   running run as stuck. Capture the compile run id with `gh run list`, then
   watch it in a background terminal or repo-watcher helper with low-frequency
   status updates, e.g. `gh run watch <run-id> --exit-status`. While compile
   runs, you may read Slack/setup docs or prepare the next checklist, but do
   not dispatch recap/slack work or claim setup success until compile is green,
   the wiki commit is pulled locally, and `bowerbird lint` passes. If an older
   compile run fails only in the final push/commit step after compile and lint
   passed, and a newer compile run is already queued for the current branch,
   watch the newer run before declaring setup blocked. Run bowerbird doctor
   after pulling if this checkout exposes it. Troubleshoot from docs/setup.md
   if a run fails.

8. SLACK CONNECTOR — follow connectors/slack/README.md. With browser
   control, help me create or configure a dedicated Slack app named
   `Bowerbird` from `connectors/slack/manifest.json`, install it, and stage the
   Bot User OAuth Token as `SLACK_BOT_TOKEN` in `bin/.env` without reading,
   printing, screenshotting, or pasting the token into chat. Store the
   non-secret destination in `config/recaps.toml` under the relevant
   `[[recaps.deliveries]]` entry; prefer the channel or DM ID. Run
   `bowerbird push-secrets`, verify by secret name only that `gh secret list`
   includes `SLACK_BOT_TOKEN`, then dispatch `recap` or run
   `bowerbird slack-recap` against an existing manifest. Do not send from my
   personal Slack account, a user token, an incoming webhook, Codex/ChatGPT's
   Slack connector, or Guild's Slack app. Setup is complete only after one
   recap posts from the `Bowerbird` bot and the log records the destination,
   Slack channel, and Slack timestamp.

9. WRAP-UP — print a status table: what's working (tests, lint, doctor,
   each workflow, Slack connector), what I chose (watched folders, followed
   accounts, Slack destination), and what's left optional (compile runner via
   the COMPILE_RUNNER repo variable, DUMP_WINDOW_DAYS, cron times per
   docs/upgrading.md). Remind me the wiki fills up as the daily crons run.

Start with step 0 now.
```
