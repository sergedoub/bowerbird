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
  help with the portal; without it, the agent falls back to click-by-click
  instructions.

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
- I run anything interactive or secret-bearing myself: when a step needs an
  OAuth browser flow or typing credentials, tell me the exact command to run
  with the `!` prefix (e.g. `! bowerbird init`) and wait for me to report
  back. Never ask me to paste tokens or secrets into this chat, never write
  them into any file other than the repo's gitignored bin/.env, and never
  commit them.
- Clipboard rule when you have browser control — it applies to EVERY
  credential behind a Copy/reveal control in this journey (the X console
  values, the GitHub fine-grained PAT, and the compile-runner credential):
  click Copy yourself and pipe the clipboard into the repo's gitignored
  bin/.env under the exact key name, e.g.
  (umask 177; touch bin/.env); printf 'GH_PAT=%s\n' "$(pbpaste)" >> bin/.env
  (Linux: xclip -o instead of pbpaste). Keys: X_CLIENT_ID, X_CLIENT_SECRET,
  X_BEARER_TOKEN, GH_PAT, and exactly one compile key:
  OPENAI_API_KEY for codex, ANTHROPIC_API_KEY for claude, or GEMINI_API_KEY
  for gemini. NEVER let a secret value
  into your context: no DOM text reads of credential fields, NO screenshots
  while a secret is revealed on screen (close or scroll past the dialog
  first), no cat of bin/.env, no echoing values. While a secret is visible,
  locate the Copy control by reading only the interactive-element /
  accessibility tree (button labels and roles, never page text or field
  values) and click it by reference — a real click populates the clipboard.
  Verify by key name only, e.g. grep -c '^GH_PAT=' bin/.env.
- After credentials are verified by key name only, close only setup/credential
  tabs you opened: X developer portal/console tabs, GitHub PAT or repo-secret
  pages, model-provider API-key pages, OAuth callback leftovers, Slack app
  setup tabs, and setup docs/search tabs opened just for credential work. Do
  not inspect secret values, and do not close unrelated browsing.
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

4. X DEVELOPER APP — create a NEW app dedicated to Bowerbird, even if I
   already have other X apps (separate credentials I can revoke
   independently, and its own usage line on my X bill). Walk me through the
   portal at https://developer.x.com/en/portal/dashboard: pay-as-you-go
   billing enabled, a new project + app named for Bowerbird, OAuth 2.0 user
   authentication set up, and redirect URI registered:
   http://bowerbird.localhost:8080/callback. Scopes "bookmark.read tweet.read
   users.read offline.access". docs/setup.md has the click-by-click
   appendix.
   - If you have browser control (e.g. Claude in Chrome or a browser tool),
     offer to drive the portal together with my logged-in session instead of
     dictating clicks — I'll handle the login and any payment step myself.
   Stage the three values per the clipboard rule (X_CLIENT_ID,
   X_CLIENT_SECRET, X_BEARER_TOKEN).

5. REMAINING CREDENTIALS — stage into bin/.env, then push:
   a. GH_PAT: fine-grained PAT scoped to my fork, "Secrets: read and
      write" — suggest a longer expiration than the 30-day default (the
      pipeline uses it on every run). Clipboard rule applies.
   b. Model provider credential: default to the active setup agent's provider
      unless I choose otherwise. In Codex, choose OpenAI/Codex: run
      `bowerbird models --provider openai --write`, open
      https://platform.openai.com/api-keys, create a Bowerbird API key, and
      stage it as OPENAI_API_KEY per the clipboard rule. If I choose Claude or
      Gemini instead, run `bowerbird models --provider anthropic --write` plus
      ANTHROPIC_API_KEY, or `bowerbird models --provider gemini --write` plus
      GEMINI_API_KEY. Hosted GitHub Actions cannot use a local app
      subscription directly; it needs the API key secret.
   c. Run `bowerbird auth` to create the OAuth token file, then run
      `bowerbird push-secrets` — pushes everything staged to the repo's
      Actions secrets without printing a value and sets
      BOWERBIRD_LIVE_INSTANCE=true when the required ingest secrets are
      present. Verify names with `gh secret list`, including X_TOKENS and the
      compile key I chose.

6. WATCH FOLDERS AND FOLLOW ACCOUNTS — run `bowerbird folders`, then ask me
   which folders to watch and which accounts to follow. Use plain language:
   "watch a folder", "follow an account", "wiki section", and "recap
   label". Write `config/topics.toml` and `config/accounts.toml` directly,
   commit the config changes, and push.

7. FIRST PULL — make sure Actions
   are enabled on the repo (walk me through the Actions tab if needed),
   then dispatch `pull-bookmarks` with `limit_per_folder=3` and dispatch
   `account-dump` with gh workflow run; watch with gh run watch. The default
   first bookmark import is capped to the latest 3 items per selected folder.
   If I explicitly ask to import all folder history, first run
   `bowerbird folders --counts`, explain the count/cost estimate, then dispatch
   `pull-bookmarks` with `import_all=true`. Both importers must go green;
   confirm compile-wiki chains green and new files land in raw/ and wiki/; run
   bowerbird lint and bowerbird doctor after pulling. Troubleshoot from
   docs/setup.md if a run fails.

8. SLACK CONNECTOR — follow connectors/slack/README.md. With browser
   control, help me create or configure the Slack app, install it, store the
   bot token in the connector runtime's secret store, choose a channel/DM/App
   Home destination, set the external connector schedule after kb-recap-feed,
   and manually verify one delivery.

9. WRAP-UP — print a status table: what's working (tests, lint, doctor,
   each workflow, Slack connector), what I chose (watched folders, followed
   accounts, Slack destination), and what's left optional (compile runner via
   the COMPILE_RUNNER repo variable, DUMP_WINDOW_DAYS, cron times per
   docs/upgrading.md). Remind me the wiki fills up as the daily crons run.

Start with step 0 now.
```
