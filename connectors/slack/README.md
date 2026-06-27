# Slack Connector

The Slack connector posts generated Bowerbird recap files into Slack as the
dedicated Bowerbird Slack app. Bowerbird creates recap knowledge in `recaps/`;
the connector only delivers it.

This directory contains setup instructions and the Slack app manifest. The
bundled runtime code lives with the rest of the pipeline:

- `bin/slack_recap.py` is the CLI/GitHub Actions entry point.
- `src/bowerbird/slack_delivery.py` contains the Slack Web API delivery logic.

The bundled public path is GitHub Actions: `.github/workflows/recap.yml`
generates and commits recap files, then `bin/slack_recap.py` posts each Slack
delivery entry using `SLACK_BOT_TOKEN`. External connector runtimes can use the
same manifest contract, but public setup should prove the bundled path first.

## What The Agent Needs

- Repo read access to `recaps/manifests/*.json` and the listed recap files.
- A Slack workspace where the user can create or install apps.
- A dedicated Slack app named `Bowerbird`.
- A bot user named `bowerbird`.
- A Bot User OAuth Token stored as the `SLACK_BOT_TOKEN` GitHub Actions secret
  or, for an external runtime, that runtime's secret store. Never commit it.
- Recommended bot scope: `chat:write.public`.
- Minimum bot scope when the bot is invited to each destination: `chat:write`.
- One or more destinations from `config/recaps.toml`. Destinations may be
  channel IDs, DM IDs, or any value the runtime adapter supports. Prefer channel
  IDs because channel names can be renamed and are ambiguous across Slack views.

Do not post from the user's personal Slack account. Do not use a user token or
an unrelated Slack app as the Bowerbird identity. External automation may
orchestrate delivery, but Slack messages should still be sent by the Bowerbird
bot integration.

Slack references:

- [`chat.postMessage`](https://docs.slack.dev/reference/methods/chat.postMessage/)
- [Slack GitHub Action](https://docs.slack.dev/tools/slack-github-action/)

## Setup Playbook

1. Ask the user which Slack workspace and destination to use.
2. Create or configure the dedicated Slack app named `Bowerbird`.
   - Assume the user does not have a Slack app configuration token.
   - Open <https://api.slack.com/apps> in the user's browser session and create
     the app from `connectors/slack/manifest.json`.
   - Do not ask for a Slack app configuration token during normal setup. Only
     use Slack's App Manifest API if the user proactively says they already
     have the right token for this workspace.
   - Do not use the Codex/ChatGPT Slack connector as the Bowerbird app.
3. Configure a bot user and add the bot scope from
   `connectors/slack/manifest.json`.
4. Install the app to the workspace. This is an expected human/admin approval
   boundary.
5. Copy the Bot User OAuth Token into `bin/.env` as `SLACK_BOT_TOKEN`, then run
   `bowerbird push-secrets`. Verify by secret name only that `gh secret list`
   includes `SLACK_BOT_TOKEN`.
6. Record non-secret destinations in `config/recaps.toml` under the relevant
   profile's `[[recaps.deliveries]]` entries. Use the Slack channel or DM ID
   when possible:

   ```toml
   [[recaps.deliveries]]
   type = "slack"
   destination = "C0123456789"
   ```

7. Run `bowerbird recap` manually or let `.github/workflows/recap.yml` generate
   and commit recap files. The workflow then runs `bin/slack_recap.py`; a missing
   token fails the delivery step instead of silently reporting success.

If `chat.postMessage` returns `not_in_channel` and you are using only
`chat:write`, invite the `Bowerbird` bot to that channel and retry once. Use
`chat:write.public` when public channel posting without per-channel invites is
the intended setup.

## Runtime Contract

Every delivery run must:

1. Read the latest relevant `recaps/manifests/<run-date>.json`.
2. For each manifest entry with a Slack delivery target, read the listed recap
   file from the same checkout or fetched default branch.
3. Verify the recap frontmatter has `type: Recap`.
4. Post the existing recap body with `chat.postMessage` as the `Bowerbird` bot.
5. Log the profile, file, destination, and Slack response ID.

The connector must not synthesize, summarize, or rewrite the recap. It may adapt
transport details such as splitting an oversized Slack message, but the source
content remains the generated recap file.

## External Adapter Variant

For another connector runtime, watch or fetch the committed
`recaps/manifests/<run-date>.json` file after `.github/workflows/recap.yml`
commits `recaps/`. The external adapter reads the manifest, posts through the
narrow Bowerbird Slack integration, and records delivery status in its own logs.
The Slack identity remains the Bowerbird app, not the orchestrator's Slack app.

## Acceptance Test

- Run `bowerbird doctor` in the checkout; config, recaps, and lint must be OK.
- Generate a recap with `bowerbird recap --deterministic --force` in a test
  branch or use an existing committed recap file.
- Trigger the connector once manually with `bowerbird slack-recap`, or dispatch
  the `recap` workflow and inspect its `Deliver Slack recaps` step.
- Confirm exactly one Slack message appears in the configured channel, DM, or
  App Home from the `Bowerbird` app/bot identity.
- Confirm the connector log records the profile, recap file, destination, and
  Slack timestamp.
