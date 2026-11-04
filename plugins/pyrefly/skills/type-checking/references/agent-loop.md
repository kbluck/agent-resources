# Making the Check Automatic

The Pyrefly team found that a skill on its own does not reliably make an agent run the type checker before it finishes, even with a
description that says the check is mandatory
([Adding Pyrefly Type Checking to Your Agentic Loop](https://pyrefly.org/blog/pyrefly-agentic-loop/)). Two additions make it
dependable. Offer them when the user wants every task to end with a clean check; add them only when asked, since both change how
every future session in the project behaves.

Replace `pyrefly check` below with the project's own invocation (`uv run pyrefly check`, and so on).

## An `AGENTS.md` Directive

Instructions in `AGENTS.md` (or `CLAUDE.md`) load in every session, so they apply even when no skill triggers:

```markdown
## Type Checking

Before completing any task that creates or modifies Python files:

1. Run `pyrefly check` at the root of the project.
2. Fix every new type error. Do not suppress an error unless the code is correct and Pyrefly cannot see it.
3. Run `pyrefly check` again to confirm no new errors remain.
```

## A Claude Code `Stop` Hook

A hook runs every time, whether or not the agent remembers. A `Stop` hook runs when the agent tries to finish; exit code 2 sends
stderr back to the agent and keeps it working. Pyrefly writes errors to stdout, so redirect them. In `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "pyrefly check >&2 || exit 2",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

Points to settle with the user before adding it:

- **Pre-existing errors.** If the project does not already check clean, this hook blocks every session. Fix or baseline the existing
  errors first, or point the hook at a baseline (`pyrefly check --baseline baseline.json`).
- **Non-Python tasks.** The hook runs even when no Python changed. That is cheap when the project is clean, since Pyrefly is fast.
- **Timeout.** Size it for the whole project; large projects need more than the blog's 30 seconds.
- **Other agents.** Gemini CLI, Codex, and Kiro have their own hook formats; see their documentation.

A pre-commit hook or CI step that runs `pyrefly check` also gives the agent pushback when it commits, and covers human contributors
too. If the project already has one, the agent loop may need nothing more.
