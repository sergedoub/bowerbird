# Installing the my-knowledge skill

This skill teaches a coding agent (Claude Code or compatible) to retrieve from your
compiled wiki with navigation-first reads and mandatory source citations.

Used inside this repo, it works as-is — the skill auto-detects the checkout.

To use it globally (so "use my marketing knowledge" works in any project):

```bash
mkdir -p ~/.claude/skills
cp -R skill/my-knowledge ~/.claude/skills/my-knowledge
```

Then edit one line in `~/.claude/skills/my-knowledge/SKILL.md` under **Setup**,
pointing it at your checkout:

```text
- knowledge base checkout: `~/path/to/your/knowledge-base`
```

That's the only configuration. The skill reads real files and cites
author + url for every curated claim; if your wiki has nothing on a topic, it
says so instead of inventing curated knowledge.
