# Samples

Demo content for a fresh instance, mirroring the live repo layout:

- `raw/bookmarks/getting-started/` — four synthetic posts (clearly fake ids,
  authored for this repo) showing the raw bookmark format.
- `wiki/` — the compiled form of those posts: faithful source notes plus one
  concept article where every claim cites a source. Passes `bin/lint.py`
  (enforced by `tests/test_samples.py`).
- `config/` — starting configs: a placeholder bookmark topic and four
  account mirrors (one voice per large AI lab) with recap labels.
- `recap-feed.json` — the recap feed those notes produce, generated with the
  real builder (`kb.recap_feed`); used by the web app preview in development.
  Its `generated` date is intentionally fixed (matching the newest sample
  note), so the web app correctly badges it **stale** — that's the freshness
  guard working, not a bug. A live instance gets a fresh feed from the daily
  `kb-recap-feed` workflow.
- `seed-accounts.sh` — fetches 5 real posts per default account (~$0.10 of
  pay-as-you-go reads). Run during launch assembly, after copying the configs.

During launch assembly these are copied into place in the fresh public repo
(`raw/`, `wiki/`, `config/`). They are NOT live data in a personal instance —
the pipeline never reads from `samples/`.
