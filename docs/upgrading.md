# Upgrading Your Fork

Your fork is both your copy of the code and your knowledge base: the pipeline
commits your data into it daily. You can never "re-fork to update" — instead,
updates flow in as a normal git merge:

```bash
git remote add upstream https://github.com/<upstream-org>/<upstream-repo>.git  # once
git fetch upstream
git merge upstream/main
git push
```

## Why the merge is conflict-free

The repo enforces a path-disjointness rule:

- **Code paths** — `src/`, `bin/`, `web/`, `tests/`, `compile/INSTRUCTIONS.md`,
  `compile/PROMPT.md`, `.github/`, `docs/`, `skill/` — are only ever changed by
  upstream. Your instance's automation never writes here.
- **Data paths** — `raw/`, `wiki/`, `config/`, `compile/recap-feed.json` — are
  only ever written by your instance (your imports, your compile, your config).
  Upstream never ships changes here beyond the initial examples.

Disjoint paths mean `git merge upstream/main` cannot conflict, no matter how
many daily data commits your fork has accumulated.

## Customization without divergence

Values you'd plausibly change live in **repository variables** (Settings →
Secrets and variables → Actions → Variables), not in workflow files:

| Variable | Default | Effect |
| --- | --- | --- |
| `COMPILE_RUNNER` | `claude` | Which agent CLI performs the compile (`claude` \| `codex` \| `gemini`). |
| `DUMP_WINDOW_DAYS` | `3` | Trailing window for the daily account mirror. |
| `X_USER_ID` | (empty) | Your numeric X user id; skips a `/users/me` lookup per pull run. |

## The one accepted divergence: cron schedules

GitHub Actions cannot read repository variables inside `schedule:` blocks, so
cron times are hard-coded in the workflow files. If you edit them (e.g. to
match your timezone), a future upstream change to the same lines would
conflict. This is accepted and easy to resolve: keep your line. Everything
else in the workflows should be left untouched.

## After merging

```bash
python3 -m pytest        # the suite is offline and fast
bowerbird lint           # provenance must stay green
```

If upstream added new repo variables or secrets, the release notes will say
so; `bowerbird init` can be re-run safely at any time — it never overwrites
your config without asking.
