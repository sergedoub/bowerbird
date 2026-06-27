# Installing the Bowerbird skill

This skill teaches a coding agent (Claude Code or compatible) to retrieve from your
compiled Bowerbird wiki with navigation-first reads and mandatory source citations.

Used inside this repo, it works as-is — the skill auto-detects the checkout.

To use it globally (so `$bowerbird`, "use Bowerbird", or "use my marketing
knowledge" works in any project), copy it into your agent's global skills
directory as `bowerbird`.

For Claude Code, use `~/.claude/skills`; for Codex, use `~/.codex/skills`.

```bash
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"
rm -rf "$SKILLS_DIR/my-knowledge"
cp -R skill/bowerbird "$SKILLS_DIR/bowerbird"
```

Then edit one line in `$SKILLS_DIR/bowerbird/SKILL.md` under **Setup**,
pointing it at your checkout:

```text
- Bowerbird checkout: `~/path/to/your/bowerbird`
```

Migration note: remove any old globally installed `my-knowledge` skill before
installing `bowerbird`. Do not keep both packages; the Bowerbird skill already
keeps natural-language compatibility with "use my knowledge" requests.

That's the only configuration. The skill reads real files and cites author + URL
for every curated claim; if your wiki has nothing relevant, it says so instead
of inventing curated knowledge.
