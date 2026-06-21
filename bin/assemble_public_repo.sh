#!/usr/bin/env bash
# Assemble the fresh-history public Bowerbird repo from this working tree.
#
# Copies code paths verbatim, swaps personal data paths for samples/, and
# excludes everything personal. Produces a git repo with ONE initial commit
# and no history. Usage:
#
#   bash bin/assemble_public_repo.sh /tmp/bowerbird-public
#
# Then review the private source-side docs/launch-checklist.md, run the audit,
# create or update sergedoub/bowerbird, and push.
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:?usage: assemble_public_repo.sh <target-dir>}"

if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "refusing to write into non-empty $TARGET" >&2
  exit 1
fi
mkdir -p "$TARGET"

# Code paths ship verbatim. Data paths (raw/, wiki/, config/,
# compile/recap-feed.json) are NOT copied — samples take their place below.
SHIP=(
  README.md LICENSE AGENTS.md CLAUDE.md llms.txt pyproject.toml .gitignore
  bin src tests compile/INSTRUCTIONS.md compile/PROMPT.md
  .github .agents .claude/skills skill samples web docs
)

for item in "${SHIP[@]}"; do
  src="$ROOT/$item"
  [ -e "$src" ] || { echo "missing: $item" >&2; exit 1; }
  mkdir -p "$TARGET/$(dirname "$item")"
  if [ "$item" = "web" ]; then
    mkdir -p "$TARGET/web"
    (cd "$ROOT/web" && tar --exclude './node_modules' --exclude './.next' -cf - .) \
      | (cd "$TARGET/web" && tar -xf -)
  else
    cp -R "$src" "$TARGET/$item"
  fi
done

# Personal/local material that must not ship even though it lives in shipped dirs.
rm -rf "$TARGET/docs/reviews" "$TARGET/docs/launch-checklist.md" "$TARGET/docs/rehearsal-prompt.md"
rm -rf "$TARGET/web/node_modules" "$TARGET/web/.next"
rm -f  "$TARGET/bin/.env" "$TARGET/bin/.x_tokens.json"

# Samples become the live starting data.
mkdir -p "$TARGET/config" "$TARGET/compile" "$TARGET/raw" "$TARGET/wiki"
cp "$ROOT/samples/config/topics.toml"   "$TARGET/config/topics.toml"
cp "$ROOT/samples/config/accounts.toml" "$TARGET/config/accounts.toml"
cp "$ROOT/samples/recap-feed.json"      "$TARGET/compile/recap-feed.json"
cp -R "$ROOT/samples/raw/."             "$TARGET/raw/"
cp -R "$ROOT/samples/wiki/."            "$TARGET/wiki/"
cp "$ROOT/samples/wiki/index.md"        "$TARGET/index.md"

cd "$TARGET"
git init -q -b main   # the workflows assume the default branch is main
git add -A
# Neutral, push-safe identity: a personal default email here may be private,
# and GitHub rejects pushes that would expose one (GH007).
git -c user.name="github-actions[bot]" \
    -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit -q -m "Bowerbird: initial public release"

echo "assembled at $TARGET"
echo
echo "verify:"
(cd "$TARGET" && python3 -m pip install -qe '.[dev]' >/dev/null 2>&1 || true)
(cd "$TARGET" && python3 bin/lint.py)
echo
echo "next: from the source checkout, work through docs/launch-checklist.md against $TARGET before pushing."
