# AI-Guided Setup

Have a coding agent (Codex, Claude Code, or compatible) set Bowerbird up for you,
end to end. You don't need to clone anything first — paste the prompt below
into an agent session running **anywhere** (any folder, any project) and it
takes it from there: forking, cloning, credentials, first pull, web app.

Heads-up before you start:

- You'll need roughly 30–45 minutes and a payment method on the X developer
  portal (pay-as-you-go; a normal day of use costs cents).
- The public repo includes a living demo wiki/recap from four AI accounts, so
  your fork is viewable before setup. Connecting X turns that demo snapshot
  into your own running instance.
- Secrets stay out of the chat: when browser control is available, the agent
  clicks Copy controls and writes clipboard values straight into gitignored
  env files without reading them.
- Browser control is strongly recommended. In Codex, use the Chrome extension
  bridge specifically; the expected evidence is that the extension attaches
  successfully and Chrome shows it is being controlled/debugged by Codex. If
  extension attach fails or macOS asks for System Events/Desktop UI control,
  pause and ask the user to reconnect/restart/enable the extension. Do not
  silently fall back to System Events for credential pages. In Claude Code,
  start with `claude --chrome` or run `/chrome` with the Chrome extension
  installed. Without extension-backed browser control, use click-by-click
  instructions.
- If ordinary browser UI gets in the way, the agent should try to clear it
  before pausing: press Escape, click outside the overlay, or click visible
  close/cancel/not-now controls. This includes 1Password, autofill, cookie,
  save-password, and help/chat overlays. The agent must not inspect 1Password
  item contents, choose/fill stored secrets, or use desktop automation for
  credential values; native 1Password unlock or OS prompts remain user-owned.
- After the agent verifies the required key names are stored locally and in
  GitHub Actions, it should close setup-only credential tabs it opened
  (X developer portal, GitHub PAT/secrets pages, model-provider key pages,
  OAuth leftovers, and setup docs/search tabs) while leaving the Bowerbird
  dashboard/recap/health tabs open. It should not close unrelated browsing.

---

Copy everything below into the agent:

```text
Set up Bowerbird for me, end to end. You're hearing about it for the first
time: Bowerbird turns my X (Twitter) bookmarks and selected X accounts into a
personal, LLM-compiled markdown knowledge base with a daily recap. It lives at
https://github.com/sergedoub/bowerbird — my fork of it will be both the code
and my data, and its GitHub Actions are the compute. The upstream repo is also
a living demo with four starter AI accounts and generated wiki/recap output;
my fork starts with that demo snapshot until we connect my X account and run my
own workflows. I may be in a completely unrelated directory right now; treat
this as a brand-new project and I am present for browser steps when you ask.

Ground rules:
- Once cloned, the repo's docs/setup.md is the source of truth — follow its
  order, don't improvise. Re-read README.md and docs/setup.md before acting.
- Go ONE STEP AT A TIME: do a step, verify it worked, show me the evidence
  (command output, file created, green run), then move on. If something
  fails, stop and troubleshoot before continuing.
- Use extension-backed browser control if you have it. In Codex, first attach
  to the Chrome extension bridge and verify that Chrome shows it is being
  controlled/debugged by Codex. If the extension is unavailable, fails to
  attach, or macOS prompts for System Events/Desktop UI control, stop and tell
  me the exact state; do not continue with System Events for credential pages
  unless I explicitly approve that fallback. In Claude Code, use `claude
  --chrome` or `/chrome`. I handle login, payment, and permission screens; you
  can drive ordinary navigation and Copy buttons only through the browser
  extension path.
- If unexpected browser UI blocks progress, try the normal escape hatches
  before pausing: press Escape, click outside the overlay, or click a visible
  close/cancel/not-now control. This applies to 1Password, autofill, cookie,
  save-password, and help/chat overlays. Do not inspect 1Password item
  contents, choose/fill stored secrets, or use desktop automation for
  credential values. If a native 1Password unlock or OS prompt appears, stop
  and ask me to handle it.
- If a step truly requires me to run something interactive myself, tell me the
  exact command to run with the `!` prefix and wait. Never ask me to paste
  tokens or secrets into this chat, never write them anywhere except the
  gitignored setup files, and never commit them.
- When I must choose between setup options, prefer a structured user-choice
  tool such as AskUserQuestion or request_user_input only when it is actually
  callable in the current mode. If that tool is unavailable or rejected,
  immediately ask the same question as a concise numbered list and continue
  from my reply.
- Clipboard rule when you have extension-backed browser control — it applies to EVERY
  credential behind a Copy/reveal control in this journey (the X console
  values, the GitHub fine-grained PAT, and the selected model provider API
  key):
  click Copy yourself and pipe the clipboard into the repo's gitignored
  bin/.env under the exact key name, e.g.
  (umask 177; touch bin/.env); printf 'GH_PAT=%s\n' "$(pbpaste)" >> bin/.env
  (Linux: xclip -o instead of pbpaste). Keys: X_CLIENT_ID, X_CLIENT_SECRET,
  X_BEARER_TOKEN, GH_PAT, and one of OPENAI_API_KEY, ANTHROPIC_API_KEY, or
  GEMINI_API_KEY. NEVER let a secret value into your context: no DOM text
  reads of credential fields, NO screenshots while a secret is revealed on
  screen (close or scroll past the dialog first), no cat of bin/.env, no
  echoing values. While a secret is visible, locate the Copy control by
  reading only the interactive-element / accessibility tree (button labels
  and roles, never page text or field values) and click it by reference — a
  real click populates the clipboard. Verify by key name only, e.g.
  grep -c '^GH_PAT=' bin/.env.
- Never touch the repo's raw/ or wiki/ by hand, and never force-push.
- After verifying secrets by key name only, clean up the browser: close
  setup-only tabs you opened for X developer portal/console work, GitHub PAT
  or repo-secret setup, model-provider API keys, OAuth callback leftovers, and
  setup docs/search pages. Keep the Bowerbird dashboard, recap, and health
  tabs open. Leave unrelated user tabs alone.

The journey:

0. WORKSPACE — ask me where Bowerbird should live (suggest ~/bowerbird) and
   confirm before creating anything outside the current project.

1. PREREQUISITES — check python3 (3.11+), node + npm, git, and the gh CLI
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
   authentication set up, and only these local redirect URIs registered:
   http://bowerbird.localhost:8080/callback and
   http://bowerbird.localhost:3000/api/auth/callback. Do not add plain
   localhost web callbacks; Bowerbird uses bowerbird.localhost as the
   canonical local origin. Scopes "bookmark.read tweet.read users.read
   offline.access". docs/setup.md has the
   click-by-click appendix.
   - Strongly prefer extension-backed browser control. If this is Codex, use
     the Chrome extension bridge and verify Chrome shows it is being
     controlled/debugged by Codex before navigating credential pages. Do not
     use macOS System Events, AppleScript, screenshots/OCR, or generic desktop
     UI automation for credential pages unless I explicitly approve that
     fallback. If the extension is not connected, pause and tell me how to fix
     it, then use click-by-click instructions until it is available.
   Stage the three values per the clipboard rule (X_CLIENT_ID,
   X_CLIENT_SECRET, X_BEARER_TOKEN).

5. REMAINING CREDENTIALS — stage into bin/.env, then push:
   a. GH_PAT: fine-grained PAT scoped to my fork, "Secrets: read and
      write" — suggest a longer expiration than the 30-day default (the
      pipeline uses it on every run). Clipboard rule applies.
   b. Model provider key: default to the provider matching the agent I am
      using right now. If this session is Codex, choose OpenAI/Codex:
      run `bowerbird models --provider openai --write`, open
      https://platform.openai.com/api-keys, create a Bowerbird API key, and
      stage it as OPENAI_API_KEY per the clipboard rule. If this session is
      Claude Code or Gemini and I explicitly prefer that provider instead,
      use `bowerbird models --provider anthropic --write` with
      ANTHROPIC_API_KEY or `bowerbird models --provider gemini --write` with
      GEMINI_API_KEY. A local app subscription does not authenticate GitHub
      Actions; hosted automation needs this API key secret.
   c. Run `bowerbird push-secrets` — pushes everything staged to the
      repo's Actions secrets without printing a value (X_TOKENS will show
      as skipped; the web sign-in seeds it next). The workflows live in the
      repo as product code, but scheduled personal ingest stays off until
      setup has X_TOKENS too and marks the repo live with
      BOWERBIRD_LIVE_INSTANCE=true. Verify names with
      `gh secret list`; verify `config/models.toml` contains the selected
      provider. You can close the GitHub PAT and model-provider key tabs
      after this verification.

6. LOCALHOST CONTROL PANEL — onboarding now moves to the browser. Build
   web/.env.local shell-side (values never enter your context): copy
   X_CLIENT_ID and X_CLIENT_SECRET lines from bin/.env (grep >> — don't
   read them), GITHUB_REPO=<my fork owner/name>, GITHUB_TOKEN via
   printf 'GITHUB_TOKEN=%s\n' "$(gh auth token)" >> web/.env.local,
   APP_URL=http://bowerbird.localhost:3000, OWNER_X_USERNAME=<my X handle — ask me>,
   SESSION_SECRET via "$(openssl rand -hex 32)". Then
   cd web && npm install && npm test && npm run dev (background) and have
   me open http://bowerbird.localhost:3000. The homepage may show sample recap output
   from the upstream demo snapshot; that's useful for understanding the value,
   but my setup is not complete until I connect X. In the browser I:
   - Sign in with X (one click; this ALSO seeds the pipeline's X_TOKENS
     Actions secret automatically and sets BOWERBIRD_LIVE_INSTANCE when
     the other required secrets exist — that's the web app's job, not yours);
   - manage monitored accounts on the homepage, keeping or replacing the four
     starter AI accounts;
   - map bookmark folders to topics on the homepage.
   Saves are commits to my repo — run `git pull` afterwards so the clone
   has them, then confirm `gh secret list` now shows X_TOKENS too.
   After confirming X_TOKENS, close any remaining setup-only credential tabs
   you opened, including X developer console and OAuth leftover tabs. Keep
   http://bowerbird.localhost:3000 and recap/health tabs open for me.
   Fallback if the web sign-in misbehaves: `bowerbird auth` + ask me the
   watch/follow questions using the structured-question rule above (plain
   language — no file names, no "mirror"/"dump"; section names and recap
   labels default from the folder/account names) + write the TOMLs +
   push-secrets again.
   After setup, if I ask to follow a new account, use the fast path:
   `bowerbird accounts add <handle> --topic <topic>`, commit/push, then
   dispatch `gh workflow run account-dump.yml -f handle=<handle> -f days=3`.
   Do not narrate config edits, raw paths, workflow polling, commit hashes,
   or lint output unless I ask for evidence. If the three-day import
   completes in-session, respond like: "Account added. Last 3 days of posts
   imported. Cost $0.011. Recap of posts will be available shortly." Use the
   actual cost printed by the import. If the compile/recap is still running,
   monitor it quietly in the background and follow up only on success/failure.
   Once the dashboard shows the starter accounts and visible folders, say
   exactly:
   "Setup complete! You can now look at an example of four monitored X
   accounts and look at their recap: http://bowerbird.localhost:3000/recap. We also
   have access to your bookmark folders, and it is up to you to say which
   folders you want monitored and ingested into your wiki. Once selected, we
   will run the first import from each selected folder for the latest three
   pieces of content by default, then keep ingesting new items going forward.
   If you want the full folder history instead, say import all; I can first
   run a count estimate with `bowerbird folders --counts`. Budget up to
   $0.005 per post read for X calls."

7. FIRST PULL — commit and push anything still local, make sure Actions
   are enabled on the repo (walk me through the Actions tab if needed),
   then dispatch pull-bookmarks with a setup cap
   (`gh workflow run pull.yml -f limit_per_folder=3`) and account-dump
   with `gh workflow run account-dump.yml`; watch quietly or via a background
   monitor. The setup pull imports
   only the latest three items from each watched folder. If I explicitly
   choose "import all", run `bowerbird folders --counts` first, report the
   count/cost estimate, and only then dispatch
   `gh workflow run pull.yml -f import_all=true`. Normal scheduled pulls use
   forward-only stop-at-existing behavior, so they pick up newer items without
   draining old folder history. The first compile may need re-dispatching to
   chew through the backlog — it's idempotent. Both importers must go green;
   confirm compile-wiki chains green and new files land in raw/ and wiki/;
   run bowerbird lint after pulling. The Bowerbird Health page is my live
   status surface while this runs. Keep user-facing updates short and
   product-shaped; troubleshoot from docs/setup.md if a run fails.

8. SLACK CONSUMER — ask whether I want daily recaps posted to Slack now. If
   yes, use the Chrome extension bridge for Slack setup pages. The user handles
   Slack login/workspace prompts. Create or open a Slack app with incoming
   webhooks, choose the channel, and use only the page's Copy control for the
   webhook URL. Do not read, print, screenshot, or paste the webhook in chat.
   Paste it into the dashboard's Slack recap field and click "Save and send
   test recap". Confirm the dashboard reports Slack connected and a test/current
   recap was posted. Then verify by secret name only that `gh secret list`
   includes `SLACK_WEBHOOK_URL`; the daily `slack-recap` workflow will consume
   `compile/recap-feed.json`.

9. WRAP-UP — print a status table: what's working (tests, lint, each
   workflow, local web dashboard, recap feed, Slack delivery if configured),
   what I chose (watched folders, followed accounts, Slack channel if
   configured), and what's left optional (compile runner and model override via
   `bowerbird models`, DUMP_WINDOW_DAYS, cron times per docs/upgrading.md).
   Remind me the wiki fills up as the daily crons run.

Start with step 0 now.
```
