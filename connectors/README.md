# Connectors

Connectors are agent-facing playbooks for services that consume Bowerbird
artifacts. They are not web pages and they are not runtime code in this repo.

Bowerbird's stable handoff is file-first:

```text
compile/recap-feed.json
```

A connector agent reads that file, checks freshness, performs any service setup
the user approves, and owns the external schedule and delivery credentials.

## Included Connectors

| Connector | Purpose |
| --- | --- |
| [Slack](slack/README.md) | Send one daily recap to a Slack channel, DM, or App Home. |

## Connector Rules

- Read deterministic repo artifacts; do not infer state from chat history.
- Keep service credentials in the connector runtime or the user's secret store,
  not in tracked repo files.
- Post at most one daily recap from a fresh `compile/recap-feed.json`.
- Keep setup verifiable: list required scopes, secrets, target IDs, schedule,
  and one explicit acceptance test.
- Prefer browser-assisted service setup when no public app-provisioning API
  exists.

Use [TEMPLATE.md](TEMPLATE.md) when adding another connector.
