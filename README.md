# Bowerbird

## Start Here: Paste This Into Codex

Open Codex in any folder and paste:

```text
Set up Bowerbird for me, end to end.

Use https://github.com/sergedoub/bowerbird as the upstream repo. First read
the full guided setup prompt at:
https://github.com/sergedoub/bowerbird/blob/main/docs/setup-prompt.md

Follow that setup flow one step at a time: ask me where the repo should live,
fork and clone it, verify prerequisites, keep secrets out of chat, use
the Codex Chrome extension for credential pages, launch the local dashboard,
run the first import, and show evidence before moving to each next step. If
the Chrome extension is not attached, pause and tell me how to connect it; do
not silently fall back to macOS System Events or desktop UI automation for
credential pages. If browser overlays like 1Password, autofill, cookies, or
save-password prompts block progress, first try Escape, clicking outside, or a
visible close/cancel/not-now control; do not inspect or fill stored secrets.
After verifying stored secret names, close setup-only developer portal,
GitHub PAT/secrets, model-provider key, OAuth leftover, and setup-doc tabs;
keep the Bowerbird dashboard/recap/health tabs open.
```

The full agent prompt lives in [docs/setup-prompt.md](docs/setup-prompt.md).
Manual setup is still supported below, but the intended first-run path is to
have Codex drive the setup with you present for credentials and browser steps.

## What It Is

Collect, arrange, display: Bowerbird turns what you save into a personal,
LLM-compiled markdown knowledge base — and a daily recap so you actually
revisit it. It starts with X bookmarks and account mirrors, and its raw-source
contract also fits local notes, web clips, and long-form material.

- **Collect** — import the X bookmark folders you choose, and mirror selected
  X accounts in full. Raw snapshots land as append-only markdown under declared
  namespaces such as `raw/bookmarks/`, `raw/accounts/`, `raw/notes/`, and
  `raw/clips/`.
- **Arrange** — the active setup agent's model provider (Codex/OpenAI,
  Claude/Anthropic, or Gemini)
  compiles raw posts into a two-layer wiki: faithful, attributed source notes
  plus synthesized concept articles where **every claim cites its source**. A
  linter enforces that mechanically. The wiki is a native **Open Knowledge
  Format (OKF) v0.1 bundle**, so any OKF-aware tool can read it — with
  Bowerbird's stricter provenance lint as a floor on top.
- **Display** — a daily recap feed of what's new, delivered to Slack by the
  bundled self-hosted web app (or any consumer you build on the feed contract).

The design is deliberately simple: Python 3.11+ with a stdlib-only runtime,
markdown files as the database, your GitHub fork as the storage and compute
(GitHub Actions), no RAG, no embeddings, no vector store. Everything runs on
credentials you own — your X developer app, your LLM key, and a local
dashboard.

The public repo is also a living demo instance. It ships with four starter
AI-account lanes (`thsottiaux`, `bcherny`, `OfficialLoganK`, and
`santiagomed`) plus generated wiki/recap output so you can see the shape of a
working knowledge base before connecting your own X account. Your fork starts
with that demo snapshot; setup turns it into your running instance.

## Manual Setup

1. **Fork this repository and clone your fork** — the fork is your knowledge
   base; the pipeline commits your data into it daily.

   ```bash
   git clone https://github.com/<you>/<your-fork>.git && cd <your-fork>
   ```

2. **Install (in a virtualenv) and run the setup wizard:**

   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   python3 -m pip install -e '.[dev]'
   bowerbird init
   ```

   The wizard walks you through X app credentials, the OAuth sign-in, choosing
   which folders Bowerbird watches and which accounts it follows, and setting
   the GitHub Actions secrets (automatic when the `gh` CLI is installed).
3. **Enable GitHub Actions** on your fork and run `pull-bookmarks` once with
   `limit_per_folder=3`, then run `account-dump` once manually. Later account
   adds use `bowerbird accounts add <handle> --topic <topic>` plus a targeted
   `account-dump` dispatch with `handle=<handle>`, `days=3`. The compile chains
   automatically; `bowerbird lint` must print `provenance OK`.
4. **Run the local dashboard** for X sign-in, account management, bookmark
   mapping, pipeline health, and recap preview. See [web/README.md](web/README.md).

Full walkthrough: [docs/setup.md](docs/setup.md).

## CLI

```bash
bowerbird --help     # all verbs
bowerbird init       # interactive setup wizard
bowerbird auth       # X OAuth flow
bowerbird folders    # list your bookmark folders (names + ids)
bowerbird folders --counts # explicit count/cost estimate before importing all
bowerbird pull       # pull new bookmarks into raw/bookmarks/
bowerbird pull --limit-per-folder 3 # setup smoke import
bowerbird dump-account --handle <h> --days 3
bowerbird backfill --topic <t> --no-threads
bowerbird models     # choose compile + recap provider/model
bowerbird lint       # provenance guardrail

# advanced / optional
bowerbird push-secrets # push credentials staged in bin/.env to GitHub Actions secrets (non-interactive)
bowerbird dump-all     # archive ALL bookmarks (every folder + unsorted) outside the pipeline
bowerbird ingest-book  # split a Markdown book (config/books.toml) into raw chapter inputs
```

## Costs

Everything is bring-your-own and usage-priced: X pay-as-you-go API reads
(roughly $0.001–0.005 per post; a normal day costs cents — see the cost table
in [docs/importing-x.md](docs/importing-x.md)), and your LLM credentials for
the compile and recap synthesis. There are no Bowerbird servers and no
subscription.

## Documentation

| Doc | What it covers |
| --- | --- |
| [Setup guide](docs/setup.md) | Fork → wizard → green workflows. |
| [AI-guided setup](docs/setup-prompt.md) | One prompt that has a coding agent walk you through setup. |
| [How it works](docs/how-it-works.md) | Architecture and data flow. |
| [Importing from X](docs/importing-x.md) | Credentials, folder discovery, cost table, Actions secrets. |
| [Compile runners](docs/compile-runners.md) | Choosing Codex / Claude / Gemini; adding a runner. |
| [Daily recap](docs/slack-recap.md) | The feed contract and delivery options. |
| [Web app](web/README.md) | Running the local management + recap UI. |
| [Upgrading your fork](docs/upgrading.md) | `git merge upstream/main` and why it never conflicts. |
| [`llms.txt`](llms.txt) | Dense agent-facing docset for coding agents working on this repo. |

## Retrieval skill

`skill/my-knowledge/` teaches a coding agent to answer from your compiled wiki
with navigation-first reads and mandatory citations — "use my marketing
knowledge" from any project. See [its README](skill/my-knowledge/README.md).

## License

MIT.
