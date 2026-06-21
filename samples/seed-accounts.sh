#!/usr/bin/env bash
# Seed the accounts lane with real posts: 5 newest posts per default handle.
#
# Run during launch assembly, AFTER samples/config/accounts.toml has been copied to
# config/accounts.toml. Requires X_BEARER_TOKEN (env or bin/.env). Cost: 4 handles x 5
# posts x $0.005 = ~$0.10 of pay-as-you-go reads.
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for handle in thsottiaux bcherny OfficialLoganK santiagomed; do
  python3 bin/dump_account.py --handle "$handle" --full --max-posts 5
done

echo "seeded. Run a compile (bash bin/compile.sh && python3 bin/lint.py) to distill these into wiki notes."
