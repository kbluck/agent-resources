# Plugin Layout

This repository is one plugin marketplace that serves several plugins to Claude Code, GitHub Copilot (CLI and VS Code), OpenAI
Codex, Cursor, and Gemini CLI. Each plugin lives in its own folder under `plugins/`, keeps its skills and other components in the
standard locations every harness discovers on its own, and carries one thin manifest per harness. The marketplace files at the
repository root list every plugin. This page explains which harness reads which file, and how to add a plugin or a new kind of
component without breaking discovery anywhere.

## Contents

- [Repository Layout](#repository-layout)
- [Who Reads What](#who-reads-what)
- [Adding a Plugin](#adding-a-plugin)
- [Adding Hooks, MCP Servers, and LSP Servers](#adding-hooks-mcp-servers-and-lsp-servers)
- [Versions](#versions)
- [Skill Packs](#skill-packs)
- [Checking Your Work](#checking-your-work)

## Repository Layout

```text
.
├── .agents/plugins/marketplace.json   # Codex marketplace
├── .claude-plugin/marketplace.json    # Claude Code marketplace
├── .cursor-plugin/marketplace.json    # Cursor marketplace
├── .github/plugin/marketplace.json    # Copilot CLI and VS Code marketplace
├── plugins/
│   └── <plugin>/
│       ├── plugin.json                # Agent Plugins 1.0 manifest: Copilot, Cursor, Codex
│       ├── .claude-plugin/plugin.json # Claude Code
│       ├── .codex-plugin/plugin.json  # Codex releases older than Agent Plugins support
│       ├── .cursor-plugin/plugin.json # Cursor marketplace resolver
│       ├── gemini-extension.json      # Gemini CLI extension
│       └── skills/
│           └── <skill>/SKILL.md       # Shared by every harness
├── skills/
│   └── <skill>/SKILL.md               # Setup skill, in no plugin; installed with the skills CLI
├── packs.json                         # Skill packs: pack name -> skill names
├── scripts/build_packs.py             # Builds the skill pack site; .github/workflows/pages.yml deploys it
└── tests/                             # test_manifests.py keeps the manifests in agreement; test_packs.py checks the packs;
                                       # test_rumdl_lsp.py runs the markdown plugin's LSP client on fixtures/rumdl-lsp
                                       # test_pyrefly_lsp.py runs the pyrefly plugin's LSP client on fixtures/pyrefly-lsp
```

The skills are the shared core. Every harness looks for `skills/<name>/SKILL.md` under the plugin root by default, so none of the
manifests lists them. The manifests carry only metadata, which is why they are small and why they must agree with each other.

## Who Reads What

### Plugin Manifests

| File | Read by | Notes |
| :--- | :------ | :---- |
| `plugin.json` | Copilot, Cursor, Codex | [Agent Plugins](https://agent-plugins.org) 1.0. Metadata only: component path fields make the manifest invalid. Copilot prefers it over every legacy location. Codex display data goes under `extensions["com.openai"]` |
| `.claude-plugin/plugin.json` | Claude Code | Claude Code does not read the root `plugin.json` |
| `.codex-plugin/plugin.json` | Older Codex releases | Current Codex reads the root `plugin.json` and ignores this overlay when `extensions["com.openai"]` is set |
| `.cursor-plugin/plugin.json` | Cursor | Cursor's marketplace resolver looks for this path first |
| `gemini-extension.json` | Gemini CLI | Gemini installs one extension per repository root, so each plugin is installed from a local clone |

### Marketplaces

All four files list the same plugins under the same marketplace name, `kbluck-agent-resources`. Each harness resolves `source`
differently, so the entries are not copies of one another.

| File | Read by | `source` form |
| :--- | :------ | :------------ |
| `.claude-plugin/marketplace.json` | Claude Code; also Copilot and Codex as a fallback | `"./plugins/git"`, with the `./` required |
| `.github/plugin/marketplace.json` | Copilot CLI, VS Code | `"./plugins/git"` |
| `.cursor-plugin/marketplace.json` | Cursor | `"git"`, resolved under `metadata.pluginRoot` |
| `.agents/plugins/marketplace.json` | Codex | `{ "source": "local", "path": "./plugins/git" }`, plus the required `policy` and `category` |

Gemini CLI has no marketplace. Users install each plugin from a local clone, or install single skills with `gemini skills install`.

> [!NOTE]
> `.agents/skills/` and `.claude/skills/` hold the skills this repository uses on itself (see `skills-lock.json`). They are
> gitignored and never ship in a plugin. The root `.mcp.json` is the same: it configures this repository's own sessions and is
> outside every plugin root.

### Setup Skills

A skill that is used once per project, such as one that configures a tool, goes in the root `skills/` folder instead of a plugin. A
plugin would keep its description loaded in every session long after the setup is done. Users install it with
`bunx skills add kbluck/agent-resources --skill <skill>` when a project needs it, and it then loads on its own or runs as a command
such as `/pytest-setup`. The `skills` CLI finds these and the plugin skills alike, and installs both without a plugin namespace, so
a setup skill must not share a name with any plugin skill; the manifest test checks this.

## Adding a Plugin

1. Create `plugins/<name>/skills/<skill>/SKILL.md`. Use a lowercase, kebab-case `<name>` that does not start with `claude-` or
   `anthropic-`; Claude Code reserves those.
2. Copy the five manifests from an existing plugin and change `name`, `description`, `displayName`, `homepage`, `keywords`, and the
   Codex `interface` block.
3. Add an entry to each of the four marketplace files, in the form the table above shows for that file.
4. Run the [checks](#checking-your-work).

## Adding Hooks, MCP Servers, and LSP Servers

The `markdown` plugin ships an LSP server (rumdl, through a launcher that picks `rumdl`, `uvx`, `bunx`, or `npx`), and so does the
`pyrefly` plugin (Pyrefly, through a launcher that picks the project's `.venv`, `pyrefly`, `uvx`, or `pipx`); no plugin ships hooks
or MCP servers yet. Put the shared code (scripts, server binaries) in the plugin folder and point each harness at it in that
harness's own format. Configuration formats differ enough that one shared file is usually wrong for at least one harness. The
manifest test checks that `.lsp.json` and `com.github.copilot/lsp.json` define the same servers with the same command, arguments,
and extensions. Claude Code starts an LSP `command` from `PATH` with no shell and no per-platform setting, so a server that must
choose at run time uses a launcher: `sh -c SCRIPT` in `.lsp.json`, the same script in Copilot's `bash` field, and a `powershell`
twin for Windows.

| Component | Claude Code | Copilot | Codex | Cursor | Gemini CLI |
| :-------- | :---------- | :------ | :---- | :----- | :--------- |
| MCP servers | `.mcp.json` | `mcp.json` | `mcp.json` | `mcp.json`, but `.mcp.json` wins if both exist | `mcpServers` in `gemini-extension.json` |
| Hooks | `hooks` field in `.claude-plugin/plugin.json` | `com.github.copilot/hooks/hooks.json` | `extensions["com.openai"].hooks` in `plugin.json` | `hooks` field in `.cursor-plugin/plugin.json` | Not supported here; see the warning |
| LSP servers | `.lsp.json` (`extensionToLanguage`) | `com.github.copilot/lsp.json` (`fileExtensions`) | | | |
| Plugin root variable | `${CLAUDE_PLUGIN_ROOT}` | `${PLUGIN_ROOT}` | `${PLUGIN_ROOT}` | `${CURSOR_PLUGIN_ROOT}` | `${extensionPath}` |

> [!WARNING]
> Do not create `hooks/hooks.json`. Gemini CLI reads hooks only from that path, but Claude Code, Codex, and Cursor load it by
> default too, each expecting different event names (`PreToolUse`, `BeforeTool`, `preToolUse`), and Claude Code merges it even when
> its manifest points elsewhere. Gemini CLI therefore gets no hooks from these plugins, and the manifest test fails if the file
> exists.

MCP servers are the one component that can share most of a definition. Write the Agent Plugins `mcp.json` (with its `$schema` and an
explicit `type` on each server), then define the same servers, under the same names and with the same command or URL, in `.mcp.json`
and `gemini-extension.json`. Only the transport spelling differs: Agent Plugins says `streamable-http` where Claude Code says
`http`. Keeping the servers equivalent matters because Cursor reads `.mcp.json` instead of `mcp.json` when both exist. The manifest
test checks that all three files name the same servers.

## Versions

Every manifest sets the same `version`. Claude Code and Codex cache a plugin by version, so users do not receive a change until the
version is bumped. Bump it in all five manifests of the plugin, and in the `version` fields of the Copilot marketplace entries; the
test fails if any of them disagree. The Claude Code marketplace entries omit `version`, because Claude Code warns when an entry
repeats the one in `plugin.json`.

## Skill Packs

A skill pack is a named set of skills that the `skills` CLI installs with one command, from
`https://kbluck.github.io/agent-resources/packs/<pack>`. Packs are defined in `packs.json` as pack name to skill names, and a skill
can be in any number of packs. Packs are for skills used together for one task and removed afterwards, such as the setup skills;
skills that belong to a plugin are installed with the plugin and stay out of packs.

`scripts/build_packs.py` builds a static site in the [Agent Skills discovery](https://agentskills.io) format that the CLI reads:

| Path | Contents |
| :--- | :------- |
| `skills/<skill>.tar.gz` | One archive per skill, with `SKILL.md` at its root, shared by every pack that lists the skill |
| `packs/<pack>/.well-known/agent-skills/index.json` | The pack's skills, each with its description, archive URL, and SHA-256 digest |
| `.well-known/agent-skills/index.json` | Every skill in the repository |

The archives are reproducible: the same files always give the same bytes. Keep it that way, because installed copies report a
changed digest as an update. The `Skill packs` workflow runs the tests, builds the site, and deploys it to GitHub Pages on every
push to `main` that touches a skill, `packs.json`, or the build. To add or change a pack, edit `packs.json` and the pack table in
the README; the tests check that they agree. To try the site locally:

```bash
python3 scripts/build_packs.py                                  # writes dist/site
python3 -m http.server 8000 --directory dist/site &
bunx skills add http://localhost:8000/packs/python-project-setup --list
```

The index lists each description cut to 1024 characters, because the CLI ignores longer entries. Installs read the description from
`SKILL.md` itself.

## Checking Your Work

Run the manifest tests and Claude Code's validator from the repository root:

```bash
python3 -m unittest discover -s tests
claude plugin validate .
for p in plugins/*/; do claude plugin validate "$p"; done
```

To try the marketplace without touching your own setup, install into a throwaway configuration directory:

```bash
export CLAUDE_CONFIG_DIR="$(mktemp -d)" CODEX_HOME="$(mktemp -d)"
claude plugin marketplace add "$PWD" && claude plugin install git@kbluck-agent-resources && claude plugin details git@kbluck-agent-resources
codex plugin marketplace add "$PWD" && codex plugin add git@kbluck-agent-resources && codex plugin list
```
