# Setting up Pyrefly's Language Server

How to install, start, register, and configure the server. Day-to-day use is in [SKILL.md](../SKILL.md). Upstream documentation:
<https://pyrefly.org/en/docs/IDE/> and <https://pyrefly.org/en/docs/IDE-features/>.

## Contents

- [Installing Pyrefly](#installing-pyrefly)
- [Starting the Server](#starting-the-server)
- [Registering It with an Agent Harness](#registering-it-with-an-agent-harness)
- [Registering It with an Editor](#registering-it-with-an-editor)
- [Which Configuration Applies](#which-configuration-applies)
- [Server Settings](#server-settings)
- [Troubleshooting](#troubleshooting)

## Installing Pyrefly

Nothing needs installing beyond one runner. The plugin's launcher and the bundled script both use the first of these that exists:
the project's own `.venv/bin/pyrefly` (`.venv\Scripts\pyrefly.exe` on Windows), `pyrefly` on `PATH`, `uvx pyrefly`, or
`pipx run pyrefly`. The script also looks in `venv` and `env`, and in parent folders up to the repository root. Using the project's
own Pyrefly keeps the server's answers and errors on the same version as its CI. To add it: `uv add --dev pyrefly`,
`pip install pyrefly`, `poetry add --group dev pyrefly`, or `pixi add pyrefly`. For the script, `PYREFLY_CMD` overrides the command,
for example `PYREFLY_CMD="uv run pyrefly"`.

## Starting the Server

```shell
pyrefly lsp                                    # stdio, for editors and harnesses
pyrefly lsp --indexing-mode none               # no project index: faster on huge repos, but no cross-file references
pyrefly lsp --workspace-indexing-limit 100000  # a project with no Pyrefly config: index past the first 2,000 files
pyrefly lsp --verbose                          # log to stderr, including when the project index is populated
```

Smoke test: run `python3 scripts/pyrefly_lsp.py outline path/to/module.py` from the project. It prints the module's classes and
functions if the server starts and answers.

## Registering It with an Agent Harness

The `pyrefly` plugin registers the server for `.py` and `.pyi` files, so installing the plugin is all the setup there is. Each
harness starts a one-line launcher that tries the project's `.venv`, then `pyrefly`, `uvx`, and `pipx`, and runs the first it finds.

| Harness | File in the plugin | Launcher | Notes |
| :------ | :----------------- | :------- | :---- |
| Claude Code | `.lsp.json` | `sh -c "..."` | Starts the server on first use of a Python file; adds the read-only `LSP` tool and injects diagnostics after each edit |
| Copilot CLI | `com.github.copilot/lsp.json` | `bash` field, and a `powershell` twin for Windows | A project's `.github/lsp.json` can override or disable it (`"pyrefly": { "disabled": true }`) |
| Codex, Cursor, Gemini CLI | None | | No plugin LSP support; use the bundled script |

Claude Code starts `command` from `PATH` with no shell and no per-platform setting, which is why its launcher is `sh`. On Windows
that needs `sh` on `PATH` (Git for Windows with its Unix tools on `PATH`); without it the server does not start, and the bundled
script still works. When the launcher finds no runner, `/plugin` shows the server in its Errors tab and `claude --debug` logs that
the pyrefly server failed to start. The first start can take a while as `uvx` or `pipx` downloads Pyrefly, so `startupTimeout` is
two minutes.

Only one Python language server should own `.py` files. If another plugin also registers one (Pyright, basedpyright, ty), disable
one of them, or both will answer and diagnose.

To keep navigation but stop diagnostics being added to the conversation after every edit, a local copy of the plugin can set
`"diagnostics": false` on the server in `.lsp.json`. To pass [server settings](#server-settings), add `initializationOptions` to the
server entry in `.lsp.json` or `com.github.copilot/lsp.json`.

## Registering It with an Editor

When a person has Pyrefly running in their editor, the agent does not share that server; the script or the harness starts its own.

| Editor | Setup |
| :----- | :---- |
| VS Code, Cursor, Windsurf, Kiro | Install the `meta.pyrefly` extension (Marketplace or Open VSX); it disables Pylance. In forks, set the Python language server to None |
| PyCharm and other JetBrains IDEs | Settings, Python, Tools, Pyrefly: Enable, then choose Interpreter (installs into it) or Path |
| Neovim 0.11+ | `vim.lsp.enable("pyrefly")` with nvim-lspconfig, or a `lsp/pyrefly.lua` returning `{ cmd = { "pyrefly", "lsp" } }`; Mason can install it |
| Vim with coc.nvim | `languageserver.pyrefly`: `"command": "pyrefly"`, `"args": ["lsp"]`, `"filetypes": ["python"]` |
| Helix | `[language-server.pyrefly]` with `command = "pyrefly"`, `args = ["lsp"]`; add `pyrefly` to the python `language-servers` |
| Zed | The Pyrefly extension; set `lsp.pyrefly.binary` and add `pyrefly` to `languages.Python.language_servers` |
| Emacs (eglot) | `(add-to-list 'eglot-server-programs '((python-mode python-ts-mode) . ("pyrefly" "lsp")))` |
| Sublime Text (LSP) | See <https://lsp.sublimetext.io/language_servers/#pyrefly> |

## Which Configuration Applies

The server picks a configuration per file: it searches upward from the file's folder for `pyrefly.toml`, `pyproject.toml`,
`setup.py`, `mypy.ini`, or `pyrightconfig.json`, and uses the nearest. A `pyrefly.toml` or a `pyproject.toml` with `[tool.pyrefly]`
is used as is. Any other marker makes Pyrefly migrate a nearby mypy or Pyright config in memory, or fall back to the `basic` preset,
which reports only a small set of error kinds. Run `pyrefly init` to write a real config; `pyrefly dump-config FILE` shows what a
file gets, including the interpreter and search path.

The project index covers the files the config includes (`project-includes`, minus `project-excludes`). With no marker at all there
is no project to index, and cross-file answers cover open files only.

The interpreter, and so the installed packages the server can see, comes from the config (`python-interpreter-path`,
`conda-environment`), then an activated venv or conda environment, then a `.venv`, `venv`, or `env` folder at or above the project
root, then `python3` on `PATH`. If `definition` on a third-party import finds nothing, the server is looking at the wrong
environment.

## Server Settings

Pass these as `initializationOptions` (shown) or as workspace configuration under `python.pyrefly`. Prefer the project's Pyrefly
config file, which the CLI and CI read too.

| Setting | Default | Effect |
| :------ | :------ | :----- |
| `pyrefly.typeCheckingMode` | `auto` | Preset when the project has no Pyrefly config: `off`, `basic`, `legacy`, `default`, `strict`, `all`. A config file always wins |
| `pyrefly.disableTypeErrors` | `false` | No diagnostics; navigation still works. A config's `disable-type-errors-in-ide = true` cannot be overridden |
| `pyrefly.disableLanguageServices` | `false` | Diagnostics only; no hover, references, or other features |
| `pyrefly.disabledLanguageServices` | `{}` | Turn off single features: `{"hover": true, "inlayHint": true, ...}` |
| `pyrefly.diagnosticMode` | `openFilesOnly` | `workspace` publishes errors for every file in the project once one is opened |
| `pyrefly.configPath` | | One config file for every file, instead of per-file discovery |
| `pyrefly.extraSearchPaths` | `[]` | Added to the config's `search-path` |
| `pythonPath` | | Interpreter to use, as an absolute path |
| `analysis.importFormat` | `absolute` | `relative` for imports that quick fixes and moves insert |
| `analysis.inlayHints.variableTypes`, `.functionReturnTypes` | `true` | Which hints `hints` returns |
| `analysis.inlayHints.callArgumentNames` | `off` | `all` adds parameter-name hints at call sites |

Config-file keys that affect only the server: `disable-type-errors-in-ide`, `skip-lsp-config-indexing` (no project index: faster
startup, no cross-file references), and `baseline-auto-update`.

## Troubleshooting

| Symptom | Cause and fix |
| :------ | :------------ |
| `findReferences` lists only one file right after start | The index is still building; ask again. The script waits for it |
| The script warns "no project" | No `pyproject.toml` or other marker above the file; add one, or run `pyrefly init` |
| A file never appears in references | Outside the config's `project-includes`, or in `project-excludes` |
| Imports of installed packages do not resolve | Wrong interpreter; check `pyrefly dump-config FILE`, set `python-interpreter-path` |
| Few or no type errors in diagnostics | No Pyrefly config, so the `basic` preset applies; run `pyrefly init` |
| Script exits 2 with "pyrefly not found" | Install Pyrefly in the project, or install uv or pipx, or set `PYREFLY_CMD` |
| Diagnostics differ from `pyrefly check` | The server picks a config per file, and only open files are checked; trust `pyrefly check` |
