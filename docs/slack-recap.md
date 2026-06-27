# Daily Recaps

Bowerbird recaps are files first. Slack, email, or any other destination
consumes generated recap files; delivery is not where recap knowledge is made.
The bundled Slack path posts the generated files with the dedicated Bowerbird
bot token after the recap workflow commits them.

## Source Of Truth

The generated source of truth is:

```text
recaps/<profile>/<YYYY-MM-DD>.md
recaps/manifests/<run-date>.json
```

`bowerbird recap` reads active profiles from `config/recaps.toml`. Presence of a
profile means enabled. Each profile selects compiled lanes from
`wiki/*/sources/*.md`:

- `accounts`: compiled notes that came from `raw/accounts/<handle>/`.
- `topics`: compiled notes that came from bookmark folders or other topic input.

The calendar window is based on when source notes were added to the wiki in Git
history, not the original X post date. Daily profiles summarize the prior day.
Weekly profiles summarize the previous calendar week and default to Monday as
the due day unless `weekly_due_day` is set.

## File Contract

Generated Markdown files include `type: Recap` frontmatter with full provenance:

- profile, frequency, format, and calendar window
- selected account/topic lanes
- source note paths and totals
- prompt path
- model provider and model
- generated timestamp
- non-secret delivery targets

The human recap body should not include citations or source paths. Provenance
lives in frontmatter and in the manifest.

The default body style is intentionally compact:

- one title
- one tight line per selected account or topic lane
- one footer with total source-note counts, lane counts, and a short keyword or
  command strip

The recap prompt favors the freshest workflow, habit, command, loop, safety,
product, or GTM signal in each lane over a complete inventory of source notes.
If readers need the full trail, they should use the frontmatter and manifest
provenance to open the source notes.

The manifest is runtime-agnostic:

```json
{
  "type": "RecapManifest",
  "run_date": "2026-06-22",
  "generated_at": "2026-06-22T00:00:00+00:00",
  "recaps": [
    {
      "profile": "ai-accounts-daily",
      "file": "recaps/ai-accounts-daily/2026-06-21.md",
      "format": "slack_mrkdwn",
      "frequency": "daily",
      "window_start": "2026-06-21",
      "window_end": "2026-06-22",
      "totals": {
        "source_notes": 4,
        "account_lanes": 4,
        "topic_lanes": 0
      },
      "deliveries": [
        {
          "type": "slack",
          "destination": "C0123456789"
        }
      ]
    }
  ]
}
```

## Slack Delivery

Slack delivery reads the manifest, opens each listed recap file, and posts the
file body. It must not rescan the repo, infer freshness from filenames, or
synthesize a new recap.

Delivery identity is part of the contract:

- Use a dedicated Slack app named `Bowerbird`.
- Use the `bowerbird` bot user.
- Use `SLACK_BOT_TOKEN` from GitHub Actions secrets for the bundled workflow, or
  the equivalent secret in an external connector runtime.
- Recommend `chat:write.public` for public channel destinations; `chat:write`
  is enough when the bot is invited to every destination.
- Destinations live in `config/recaps.toml`, are copied into the manifest, and
  are passed through to Slack. Prefer channel IDs over channel names.

Do not post from the user's personal Slack account. Do not use an unrelated
Slack app as the Bowerbird Slack identity.

## Bundled GitHub Actions Adapter

The default public setup uses `.github/workflows/recap.yml`:

1. `bowerbird recap` writes `recaps/<profile>/<date>.md` and the manifest.
2. The workflow commits `recaps/`.
3. `bin/slack_recap.py` reads the manifest and posts Slack delivery entries
   with `SLACK_BOT_TOKEN`.
4. The step logs `profile`, recap file, destination, Slack channel, and Slack
   timestamp.

If a manifest contains Slack deliveries but `SLACK_BOT_TOKEN` is missing, the
delivery step fails. That is intentional: a green recap workflow should not mean
"Slack silently skipped" when the instance is configured for Slack.

## External Adapter

An external connector runtime can still own delivery orchestration. The shape
is:

1. `.github/workflows/recap.yml` runs `bowerbird recap` and commits `recaps/`.
2. The workflow triggers an adapter webhook with the manifest.
3. The adapter reads the manifest and recap files.
4. The adapter posts through a narrow Bowerbird `chat.postMessage` integration.
5. The adapter records delivery status in its own logs only.

Generation and delivery failures stay separate. If external delivery or Slack
delivery fails, the generated recap files remain valid and committed.
