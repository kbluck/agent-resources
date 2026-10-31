# Markdown Tools

How to run each supported tool. Commands assume the repository root as the working directory. Quote globs (`"**/*.md"`) so the shell
passes them to the tool unexpanded; that works the same in Bash, zsh, PowerShell, and `cmd`.

## Contents

- [Running a tool without installing it](#running-a-tool-without-installing-it)
- [rumdl](#rumdl) (the fallback)
- [markdownlint-cli2](#markdownlint-cli2)
- [markdownlint-cli](#markdownlint-cli)
- [PyMarkdown](#pymarkdown)
- [Prettier](#prettier)
- [Rule names across tools](#rule-names-across-tools)

## Running a Tool Without Installing It

Use the project's own copy first, so the version matches CI:

| Project uses | Run with |
| :----------- | :------- |
| Bun | `bunx <tool>` |
| uv | `uv run <tool>` |
| npm | `npx --no-install <tool>` |
| pnpm | `pnpm exec <tool>` |
| Yarn | `yarn <tool>` |
| Poetry, Pipenv | `poetry run <tool>`, `pipenv run <tool>` |

When the project does not install it, run a one-off copy: `uvx <tool>` or `pipx run <tool>` for Python packages (rumdl, PyMarkdown),
`npx --yes <package>` for npm packages (rumdl, markdownlint-cli2, markdownlint-cli, Prettier). These download into a cache and
change nothing in the project. The first run needs network access. If `npx` is Bun's shim (`npx --version` prints a 1.x version and
`--yes` fails with "Script not found"), use `bunx <package>` instead.

## Rumdl

A fast Rust linter and formatter that implements every markdownlint rule plus about 30 of its own. Packages: `rumdl` on PyPI and
npm, also Homebrew and Cargo.

```shell
rumdl check <paths>         # lint; exit 0 clean, 1 violations, 2 tool error
rumdl check --diff <paths>  # show what --fix would change, without writing
rumdl check --fix <paths>   # fix, then report what remains; exit 1 if anything remains
rumdl fmt <paths>           # fix; exits 0 even if unfixable issues remain
rumdl rule MD013            # explain a rule
rumdl config file --explain # which config file applies, and why
```

Use `check --fix` in this skill's workflow: its exit code says whether anything is left. Directories are searched recursively and
`.gitignore` is respected. `--disable MD013,MD033` and `--enable` take comma-separated lists.

**Fallback invocation**: `uvx rumdl check --config <skill-dir>/assets/rumdl.toml <paths>` (and `--fix`). `--config` turns off
per-directory config discovery, which is what the fallback wants.

**Configuration**: searched upward from the working directory, stopping at `.git`: `.rumdl.toml`, `rumdl.toml`,
`.config/rumdl.toml`, `[tool.rumdl]` in `pyproject.toml`. If none, rumdl reads `.markdownlint.{json,jsonc,yaml,yml}`, then a user
config at `~/.config/rumdl/rumdl.toml` (`%APPDATA%\rumdl\` on Windows) or `~/.rumdl.toml`. Keys use hyphens (`line-length`), not
markdownlint's underscores. Rules go in `[MD013]` tables; `[global]` holds `disable`, `enable`, `exclude`, `line-length`, `flavor`.

**MD013 reflow**: with `reflow = true` under `[MD013]`, the fix rewraps paragraphs that run past the limit instead of only reporting
them. `reflow-mode = "normalize"` rewraps every paragraph; `"sentence-per-line"` and `"semantic-line-breaks"` break at sentences.

**Rules beyond markdownlint** worth knowing: `MD057` (relative links point to files that exist), `MD062` (whitespace in link
destinations), `MD064` (multiple consecutive spaces), `MD065` (blank lines around horizontal rules), `MD069` (duplicate list
markers), `MD070` (nested fences that close early), `MD076` (consistent list item spacing), `MD077` (list continuation indentation).
Run `rumdl rule` for the full list.

**Differences from markdownlint**: rumdl's `MD014` checks only blocks tagged as shell (`bash`, `sh`, `shell`,`console`), while
markdownlint checks every fence. rumdl does not flag GitHub alerts separated by a blank line (`MD028`); markdownlint does. rumdl
leaves `MD060` off unless enabled. When the result must also pass markdownlint, check these by hand.

**Inline suppression**: `<!-- rumdl-disable MD013 -->` ... `<!-- rumdl-enable MD013 -->`, `<!-- rumdl-disable-next-line MD013 -->`,
`<!-- rumdl-disable-line MD013 -->` at the end of a line, `<!-- rumdl-disable-file MD013 -->`. The markdownlint forms also work.

## Markdownlint-Cli2

The current command-line front end for markdownlint, by its author. Package: `markdownlint-cli2` on npm.

```shell
markdownlint-cli2 "**/*.md" "#node_modules"          # lint; "#" negates a glob
markdownlint-cli2 --fix "**/*.md" "#node_modules"    # fix, then report what remains
markdownlint-cli2 --config path/to/.markdownlint-cli2.jsonc "**/*.md"
```

Exit codes: 0 clean, 1 violations, 2 tool failure. It needs at least one glob on the command line unless the config file has a
`globs` property; check the config before assuming it lints nothing. Pass explicit file paths to lint only some files.

**Configuration**: per directory, so a nested config applies to files under it. In each directory it reads the first of
`.markdownlint-cli2.jsonc`, `.markdownlint-cli2.yaml`, `.markdownlint-cli2.cjs`, `.markdownlint-cli2.mjs` (rules go under a `config`
key, with options such as `globs`, `ignores`, `gitignore`, `fix`), plus the first of `.markdownlint.jsonc`, `.markdownlint.json`,
`.markdownlint.yaml`, `.markdownlint.yml`, `.markdownlint.cjs`, `.markdownlint.mjs` (rules only). Configuration inside
`package.json` or `pyproject.toml` is read only through `--config <file> --configPointer /key`.

**Inline suppression** (shared by every markdownlint front end): `<!-- markdownlint-disable MD013 -->` ...
`<!-- markdownlint-enable MD013 -->`, `<!-- markdownlint-disable-next-line MD013 -->`, `<!-- markdownlint-disable-line MD013 -->`,
`<!-- markdownlint-disable-file MD013 -->`, `<!-- markdownlint-capture -->` and `<!-- markdownlint-restore -->`.

## Markdownlint-Cli

The older front end, which provides the `markdownlint` command. Package: `markdownlint-cli` on npm. (`markdownlint` on npm is the
library; it has no command.)

```shell
markdownlint "**/*.md" --ignore node_modules
markdownlint --fix "**/*.md" --ignore node_modules
markdownlint --disable MD013 MD033 -- README.md     # --enable and --disable need "--" before the files
```

Exit codes: 0 clean, 1 violations, other non-zero values for tool errors. Files and folders starting with a dot (`.github/`) are
skipped unless `--dot` is given.

**Configuration**: `--config <file>`, else the first of `.markdownlint.jsonc`, `.markdownlint.json`, `.markdownlint.yaml`,
`.markdownlint.yml` in the current folder, merged over any `.markdownlintrc`. Ignore patterns come from `.markdownlintignore`.

## PyMarkdown

A Python linter with its own parser. Package: `pymarkdownlnt` on PyPI; the command is `pymarkdown`. Options that select
configuration go before the subcommand.

```shell
pymarkdown scan -r <paths>                       # lint; -r recurses into directories
pymarkdown fix -r <paths>                        # fix what its rules can
pymarkdown --config .pymarkdown.json scan -r docs
pymarkdown -d md013,md033 scan -r <paths>        # disable rules for this run
```

Exit codes (default scheme): 0 clean, 1 violations or no files found, 2 command-line error, 3 files were fixed. A 3 from `fix` is
success; scan again to see what remains.

**Configuration**: `.pymarkdown` (JSON), `.pymarkdown.json`, `.pymarkdown.yml`, `.pymarkdown.yaml` in the current directory, or
`[tool.pymarkdown]` in `pyproject.toml`. Rule settings live under `plugins`, with lowercase IDs or names:
`plugins.md013.line_length`.

**Inline suppression**: `<!-- pyml disable md013-->` ... `<!-- pyml enable md013-->`, `<!-- pyml disable-next-line md013-->`,
`<!-- pyml disable-num-lines 5 md013-->`. Rule names work in place of IDs (`line-length`).

PyMarkdown's rule IDs follow markdownlint's, and it adds `pml` rules of its own.

## Prettier

A formatter, not a linter. It rewrites spacing, list markers, emphasis markers, table alignment, and escaping, and reports nothing
about content. Package: `prettier` on npm.

```shell
prettier --check <paths>     # exit 0 formatted, 1 some files would change, 2 error
prettier --write <paths>     # format in place
```

**Configuration**: `.prettierrc` (JSON or YAML), `.prettierrc.{json,yaml,yml,json5,toml,js,cjs,mjs,ts}`,
`prettier.config.{js,cjs,mjs,ts}`, or a `prettier` key in `package.json`. Files are skipped if listed in `.prettierignore`. The
Markdown-relevant option is `proseWrap`: `"preserve"` (the default) leaves line breaks alone, `"always"` wraps at `printWidth`
(default 80), `"never"` joins each paragraph onto one line.

**Inline suppression**: `<!-- prettier-ignore -->` before a block, or `<!-- prettier-ignore-start -->` ...
`<!-- prettier-ignore-end -->`.

Because Prettier checks no content rules, a project that uses only Prettier still needs the judgment rules (heading structure, code
block languages, alt text, link text) applied by hand. When a project runs both Prettier and a linter, run Prettier first; a linter
fix applied afterward may be undone the next time Prettier runs, so resolve conflicts in the linter config, not the files.

## Rule Names Across Tools

The four linters accept markdownlint's rule IDs (`MD013`) and aliases (`line-length`), with the same meaning. Their extra rules do
not carry over: rumdl's own rules are `MD057` and `MD061` onward, which markdownlint does not have, and PyMarkdown's use `pml` IDs.
