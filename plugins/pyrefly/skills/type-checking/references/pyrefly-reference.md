# Pyrefly Reference for Type Checking

The commands, config behavior, and suppression rules this skill relies on, checked against Pyrefly 1.4 and the
[Pyrefly docs](https://pyrefly.org/en/docs/). The docs sometimes describe flags newer than the installed version; where they
disagree, `pyrefly <command> --help` wins.

- [Check flags](#check-flags)
- [Output formats](#output-formats)
- [Severity and exit codes](#severity-and-exit-codes)
- [Config discovery](#config-discovery)
- [Presets](#presets)
- [Import resolution](#import-resolution)
- [Suppression comments](#suppression-comments)
- [Baselines](#baselines)
- [Bulk suppression after an upgrade](#bulk-suppression-after-an-upgrade)

## Check Flags

| Command | What it does |
| :------ | :----------- |
| `pyrefly check` | Project mode: checks the files in the nearest config's `project-includes`, minus `project-excludes`. |
| `pyrefly check <paths>` | File mode: checks only the named files or directories (globs allowed), each with its own config. Ignores `project-excludes`. |
| `pyrefly check -a <paths>` | Also checks every module the named files reach through imports. |
| `--only <kind>[,<kind>]` | Show only these kinds. |
| `--error`, `--warn`, `--info`, `--ignore <kind>` | Change a kind's severity for this run only. |
| `--count-errors[=N]` | Print the top N kinds by count (default 5; `0` for all). |
| `--summarize-errors` | Print errors per directory, broken down by kind. |
| `--min-severity <level>` | Show, and fail on, everything at or above this level. |
| `--preset <name>` | Use a preset for this run, for example `default` when the project has no config. |
| `--summary=none` | Hide the progress bar and the final count line. |
| `pyrefly dump-config <files>` | Show the governing config, the interpreter, and the search and site-packages paths. |

## Output Formats

`--output-format <format>`:

| Format | Use |
| :----- | :-- |
| `full-text` (default) | Code frame for each error; `missing-import` lists every path searched. |
| `min-text` | One line per error: `ERROR path:line:col-col: message [kind]`. Best for iterating and diffing before and after. |
| `json` | `{"errors": [...]}` with `path`, `line`, `column`, `stop_line`, `stop_column`, `name` (the kind), `description`, `concise_description`, `severity`. |
| `github`, `sarif`, `junit-xml`, `code-climate` | CI annotations and reports. |
| `omit-errors` | Only the count. |

The errors go to stdout; the `INFO` progress and summary lines go to stderr.

## Severity and Exit Codes

Each kind has a severity: `error`, `warn`, `info`, `hint`, or `ignore`. Without `min-severity`, `pyrefly check` shows warnings and
errors and exits nonzero only on errors. With `min-severity` set, everything at or above it is shown and fails the run. `hint`-level
kinds (`unused-import`, `unused-variable`, `unused-parameter`, `unreachable`) are hidden unless `--min-severity hint`.

Precedence: CLI flags, then the config file, then the preset, then each kind's default.

`[errors]` in the config sets severities by kind: `"error"`, `"warn"`, `"info"`, `"hint"`, `"ignore"`, `true` (default severity, or
`error` for a kind that is off by default), or `false`. `[[sub-config]]` entries override `[errors]` for files matching a glob.
`min-severity` and `baseline` are project-level and cannot be set per sub-config.

## Config Discovery

Pyrefly searches upward from each checked file (file mode) or from the working directory (project mode) for `pyrefly.toml`,
`pyproject.toml`, `setup.py`, `mypy.ini`, or `pyrightconfig.json`. `pyrefly.toml` wins over `pyproject.toml` in the same directory.

- `pyrefly.toml`, or `pyproject.toml` with `[tool.pyrefly]`: native config.
- `mypy.ini`, `pyrightconfig.json`, or `[tool.mypy]` / `[tool.pyright]` / `[tool.basedpyright]` with no Pyrefly config: migrated in
  memory, the same way `pyrefly init` would write it.
- Nothing usable: the `basic` preset. The CLI says so at the end of the run and suggests `pyrefly init`.

`-c <file>` uses one config for every file and skips the search.

## Presets

| Preset | Effect |
| :----- | :----- |
| `off` | Every kind silenced. For IDE-only use. |
| `basic` | Used when no config exists. Only syntax errors, `missing-import`, `unknown-name`, `bad-instantiation`, `unexpected-keyword`, `unused-coroutine`, and a few other high-confidence kinds. Skips unannotated function bodies and does not infer return types. |
| `legacy` | Written by `pyrefly init` for mypy projects. Skips unannotated function bodies, treats untyped imports as `Any`, and disables `unbound-name` and `bad-override-param-name`. |
| `default` | Each kind at its own default. Same as no preset. |
| `strict` | Adds `implicit-any` (all sub-kinds), `unused-ignore`, `missing-override-decorator`, `possibly-uninitialized-attribute`, and others. |
| `all` | Every kind at `error`. |

`check-unannotated-defs = false` (set by `basic` and `legacy`) means a function with no annotations at all is not checked inside.
Functions with at least one annotation are always checked.

## Import Resolution

Absolute imports resolve from, in order: the search path (config `search-path`, plus an import root guessed from the layout: `src/`
if present), the bundled typeshed, a fallback search path, and site-packages. For each, `-stubs` packages are preferred, then `.pyi`
files, then `.py` source.

Site-packages come from the interpreter Pyrefly finds, in this order:

1. `python-interpreter-path`, `conda-environment`, or a similar flag or config setting.
2. The interpreter the IDE supplies.
3. An active venv, conda env, or Pixi env.
4. A `.venv`, `venv`, or `env` directory (or `.pixi/envs/default`) in the project root or any parent.
5. `python3`, then `python`, on the `PATH`.

`uvx pyrefly` with no project venv falls through to uv's own isolated interpreter, which has none of the project's dependencies.
Create or activate the project venv, or run Pyrefly through the project's runner (`uv run pyrefly`).

Bundled third-party stubs: with a Pyrefly config, Pyrefly uses only stubs you have installed, and reports `untyped-import` for an
installed package without stubs. Without a config, it uses its bundled stubs, and reports `missing-source-for-stubs` when the
package itself is missing.

Editable installs that use import hooks (setuptools' default) are invisible to static tools. Path-based `.pth` editable installs
(`uv_build`, Hatchling, PDM, and Poetry by default) work.

## Suppression Comments

| Comment | Scope | Notes |
| :------ | :---- | :---- |
| `# pyrefly: ignore[<kind>]` | The line it is on, or the next line when it stands alone | The form to use. Always give the kind. |
| `# pyrefly: ignore` | Same | Suppresses every kind on the line. Avoid. |
| `# type: ignore[...]` | Same | Honored by default, and may be shared with mypy or Pyright. |
| `# pyrefly: ignore-errors` | Whole file | Only before the first line of code. Below that it is inert and reported as `misplaced-ignore`. |
| `# pyright: ignore`, `# mypy: ignore-errors`, `# pyre-fixme`, ... | Not honored by default | Honored only with `permissive-ignores = true` or when `enabled-ignores` lists the tool. The `basic` preset sets `permissive-ignores = true`. |

Unused suppressions are reported as `unused-ignore` (off by default, on in `strict`). Remove them with:

```shell
pyrefly suppress --remove-unused <files>        # pyrefly and pyre ignores only
pyrefly suppress --remove-unused=type <files>   # only "# type: ignore"
pyrefly suppress --remove-unused=all <files>    # all three
```

## Baselines

With `baseline = "baseline.json"` in the config (or `--baseline`), errors that match an entry are hidden from the CLI, but still
shown in the IDE. Only new errors are reported.

| Command | Use |
| :------ | :-- |
| `pyrefly check --prune-baseline` | After fixing baselined errors: drop the stale entries without recording anything new. |
| `pyrefly check --error-stale-baseline` | Fail when the baseline has stale entries. For CI. |
| `pyrefly check --update-baseline` | Regenerate the baseline from current errors. This accepts every current error, including new ones. Only on the user's request. |
| `pyrefly check --baseline-error-level warn` | Show baselined errors as warnings, to see them without failing. |

## Bulk Suppression After an Upgrade

Upgrading Pyrefly or a dependency can surface many new errors at once. The documented way to get back to clean and fix them later:

```shell
pyrefly suppress                   # add an ignore comment for every current error
<run the project's formatter>
pyrefly suppress --remove-unused   # remove the ones the formatter made unnecessary
```

Repeat until both the formatter and the check are clean. `--comment-location=same-line` puts the comments at the end of the line
instead of above it, which avoids collisions with other tools' comments.

This hides real errors along with noise, so it is the user's decision. Offer it when the error count is too large to fix in this
change; otherwise fix the errors. Bare `# pyrefly: ignore` comments it writes are a known, accepted debt; do not add more by hand.
