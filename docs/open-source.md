# Publishing A Bowerbird Instance

The Bowerbird source repo is meant to stay clean and public: code, docs,
workflow scaffolding, prompt files, connector setup assets, and empty config
templates.

A Bowerbird instance repo is different. It can contain private raw material,
compiled wiki notes, recap files, selected account handles, Slack destinations,
and workflow choices. Personal instances should be private repos created from
the public source, not GitHub forks: forks of public repositories are public.
Use this checklist before making an instance or demo data repo public.

## Default Recommendation

Keep your personal Bowerbird instance private.

If you want public examples, publish a separate data/demo repository such as
[bowerbird-demo](https://github.com/sergedoub/bowerbird-demo). That repo can
show the shape of `raw/`, `wiki/`, and `recaps/` without copying generated data
back into the product source repo.

## Source Repo Vs Instance Repo

| Repo type | Should contain | Should not contain |
| --- | --- | --- |
| Source repo | Product code, setup docs, workflows, prompts, empty config templates. | Personal raw data, compiled wiki output, generated recap files, real account selections, Slack destinations. |
| Personal instance | Your chosen config plus generated `raw/`, `wiki/`, and `recaps/`. | Public secrets or data you do not intend to share. |
| Demo/data repo | Intentional public example output. | Product-only source changes that belong upstream. |

## Review Before Publishing An Instance

| Path | Risk | Public-safe action |
| --- | --- | --- |
| `raw/bookmarks/` | Reveals saved posts and curation choices. | Publish only if the selection is intentional public data. |
| `raw/accounts/` | Reveals followed handles and mirrored post history. | Publish only if those account mirrors are intentional public data. |
| `raw/books/` | May contain copyrighted or private source material. | Do not publish unless you have rights to the text. |
| `raw/notes/` | Often contains first-party private notes. | Redact or keep private by default. |
| `raw/clips/` | May include copied web/API content. | Confirm licensing, privacy, and attribution. |
| `wiki/` | Compiled claims expose source choices and synthesis. | Publish only if the whole compiled knowledge base is intended public. |
| `recaps/` | Recap bodies can reveal source paths and delivery intent. | Publish only intentional public recaps. |
| `config/*.toml` | Can reveal folder IDs, handles, topics, model choices, and destinations. | Replace private IDs/destinations with placeholders or demo values. |

## Secrets

Never publish secret values:

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_TOKENS`
- `X_BEARER_TOKEN`
- `GH_PAT`
- `CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`
- Slack bot tokens, webhook URLs, or connector-runtime credentials

The repo ignores local secret files:

```text
bin/.env
.env
*.x_tokens.json
bin/.x_tokens.json
```

Still check history before publishing. If a secret was ever committed, rotate it
before making the repo public.

## GitHub Actions

Before making an instance public, review Actions settings and logs:

1. The canonical source repository `sergedoub/bowerbird` must never run
   personal ingest, compile, recap, or secret-push operations. The mutating
   workflows contain an explicit `github.repository != 'sergedoub/bowerbird'`
   guard, and local commands such as `bin/compile.sh` and `bowerbird
   push-secrets` refuse to run against that repository identity.
2. Keep `BOWERBIRD_LIVE_INSTANCE` unset or `false` unless the repo is an
   installed instance that should actively run paid personal ingest workflows.
3. Remove or rotate secrets that were used only for private setup.
4. Check workflow logs for pasted tokens, private channel names, or accidental
   raw content.
5. Confirm recap delivery targets in `config/recaps.toml` are public-safe.

## Final Checks

Run a direct scan before publishing:

```bash
rg -n "xoxb-|ghp_|github_pat_|OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|X_BEARER_TOKEN|X_TOKENS|SLACK_BOT_TOKEN" .
python3 -m pytest
python3 bin/lint.py
python3 bin/doctor.py --json
```

The shortest public positioning:

> Bowerbird is a file-first personal knowledge-base pipeline that imports X
> bookmarks and selected X accounts, compiles them into a cited markdown wiki,
> and emits durable recap files for Slack and other delivery adapters.
