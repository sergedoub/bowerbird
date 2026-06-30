# Bowerbird

**TL;DR:** simple personal knowledge automations built on Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
Google's new [Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing), and content ingestion from X and other
sources. Curated, fresh context your agents can use.

Bowerbird turns what you save into a personal, LLM-compiled markdown knowledge
base. Automatically ingest your X bookmarks, monitor and store every post from
an account, and that raw-source content gets synthesized and given to your
agents through connectors.

Examples:

1. Tell Bowerbird to monitor @karpathy and send a daily summary into Slack.
2. Bookmark an article on X and it is ingested, synthesized, and your Claude or
   ChatGPT uses a skill to reference it when relevant.

The design is deliberately simple: Python 3.11+ with a stdlib-only runtime,
markdown files as the database, your private GitHub instance repo as the storage
and compute (GitHub Actions), no RAG, no embeddings, no vector store. Everything runs on
credentials you own — your X developer app, your LLM key, and your connector
services.

## Quick start

> **Using Codex, Claude Code, or another coding agent?** Skip every manual
> step. Already in a private instance checkout? Run the repo's guided setup
> skill. Not cloned yet? Paste the one prompt in
> [docs/setup-prompt.md](docs/setup-prompt.md) into your agent from anywhere; it
> creates a private instance repo from this public source, clones it, and walks
> you through the entire setup, end to end.

1. **Create a private instance repo from this source repo** — do not use
   GitHub's Fork button for a personal Bowerbird instance. GitHub forks of a
   public repository are public, but your Bowerbird instance is where private
   raw material, compiled wiki output, and recap files accumulate.

   ```bash
   git clone https://github.com/sergedoub/bowerbird.git <your-instance-repo>
   cd <your-instance-repo>
   git remote rename origin upstream
   gh repo create <you>/<your-instance-repo> --private --source=. --remote=origin --push
   ```

   Without `gh`, create an empty private GitHub repo in the browser, add it as
   `origin`, then `git push -u origin main`.

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
3. **Enable GitHub Actions** on your private instance repo and run
   `pull-bookmarks` once with `limit_per_folder=3`. If you configured account
   mirrors, run `account-dump` once manually too. Later account adds use
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

## Retrieval skill

`skill/bowerbird/` teaches a coding agent to answer from your compiled OKF wiki
with navigation-first reads and mandatory citations. It can be invoked directly
with `$bowerbird` or "use Bowerbird", and it still understands natural-language
requests like "use my marketing knowledge." See [its README](skill/bowerbird/README.md).

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
bowerbird push-secrets # push staged credentials; mark repo live when ingest secrets are complete
bowerbird dump-all     # archive ALL bookmarks outside the pipeline
bowerbird ingest-book  # split a configured Markdown book into raw chapter inputs
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
| [Setup guide](docs/setup.md) | Private instance repo → wizard → green workflows. |
| [AI-guided setup](docs/setup-prompt.md) | One prompt that has a coding agent walk you through setup. |
| [How it works](docs/how-it-works.md) | Architecture and data flow. |
| [Importing from X](docs/importing-x.md) | Credentials, folder discovery, cost table, Actions secrets. |
| [Compile runners](docs/compile-runners.md) | Choosing Codex / Claude / Gemini; adding a runner. |
| [Daily recap](docs/slack-recap.md) | File-first recap generation and delivery options. |
| [Connectors](connectors/README.md) | Agent playbooks for delivery services, starting with Slack. |
| [Upgrading your instance](docs/upgrading.md) | `git merge upstream/main` and why it avoids conflicts. |
| [`llms.txt`](llms.txt) | Dense agent-facing docset for coding agents working on this repo. |

## License

MIT.
