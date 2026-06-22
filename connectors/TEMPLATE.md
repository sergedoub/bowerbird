# Connector Template

## Purpose

State the service, the Bowerbird artifact it consumes, and the user-visible
outcome.

## Inputs

- Bowerbird artifact:
- Required repo access:
- Required service account or app:
- Required runtime secrets:
- User choices:

## Setup Playbook

1. Confirm the target service account/workspace.
2. Create or select the dedicated service app.
3. Configure the minimum scopes/permissions.
4. Install or authorize the app.
5. Store credentials in the connector runtime or user secret store.
6. Record the target destination and schedule.

## Runtime Contract

- Read:
- Freshness guard:
- Message or action shape:
- Delivery cadence:
- Duplicate prevention:

## Acceptance Test

- Command or agent prompt:
- Expected service-side result:
- Expected logs:

## Failure Modes

- Missing artifact:
- Stale artifact:
- Missing permission:
- Invalid destination:
- Service API failure:
