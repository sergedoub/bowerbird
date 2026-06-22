# Slack Connector

The Slack connector sends one Bowerbird daily recap into a Slack channel, DM,
or App Home. The repo only produces `compile/recap-feed.json`; the connector
agent owns Slack setup, recap synthesis, scheduling, and posting.

## What The Agent Needs

- Repo read access to `compile/recap-feed.json`.
- A Slack workspace where the user can create or install apps.
- A dedicated Slack app named `Bowerbird Recap` or `Bowerbird <workspace>`.
- A bot token with `chat:write`.
- A destination:
  - channel ID such as `C123...` after inviting the bot to the channel, or
  - user ID / DM channel ID for a direct destination.

Slack references:

- [`chat.postMessage`](https://docs.slack.dev/reference/methods/chat.postMessage/)
- [Slack GitHub Action](https://docs.slack.dev/tools/slack-github-action/)

## Setup Playbook

1. Ask the user which Slack workspace and destination to use.
2. Open <https://api.slack.com/apps> in the user's browser session.
3. Create a new app from a manifest or from scratch.
4. Configure a bot user and add the minimum bot scope:

   ```yaml
   display_information:
     name: Bowerbird Recap
   features:
     bot_user:
       display_name: bowerbird
       always_online: false
   oauth_config:
     scopes:
       bot:
         - chat:write
   ```

5. Install the app to the workspace.
6. Copy the Bot User OAuth Token into the connector runtime's secret store.
   Do not commit it to this repo.
7. If posting to a channel, invite the bot to the channel and record the
   channel ID. If posting to a DM/App Home, record the user ID or DM channel ID.
8. Configure the connector runtime schedule to run after
   `.github/workflows/kb-recap-feed.yml` normally completes.

## Runtime Contract

Every scheduled run must:

1. Fetch `compile/recap-feed.json` from the default branch.
2. Stop without posting if the file is missing, invalid, or stale.
3. If `summary.total_new` is `0`, either post nothing or post one quiet
   no-change message, according to the user's connector setting.
4. Synthesize one concise Slack `mrkdwn` recap grouped by `accounts` and
   `topics`.
5. Send exactly one Slack message with `chat.postMessage`.
6. Log the feed date, total note count, destination, and Slack response ID.

Do not post GitHub Actions status messages, importer counts, or separate
partial recaps.

## Agent Prompt

Use this as the recurring connector task:

```text
Read compile/recap-feed.json from the Bowerbird repo. If generated is not
today's expected feed date, do not post and report the stale date. If
summary.total_new is 0, follow the configured quiet-day preference. Otherwise,
write one concise Slack mrkdwn recap grouped by Accounts and Bookmark Topics,
then send exactly one chat.postMessage to the configured Slack destination.
Log the feed date, total_new count, destination, and Slack timestamp.
```

## Acceptance Test

- Run `bowerbird doctor` in the checkout; config and lint must be OK, and the
  feed must be valid.
- Trigger the connector once manually.
- Confirm exactly one Slack message appears in the configured channel, DM, or
  App Home.
- Confirm the connector log records the feed date and Slack timestamp.

If the bundled sample feed is stale, the test run should send a clearly labeled
manual connector test message instead of pretending old source notes are new.
