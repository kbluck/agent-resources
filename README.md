# Agent Resources

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)
[![Agent Skills](https://img.shields.io/badge/format-Agent%20Skills-8A2BE2)](https://agentskills.io)
[![Agent Plugins](https://img.shields.io/badge/format-Agent%20Plugins-8A2BE2)](https://agent-plugins.org)

Portable [Agent Skills](https://agentskills.io) for Claude Code and other coding agents: Git branches and commits that follow the
conventions, and Markdown that is easy to read and lint-clean.

[Plugins](#plugins) • [Installation](#installation) • [Usage](#usage) • [Development](#development)

Each skill is a folder with a `SKILL.md` file and, where useful, reference material and scripts that the agent loads only when it
needs them. Related skills are bundled into plugins, and the repository is a plugin marketplace that Claude Code, GitHub Copilot,
Codex, Cursor, and Gemini CLI can install from. Any other agent that supports the Agent Skills format can install the skills one by
one. They were written for my own projects, but anyone who finds them useful is welcome to them.

## Plugins

Each plugin bundles a pair of skills designed to work together.

> [!NOTE]
> Every skill defers to the repository it runs in. A contributing guide, `commitlint` config, or existing linter setup always wins
> over the skill's defaults.

## Installation

Every harness below installs from the same marketplace, `kbluck-agent-resources`. Add it once, then install the plugins you want by
name.

### Claude Code

```bash
claude plugin marketplace add kbluck/agent-resources
claude plugin install git@kbluck-agent-resources
```

Inside a session, `/plugin marketplace add kbluck/agent-resources` and `/plugin install git@kbluck-agent-resources` do the same.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add kbluck/agent-resources
copilot plugin install git@kbluck-agent-resources
```

In VS Code, enable `chat.plugins.enabled`, add `kbluck/agent-resources` to `chat.plugins.marketplaces` in your user settings, and
install from the `@agentPlugins` view in Extensions.

### Codex

```bash
codex plugin marketplace add kbluck/agent-resources
codex plugin add git@kbluck-agent-resources
```

### Cursor

In the Cursor dashboard, open Plugins & MCPs, choose Add Marketplace under Team Marketplaces, select Import from Repo, and paste
`https://github.com/kbluck/agent-resources`. To try a plugin locally instead, copy its folder to `~/.cursor/plugins/local/` and
reload the window.

### Gemini CLI

Gemini CLI installs one extension per repository root, so install each plugin from a local clone:

```bash
git clone https://github.com/kbluck/agent-resources.git
gemini extensions install ./agent-resources/plugins/git
```

To install a single skill without the rest of its plugin:

```bash
gemini skills install https://github.com/kbluck/agent-resources --path plugins/git/skills/commit
```

### Any Other Agent

The [`skills`](https://github.com/vercel-labs/skills) CLI installs individual skills into any agent that supports the Agent Skills
format. It asks which skills to install and which agents to install them for:

```bash
# Choose interactively
bunx skills add kbluck/agent-resources

# Every skill for every detected agent, no prompts
bunx skills add kbluck/agent-resources --all

# User-level install, available in all projects
bunx skills add kbluck/agent-resources --global

# See what is available without installing
bunx skills add kbluck/agent-resources --list
```

Keep them current with `bunx skills update`.

> [!TIP]
> The `skills` CLI records installed skills in `skills-lock.json`. Commit it, and teammates can restore the same set with
> `bunx skills experimental_install`.

## Usage

Skills load on their own when a request matches their description, so there is nothing to call explicitly. Ask the way you normally
would.

## Development

Each plugin lives in `plugins/`, with its skills in `skills/` and one small manifest per harness. The marketplace files at the root
list every plugin. [Plugin layout](docs/plugins.md) explains which harness reads which file, how to add a plugin, and where hooks,
MCP servers, and LSP servers go. The skills this repository uses on itself, including `skill-creator` for building and evaluating
new skills, are listed in `skills-lock.json` and installed into `.agents/skills/`.

```text
plugins/
```

Restore the development skills, run the tests, validate the plugins, and lint the Markdown:

```bash
bunx skills experimental_install
python3 -m unittest discover -s tests
claude plugin validate .
uvx rumdl check .
```

> [!IMPORTANT]
> New skills follow the [Agent Skills specification](https://agentskills.io): a `SKILL.md` with `name` and `description`
> frontmatter, where the description says both what the skill does and when to use it. The
> [agent-skills MCP server](https://agentskills.io/mcp) configured in `.mcp.json` has more guidance on writing and measuring them.
