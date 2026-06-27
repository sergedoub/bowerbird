# Importing From X

This repo supports two X import paths:

- Bookmark folders: import posts you saved into specific X bookmark folders.
- Account mirrors: import posts and replies from selected public accounts.

Both paths write append-only markdown under `raw/` and are safe to rerun.

## Credentials

Create an X developer app and provide credentials through environment variables
or a gitignored `bin/.env` file.

Bookmark folder imports use OAuth2 user-context auth:

```env
X_CLIENT_ID=...
X_CLIENT_SECRET=...
X_REDIRECT_URI=http://bowerbird.localhost:8080/callback
X_SCOPES=bookmark.read tweet.read users.read offline.access
X_USER_ID=...
```

Account mirrors use app-only bearer auth:

```env
X_BEARER_TOKEN=...
```

Local token files are intentionally ignored by git:

```text
bin/.env
.env
*.x_tokens.json
bin/.x_tokens.json
```

## Discover Bookmark Folder IDs

Authorize once (opens a browser window):

```bash
bowerbird auth
```

List your bookmark folders with their ids:

```bash
bowerbird folders
```

If you are considering a full-folder import, ask Bowerbird to count first:

```bash
bowerbird folders --counts
```

X's folder-contents endpoint does not expose a free total-count field; this
command walks the folder ID pages, so it can consume billable reads before any
content is hydrated.

Copy the folder IDs into `config/topics.toml`. (`bowerbird auth me` shows the
authenticated user; `bowerbird auth get <path>` issues raw API calls if you
need to poke further.)

## Configure Bookmark Imports

Each topic maps to one or more X bookmark folder IDs:

```toml
[topics.marketing]
folder_ids = ["1234567890123456789"]
```

Run one topic:

```bash
python3 bin/pull.py --topic marketing
```

For a setup smoke import, cap each selected folder to its latest three returned
items:

```bash
python3 bin/pull.py --limit-per-folder 3
```

To import all current items from each selected folder, omit the cap:

```bash
python3 bin/pull.py
```

Daily scheduled pulls use a safer forward-only mode:

```bash
python3 bin/pull.py --stop-at-existing
```

That walks newest-first in each folder and stops when it reaches a bookmark
already present in `raw/bookmarks/`, so it collects newer items without
quietly draining older folder history.

The importer writes:

```text
raw/bookmarks/<topic>/<YYYY-MM-DD>__<tweet-id>.md
```

## Configure Account Mirrors

Each account mirror maps a handle to the topic where compiled notes should land:

```bash
bowerbird accounts add example_handle --topic claude-code
```

```toml
[[handles]]
handle = "example_handle"
topic = "claude-code"
off_topic = "skip"
```

Run all configured accounts over the default trailing window:

```bash
python3 bin/dump_account.py
```

Run one account explicitly:

```bash
python3 bin/dump_account.py --handle example_handle --days 3
```

Or dispatch the targeted GitHub Actions version:

```bash
gh workflow run account-dump.yml -f handle=example_handle -f days=3
```

The importer writes:

```text
raw/accounts/<handle>/<YYYY-MM-DD>__<tweet-id>.md
```

The compile step later routes account-derived source notes to
`wiki/<topic>/sources/` and adds `mirror: accounts/<handle>` in frontmatter.

## API Costs (Pay-As-You-Go)

X's pay-as-you-go pricing bills per read: roughly $0.001 per "owned read" (your
own bookmarks) and $0.005 per general post read (timelines, search). No monthly
subscription is required. Rough per-operation costs:

| Operation | Reads | Approx cost |
| --- | --- | --- |
| Folder count estimate | Walks returned IDs for selected folders, no hydration | Owned-read rate when eligible |
| Setup bookmark smoke import | Up to 3 returned items per selected folder, plus any thread reconstruction | Budget up to $0.005/post read |
| Daily bookmark pull | A few owned reads per new bookmark | Well under $0.01/day |
| Thread reconstruction | One search per thread head; bills per post in the conversation | $0.005 × thread length |

Thread reconstruction tries full-archive search first and automatically falls
back to recent search (last 7 days) if your API plan rejects full-archive with
a 403. Bookmarks are usually fresh, so recent search reconstructs most threads;
the pull summary prints which `search_mode` was used.

| Daily account mirror | One page (up to 100 posts) per quiet account per day | ≤ $0.50/account/day, usually far less |
| `dump_account.py --full` | Up to ~3,200 posts per account | Up to ~$16/account |
| `backfill.py` | One read per historical bookmark, plus threads | Depends on archive size; use `--no-threads` first |

The account mirror stops paging at the first page that contains only
already-downloaded posts, so a daily run over a quiet window costs one page of
reads, not the whole window. Full-history runs (`--full`) never stop early.
Importers print an approximate cost line after each run. Consider setting a
spend limit in the X developer portal as a backstop.

## GitHub Actions

The built-in workflows assume these secrets:

| Secret | Used by | Purpose |
| --- | --- | --- |
| `X_CLIENT_ID` | `pull-bookmarks` | OAuth2 app client ID. |
| `X_CLIENT_SECRET` | `pull-bookmarks` | OAuth2 app client secret when using a confidential client. |
| `X_TOKENS` | `pull-bookmarks` | Serialized OAuth2 token JSON. The refresh token may rotate. |
| `GH_PAT` | `pull-bookmarks` | Fine-grained token used to persist rotated `X_TOKENS`. |
| `X_BEARER_TOKEN` | `pull-bookmarks`, `account-dump` | App-only bearer token for search/timeline calls. |
| `OPENAI_API_KEY` | `compile-wiki`, `recap` | Default hosted compile/recap credential for the Codex/OpenAI path. |
| `CODEX_ACCESS_TOKEN` | `compile-wiki` | Optional Enterprise Codex access token alternative. |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | `compile-wiki`, `recap` | Alternative hosted compile/recap credentials when selected in `config/models.toml`. |

Manual setup dispatch accepts `limit_per_folder` and `import_all` inputs on
`pull-bookmarks`; use `limit_per_folder=3` for the first run. Use
`import_all=true` only after the user explicitly asks for full folder history.
`account-dump` accepts optional `handle`, `days`, and `max_posts` inputs for
targeted account imports. Scheduled runs use forward-only stop-at-existing
behavior.

The default schedule is:

| Workflow | Schedule | Output |
| --- | --- | --- |
| `account-dump` | Daily | `raw/accounts/` commits. |
| `pull-bookmarks` | Daily | `raw/bookmarks/` commits. |
| `compile-wiki` | After either importer succeeds | `wiki/` commits. |
| `recap` | Daily or after compile succeeds | `recaps/` commits. |

If you fork this repo, adjust the cron times to match your timezone and expected
compile duration.
