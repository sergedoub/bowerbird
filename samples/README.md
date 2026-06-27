# Samples

Demo content for a fresh instance, mirroring the live repo layout:

- `raw/bookmarks/getting-started/` — four synthetic posts (clearly fake ids,
  authored for this repo) showing the raw bookmark format.
- `wiki/` — the compiled form of those posts: faithful source notes plus one
  concept article where every claim cites a source. Passes `bin/lint.py`
  (enforced by `tests/test_samples.py`).
- `config/` — starting configs: a placeholder bookmark topic, four account
  mirrors (one voice per large AI lab), and a sample recap profile.
- `recaps/` — sample durable recap Markdown plus a delivery manifest. These are
  generated artifacts, not connector state; delivery adapters consume them.
- `seed-accounts.sh` — fetches 5 real posts per default account (~$0.10 of
  pay-as-you-go reads). Run during launch assembly, after copying the configs.

During launch assembly these are copied into place in the fresh public repo
(`raw/`, `wiki/`, `config/`). They are NOT live data in a personal instance —
the pipeline never reads from `samples/`.
