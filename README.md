# Agent Resources

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)
[![Agent Skills](https://img.shields.io/badge/format-Agent%20Skills-8A2BE2)](https://agentskills.io)
[![Agent Plugins](https://img.shields.io/badge/format-Agent%20Plugins-8A2BE2)](https://agent-plugins.org)

Portable [Agent Skills](https://agentskills.io) for Claude Code and other coding agents: Git branches and commits that follow the
conventions, Markdown that is easy to read and lint-clean, Python type checking and type coverage with Pyrefly, and
language-agnostic testing practice.

[Plugins](#plugins) • [Installation](#installation) • [Usage](#usage) • [Development](#development)

Each skill is a folder with a `SKILL.md` file and, where useful, reference material and scripts that the agent loads only when it
needs them. Related skills are bundled into plugins, and the repository is a plugin marketplace that Claude Code, GitHub Copilot,
Codex, Cursor, and Gemini CLI can install from. Any other agent that supports the Agent Skills format can install the skills one by
one. They were written for my own projects, but anyone who finds them useful is welcome to them.

## Plugins

Each plugin bundles skills designed to work together.

| Plugin | Skill | What it does | Requires |
| :----- | :---- | :----------- | :------- |
| `git` | [`branch`](plugins/git/skills/branch/SKILL.md) | Names, creates, checks, and renames branches following [Conventional Branch](https://conventionalbranch.org), without losing uncommitted work | Git 2.23+; Python 3 for the optional checker script |
| | [`commit`](plugins/git/skills/commit/SKILL.md) | Inspects the diff, groups changes into right-sized commits, and writes [Conventional Commits](https://www.conventionalcommits.org) messages that explain why | Git |
| `markdown` | [`authoring`](plugins/markdown/skills/authoring/SKILL.md) | Decides what each piece of a document becomes: table, GitHub alert, code block, Mermaid or ASCII diagram, or prose | |
| | [`formatting`](plugins/markdown/skills/formatting/SKILL.md) | Lints and fixes Markdown syntax with the project's own tool, falling back to [rumdl](https://github.com/rvben/rumdl) | uv, pipx, or Node.js to run rumdl |
| `pyrefly` | [`type-checking`](plugins/pyrefly/skills/type-checking/SKILL.md) | Runs [Pyrefly](https://pyrefly.org) on existing code, separates environment problems from real type errors, and fixes each error where the bug is | Pyrefly |
| | [`type-coverage`](plugins/pyrefly/skills/type-coverage/SKILL.md) | Brings a Python file or package to full annotation coverage under [Pyrefly](https://pyrefly.org) and locks it in with a stricter sub-config | Pyrefly |
| `software-testing` | [`best-practices`](plugins/software-testing/skills/best-practices/SKILL.md) | Writes tests that fail when behavior breaks: the right level, clear structure, isolation, and careful use of test doubles | The project's test runner |

In the first three plugins, one skill does the work and the other keeps it tidy: `branch` gets work off `main` and `commit` commits
it; `authoring` shapes the document and `formatting` lints it; `type-coverage` adds annotations and `type-checking` fixes type
errors in code as it is annotated now. In `software-testing`, `best-practices` shapes each test.

> [!NOTE]
> Every skill defers to the repository it runs in. A contributing guide, `commitlint` config, or existing linter setup always wins
> over the skill's defaults.

## Installation

Every harness below installs from the same marketplace, `kbluck-agent-resources`. Add it once, then install the plugins you want by
name. The examples install `git`; repeat the install for `markdown`, `pyrefly`, and `software-testing`.

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

# Specific skills only
bunx skills add kbluck/agent-resources --skill branch --skill commit

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
would:

| You say | Skill that loads |
| :------ | :--------------- |
| "Start a branch for the OAuth login work" | `branch` |
| "Commit this", or "split these changes into separate commits" | `commit` |
| "Write a README for this project" | `authoring`, then `formatting` |
| "rumdl is failing on the docs folder" | `formatting` |
| "CI's pyrefly step is red after my refactor" | `type-checking` |
| "Get `src/billing/invoice.py` fully typed with pyrefly" | `type-coverage` |
| "Add tests for the discount calculator" | `best-practices` |

In Claude Code, you can also invoke one directly by name. Plugin skills are namespaced by plugin, such as `/git:commit`; skills
installed with the `skills` CLI are not, such as `/commit`.

The `branch` skill's checker script also works on its own, for example in a CI step or Git hook:

```bash
python3 plugins/git/skills/branch/scripts/check_branch.py # current branch
python3 plugins/git/skills/branch/scripts/check_branch.py feature/add-login bad_name
python3 plugins/git/skills/branch/scripts/check_branch.py --allow-type docs docs/update-readme
```

It exits `0` when every name conforms, `1` when any does not (with the reason), and `2` on a usage or Git error.

## Development

Each plugin lives in `plugins/`, with its skills in `skills/` and one small manifest per harness. The marketplace files at the root
list every plugin. [Plugin layout](docs/plugins.md) explains which harness reads which file, how to add a plugin, and where hooks,
MCP servers, and LSP servers go. The skills this repository uses on itself, including `skill-creator` for building and evaluating
new skills, are listed in `skills-lock.json` and installed into `.agents/skills/`.

```text
plugins/
├── git/
│   └── skills/
│       ├── branch/        # Conventional Branch spec, examples, check_branch.py and its tests
│       └── commit/        # Conventional Commits spec, examples, splitting guide
├── markdown/
│   └── skills/
│       ├── authoring/     # Before/after rewrites for tables, alerts, code, diagrams
│       └── formatting/    # Default rumdl.toml, rule notes, tool setup
├── pyrefly/
│   └── skills/
│       ├── type-checking/ # Error-kind fixes, Pyrefly command and config reference, agent-loop hook
│       └── type-coverage/ # Annotation guide and Pyrefly command, config, and error-kind reference
└── software-testing/
    └── skills/
        └── best-practices/                 # Anti-pattern examples, test doubles in six languages
```

Restore the development skills, run the tests, validate the plugins, and lint the Markdown:

```bash
bunx skills experimental_install
python3 -m unittest discover -s tests
python3 -m unittest discover -s plugins/git/skills/branch/scripts
claude plugin validate .
uvx rumdl check .
```

> [!IMPORTANT]
> New skills follow the [Agent Skills specification](https://agentskills.io): a `SKILL.md` with `name` and `description`
> frontmatter, where the description says both what the skill does and when to use it. The
> [agent-skills MCP server](https://agentskills.io/mcp) configured in `.mcp.json` has more guidance on writing and measuring them.
