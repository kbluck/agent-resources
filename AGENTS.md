# AGENTS.md

This repository is a plugin marketplace of agent skills, and later hooks, MCP servers, and LSP servers, for Claude Code, GitHub
Copilot, Codex, Cursor, and Gemini CLI. The skills can also be installed one by one with a CLI such as `npx skills` or
`bunx skills`.

Each plugin lives in `plugins/<plugin>/`, with its skills in `plugins/<plugin>/skills/<skill>/SKILL.md` and one manifest per
harness. The marketplace files at the repository root list every plugin. Read [docs/plugins.md](docs/plugins.md) before adding a
plugin, changing a manifest, or adding hooks, MCP servers, or LSP servers.

- Keep every manifest of a plugin in agreement: the same `name`, `version`, and `description` in all five, and an entry in all four
  marketplace files. Run `python3 -m unittest discover -s tests` and `claude plugin validate .` after any manifest change.
- Bump `version` in all of a plugin's manifests when releasing a change, or Claude Code and Codex users will not receive it.
- Never create `plugins/<plugin>/hooks/hooks.json`. Claude Code, Codex, Cursor, and Gemini CLI all read that path, each with
  different event names.

Use the `skill-creator` skill to create new skills, modify and improve existing skills, and measure skill performance.

Use the [agent-skills](https://agentskills.io/mcp) MCP server for additional guidance on the best practices for creating, improving,
and measuring agent skills.
