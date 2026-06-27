# Bowerbird

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
- **Display** — durable recap files of what's new, delivered by adapters such
  as the bundled Slack bot-token workflow, email, or Guild.

The design is deliberately simple: Python 3.11+ with a stdlib-only runtime,
markdown files as the database, your GitHub fork as the storage and compute
(GitHub Actions), no RAG, no embeddings, no vector store. Everything runs on
credentials you own — your X developer app, your LLM key, and your connector
services.

The public source repo is clean product code and setup scaffolding. It does not
ship pre-ingested `raw/`, compiled `wiki/`, or generated `recaps/` data. A
separate [bowerbird-demo](https://github.com/sergedoub/bowerbird-demo) repo is
reserved for generated output examples, independent from the source.

## Quick start

> **Using Codex, Claude Code, or another coding agent?** Skip every manual
> step. Already cloned? Run the repo's guided setup skill. Not cloned yet?
> Paste the one prompt in [docs/setup-prompt.md](docs/setup-prompt.md) into
> your agent from anywhere; it forks, clones, and walks you through the entire
> setup, end to end.

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
   which folders Bowerbird watches, optional topic recap profiles, which
   accounts it follows, and setting the GitHub Actions secrets (automatic when
   the `gh` CLI is installed).
3. **Enable GitHub Actions** on your fork and run `pull-bookmarks` once with
   `limit_per_folder=3`. If you configured account mirrors, run `account-dump`
   once manually too. Later account adds use
   `bowerbird accounts add <handle> --topic <topic>` plus a targeted
   `account-dump` dispatch with `handle=<handle>`, `days=3`. The compile chains
   automatically; `bowerbird lint` must print `provenance and recaps OK` and
   `bowerbird doctor` should report healthy config/recap/lint status.
4. **Generate and deliver recaps.** `bowerbird recap` writes durable Markdown
   files under `recaps/` plus a manifest under `recaps/manifests/`. Start with
   the [Slack connector](connectors/slack/README.md): create the dedicated
   Bowerbird app, store `SLACK_BOT_TOKEN` as a secret, keep channel IDs in
   `config/recaps.toml`, and verify one bot post with a Slack timestamp.

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
bowerbird accounts add <handle> --topic <topic>
bowerbird dump-account --handle <h> --days 3
bowerbird backfill --topic <t> --no-threads
bowerbird models     # choose compile + recap provider/model
bowerbird recap      # generate durable recap files + delivery manifest
bowerbird slack-recap # post manifest-listed Slack recaps with SLACK_BOT_TOKEN
bowerbird lint       # provenance + recap guardrail
bowerbird doctor     # config, recap files, and lint status

# advanced / optional
bowerbird push-secrets # push staged credentials; marks the repo live when ingest secrets are complete
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
| [Daily recap](docs/slack-recap.md) | File-first recap generation and delivery options. |
| [Connectors](connectors/README.md) | Agent playbooks for delivery services, starting with Slack. |
| [Upgrading your fork](docs/upgrading.md) | `git merge upstream/main` and why it never conflicts. |
| [`llms.txt`](llms.txt) | Dense agent-facing docset for coding agents working on this repo. |

## Retrieval skill

`skill/my-knowledge/` teaches a coding agent to answer from your compiled wiki
with navigation-first reads and mandatory citations — "use my marketing
knowledge" from any project. See [its README](skill/my-knowledge/README.md).

## License

MIT.
