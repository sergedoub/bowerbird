# Connectors

Connectors are agent-facing playbooks for services that consume Bowerbird
artifacts. The Slack connector also has a small bundled delivery adapter so
public setup can prove daily delivery without a separate runtime.

Bowerbird's stable handoff is file-first:

```text
recaps/<profile>/<YYYY-MM-DD>.md
recaps/manifests/<run-date>.json
```

A connector reads the manifest and listed recap files, performs any service
setup the user approves, and owns the service credential boundary.

## Included Connectors

| Connector | Purpose |
| --- | --- |
| [Slack](slack/README.md) | Send one daily recap to a Slack channel, DM, or App Home. |

## Connector Rules

- Read deterministic repo artifacts; do not infer state from chat history.
- Keep service credentials in GitHub Actions secrets, the connector runtime, or
  the user's secret store, not in tracked repo files.
- Deliver generated recap files; do not synthesize new recap knowledge.
- Keep setup verifiable: list required scopes, secrets, target IDs, schedule,
  and one explicit acceptance test.
- Prefer browser-assisted service setup when no public app-provisioning API
  exists.

Use [TEMPLATE.md](TEMPLATE.md) when adding another connector.
