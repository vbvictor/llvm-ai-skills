# llvm-ai-skills

Give AI assistants more knowledge to reason about the LLVM project codebase.

## Install

Install every enabled agent from `agents.json`:

```bash
./install_skills.sh
```

Install only Codex:

```bash
./install_skills.sh --agent codex
```

Install selected agents:

```bash
./install_skills.sh --agent claude --agent codex
```

Preview changes without writing symlinks:

```bash
./install_skills.sh --dry-run
```

List supported agents:

```bash
./install_skills.sh --list-agents
```

## Supported Agents

Supported agents live in `agents.json`. The installer currently supports agents
that load skills from directories containing `SKILL.md`.

- Claude installs to `${CLAUDE_HOME:-~/.claude}/skills`
- Codex installs to `${CODEX_HOME:-~/.codex}/skills`

The canonical source tree is `skills/`. The `.claude/skills` entries in this
repository are compatibility symlinks for existing Claude-oriented paths.

## Add an Agent

Add a new entry to `agents.json`:

```json
{
  "agents": {
    "example": {
      "display_name": "Example Agent",
      "home_env": "EXAMPLE_AGENT_HOME",
      "default_home": "~/.example-agent",
      "skills_subdir": "skills",
      "enabled": true
    }
  }
}
```

No installer code changes are needed for agents that use the same `SKILL.md`
directory layout.
