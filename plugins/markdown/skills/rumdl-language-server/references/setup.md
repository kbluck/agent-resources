# Setting up Rumdl's Language Server

How to install, start, register, and configure the server. Day-to-day use is in [SKILL.md](../SKILL.md). Upstream documentation:
<https://rumdl.dev/lsp/> and <https://rumdl.dev/usage/editors/>.

## Contents

- [Installing rumdl](#installing-rumdl)
- [Starting the Server](#starting-the-server)
- [Registering It With an Agent Harness](#registering-it-with-an-agent-harness)
- [Registering It With an Editor](#registering-it-with-an-editor)
- [Server Settings](#server-settings)
- [Which Configuration File Applies](#which-configuration-file-applies)
- [Troubleshooting](#troubleshooting)

## Installing Rumdl

Nothing needs installing beyond one runner. The `markdown` plugin's launcher and the bundled script both use the first of these that
is available: `rumdl` itself, `uvx rumdl` (uv), `bunx rumdl` (Bun), or `npx --yes rumdl` (Node.js). The runners download rumdl into
their cache on first use, which needs network access once. Installing rumdl makes startup faster and fixes the version: `rumdl` is
on PyPI (`uv tool install rumdl`, `pipx install rumdl`), npm (`npm install -g rumdl`), Homebrew (`brew install rumdl`), and Cargo
(`cargo install rumdl`). Editors other than VS Code need `rumdl` itself on `PATH`. For the script, `RUMDL_CMD` overrides the
command, for example `RUMDL_CMD="uv run rumdl"` to use the project's pinned version.

## Starting the Server

```shell
rumdl server                       # stdio, for editors and harnesses
rumdl server --config .rumdl.toml  # one config file for everything; turns off per-directory discovery
rumdl server --no-config           # built-in defaults only
rumdl server --verbose             # log to stderr, including which config was loaded
rumdl server --port 9257           # TCP, for debugging a client
```

Smoke test: run `python3 scripts/rumdl_lsp.py outline README.md` from a repository. It prints the heading tree if the server starts
and answers.

## Registering It with an Agent Harness

The `markdown` plugin registers the server for `.md` and `.markdown` files, so installing the plugin is all the setup there is.
Neither harness can choose between runners on its own, so each starts a one-line launcher that tries `rumdl`, `uvx`, `bunx`, then
`npx` and runs the first it finds.

| Harness | File in the plugin | Launcher | Notes |
| :------ | :----------------- | :------- | :---- |
| Claude Code | `.lsp.json` | `sh -c "..."` | Starts the server on first use of a Markdown file; adds the read-only `LSP` tool and injects diagnostics after each edit |
| Copilot CLI | `com.github.copilot/lsp.json` | `bash` field, and a `powershell` twin for Windows | A project's `.github/lsp.json` can override or disable it (`"rumdl": { "disabled": true }`) |
| Codex, Cursor, Gemini CLI | None | | No plugin LSP support; use the bundled script |

Claude Code starts `command` straight from `PATH`, with no shell and no per-platform setting, which is why its launcher is `sh`. On
Windows that needs `sh` on `PATH`, which Git for Windows provides only when installed with its Unix tools on `PATH`; without it, the
server does not start there, and the bundled script still works. When the launcher finds no runner, or `sh` is missing, `/plugin`
shows the server in its Errors tab and `claude --debug` logs "LSP server rumdl failed to start". The first start can take a while as
the runner downloads rumdl, so `startupTimeout` is two minutes.

To keep navigation but stop diagnostics being added to the conversation after every edit, a local copy of the plugin can set
`"diagnostics": false` on the server in `.lsp.json`.

Claude Code sends no initialization options by default, so the server reads the project's rumdl config file. To pass
[server settings](#server-settings), add `initializationOptions` to the server entry in `.lsp.json` or
`com.github.copilot/lsp.json`.

## Registering It with an Editor

When a person has the server running in their editor, the agent does not share it; the script or the harness starts its own.

| Editor | Setup |
| :----- | :---- |
| VS Code, Cursor, Windsurf | `rumdl vscode`, or install the `rvben.rumdl` extension; it starts the server itself |
| Neovim 0.11+ | `vim.lsp.config("rumdl", { cmd = { "rumdl", "server" }, filetypes = { "markdown" } })`, then `vim.lsp.enable("rumdl")`; or `require("lspconfig").rumdl.setup{}` |
| Helix | Built in after 25.07.1; otherwise `[language-server.rumdl]` with `command = "rumdl"`, `args = ["server"]`, and add `rumdl` to the markdown `language-servers` |
| Zed | `"lsp": { "rumdl": { "binary": { "path": "rumdl", "arguments": ["server"] } } }` and `"languages": { "Markdown": { "language_servers": ["rumdl"] } }` |
| Emacs (eglot) | `(add-to-list 'eglot-server-programs '(markdown-mode . ("rumdl" "server")))` |
| Sublime Text (LSP) | `"command": ["rumdl", "server"]`, `"selector": "text.html.markdown"` |
| JetBrains IDEs | Any LSP plugin that runs a stdio command: `rumdl server` for `*.md` |

Helix's `[[language]]` block replaces its default server list, so keep `marksman` or others in it if you use them. If another
Markdown server (marksman, markdown-oxide) should own links, turn rumdl's link features off with the settings below.

## Server Settings

Pass these as `initializationOptions`, or as workspace configuration under a `rumdl` section. Capability flags take effect only when
the server restarts.

| Setting | Default | Effect |
| :------ | :------ | :----- |
| `enableLinting` | `true` | Diagnostics as files change |
| `enableAutoFix` | `false` | Apply fixes on save |
| `enableLinkCompletions` | `true` | Path and anchor completion inside `](...)` |
| `enableLinkNavigation` | `true` | Hover, definition, references, and rename |
| `enableSymbols` | `true` | Document outline and workspace heading search |
| `linkCompletionContentRoots` | `[]` | Roots for site-absolute links such as `/img/a.png`; empty means the workspace roots |
| `configPath` | (discovered) | A rumdl config file to use for every document |
| `enableRules`, `disableRules` | (config) | Override which rules run |
| `settings` | (config) | Rule options, such as `{ "lineLength": 100 }` or `{ "MD013": { "lineLength": 120 } }` |

Prefer the project's rumdl config file over server settings, so the editor, the agent, CI, and `rumdl check` all agree.

## Which Configuration File Applies

The server resolves configuration per file, exactly as `rumdl check` does: it searches upward from the file's folder, stopping at
the repository root (`.git`), and takes the first of `.rumdl.toml`, `rumdl.toml`, `.config/rumdl.toml`, or `pyproject.toml` with
`[tool.rumdl]`. Without one it falls back to markdownlint config files, then to a user config in `~/.config/rumdl/` (or
`%APPDATA%\rumdl\` on Windows) or `~/.rumdl.toml`. `rumdl config file --explain` shows which file a directory gets and why.

The workspace index follows the config's `exclude` list and, by default, `.gitignore`. It always skips `.git`, `node_modules`, and
`target`. Files left out are not linted, completed, or found by references, and rename does not update links in them.

## Troubleshooting

| Symptom | Cause and fix |
| :------ | :------------ |
| References, rename, or headings return nothing right after start | The index is still building. The script waits for it; an editor shows indexing progress |
| No cross-file `MD051`/`MD057` diagnostics | Same: wait for the index, or run `rumdl check FILE` |
| A file is never indexed | Excluded by config or `.gitignore`; check `exclude` and `respect-gitignore` |
| Config errors do not appear in the editor | They go to the server log; start with `--verbose` |
| Settings change has no effect | Capability flags need a server restart |
| Script exits 2 with "rumdl not found" | Install rumdl, uv, Bun, or Node.js, or set `RUMDL_CMD` |
| Script exits 2 with "`npx --yes rumdl server` exited", "Script not found" | `npx` is Bun's shim; install Bun's `bunx` on `PATH` or use uv |
| A `.rumdl_cache/` folder appears in the repository | The server caches its index there unless the config sets `cache-dir`; it holds its own `.gitignore`, so git ignores it |
