# Agent Resources

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)
[![Agent Skills](https://img.shields.io/badge/format-Agent%20Skills-8A2BE2)](https://agentskills.io)

Portable [Agent Skills](https://agentskills.io) for Claude Code and other coding agents: Git branches and commits that follow the
conventions, and Markdown that is easy to read and lint-clean.

[Skills](#skills) • [Installation](#installation) • [Usage](#usage) • [Development](#development)

Each skill is a folder with a `SKILL.md` file and, where useful, reference material and scripts that the agent loads only when it
needs them. They work in any agent that supports the Agent Skills format, and install with one command. They were written for my own
projects, but anyone who finds them useful is welcome to them.

## Skills

> [!NOTE]
> Every skill defers to the repository it runs in. A contributing guide, `commitlint` config, or existing linter setup always wins
> over the skill's defaults.

## Installation

Install with the [`skills`](https://github.com/vercel-labs/skills) CLI, using `bunx` or `npx`. The CLI asks which skills to install
and which agents to install them for:

```shell
bunx skills add kbluck/agent-resources
```

To pick skills or agents up front, or install for your user account rather than the current project:

```shell
# Every skill for every detected agent, no prompts
bunx skills add kbluck/agent-resources --all

# User-level install, available in all projects
bunx skills add kbluck/agent-resources --global

# See what is available without installing
bunx skills add kbluck/agent-resources --list
```

Keep them current with `bunx skills update`.

> [!TIP]
> Installed skills are recorded in `skills-lock.json`. Commit it, and teammates can restore the same set with
> `bunx skills experimental_install`.

## Usage

Skills load on their own when a request matches their description, so there is nothing to call explicitly. Ask the way you normally
would.

## Development

Published skills live in `skills/`. The skills this repository uses on itself, including `skill-creator` for building and evaluating
new skills, are listed in `skills-lock.json` and installed into `.agents/skills/`.

```text
skills/
```

Restore the development skills, run the tests, and lint the Markdown:

```shell
bunx skills experimental_install
uvx rumdl check .
```

> [!IMPORTANT]
> New skills follow the [Agent Skills specification](https://agentskills.io): a `SKILL.md` with `name` and `description`
> frontmatter, where the description says both what the skill does and when to use it. The
> [agent-skills MCP server](https://agentskills.io/mcp) configured in `.mcp.json` has more guidance on writing and measuring them.
