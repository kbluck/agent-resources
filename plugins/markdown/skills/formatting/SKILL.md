---
name: formatting
description: >
  Use this skill whenever Markdown (.md) markup is broken, inconsistent, or failing a check, and the fix belongs in the syntax, not
  the content. This covers: any lint or format check failing on .md files (markdownlint, rumdl, PyMarkdown, prettier --check, CI,
  pre-commit); questions about MD0xx rules; requests to lint, format, or tidy Markdown, or to set up a Markdown linter; and
  Markdown that renders wrong because the syntax is malformed (a literal "#Heading", lists that restart around code blocks, broken
  tables or fences). Runs the project's own tool or falls back to rumdl. Also use it as the final pass after you write or edit any
  .md file. For structure and wording (tables versus lists, callouts, diagrams, sections), use the authoring skill. Not for MDX,
  converting to HTML or PDF, or non-Markdown linters.
compatibility: >
  Uses the project's configured Markdown tool when there is one. Otherwise runs rumdl through uvx, pipx, or npx (needs uv, pipx, or
  Node.js). Without any of them, applies the rules by hand.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/markdown/skills/formatting
  version: 1.0.0
---

# Markdown Formatting

Make Markdown files consistent and lint-clean without changing what they say. A clean file renders the same everywhere, diffs
cleanly, and passes whatever check the project runs in CI or a pre-commit hook.

The rule set is markdownlint's (`MD001` to `MD096`), which most Markdown linters share. The project's own tool and configuration
always win over this skill's defaults.

## Two Modes

- **Authoring mode**: you are writing or substantially editing a Markdown file as part of other work. Write it by the authoring
  rules, then run steps 1 to 4 of the workflow on the files you touched, and only those.
- **Fix mode**: the user wants existing files formatted, linted, or fixed. Follow the workflow for the files they named, or all
  Markdown files if they asked for the whole project.

Only `.md` and `.markdown` files are in scope. If asked to lint `.mdx`, say that this skill does not cover MDX: markdownlint-style
rules misread JSX and imports, so the results would be noise.

## Working with Markdown-Authoring

The `authoring` skill decides what a document is made of: whether facts go in a table or a list, where a warning becomes an alert,
when to draw a diagram, how sections are laid out, and how the prose reads. This skill decides how that Markdown is written down so
it lints clean. The two run in that order, because a lint pass after a restructure catches whatever the restructure broke.

- **Writing a new document, or rewriting one on request**: if `authoring` is available, follow it for structure and wording, then
  use this skill as the last pass. Without it, follow the project's own documentation conventions for structure.
- **Fixing formatting or lint**: change syntax only. Do not turn lists into tables, add alerts, reorder sections, or reword text
  beyond what a rule needs, even where `authoring` would. If the document would benefit from restructuring, suggest it; do not do it
  unasked.
- **Where they meet**: both skills want language-tagged fences, alt text, one H1, and no skipped heading levels; those are lint
  rules here. On pure syntax (table padding, list markers, line wrapping), the linter's configuration wins, so a table written from
  an `authoring` example may come back reformatted.

## Workflow

### 1. Find the Project's Markdown Tool

A project that enforces Markdown style will fail CI or a hook on anything else, and its configuration encodes choices (line length,
list style) that this skill must not override. Look, from the repository root:

- A script that already runs it: `lint:md`, `format`, or similar in `package.json`, a `Makefile`, `justfile`, or `pyproject.toml`; a
  hook in `.pre-commit-config.yaml`; a step in `.github/workflows/` or `.gitlab-ci.yml`. Prefer running the project's script, since
  it carries the right file globs and tool version.
- Configuration files. Each one identifies a tool:

| Tool | Configuration |
| :--- | :------------ |
| rumdl | `.rumdl.toml`, `rumdl.toml`, `.config/rumdl.toml`, `[tool.rumdl]` in `pyproject.toml` |
| markdownlint-cli | `.markdownlintrc` |
| markdownlint-cli2 | `.markdownlint-cli2.jsonc`, `.markdownlint-cli2.yaml`, `.markdownlint-cli2.cjs`, `.markdownlint-cli2.mjs` |
| either markdownlint CLI | `.markdownlint.json`, `.markdownlint.jsonc`, `.markdownlint.yaml`, `.markdownlint.yml` |
| PyMarkdown | `.pymarkdown`, `.pymarkdown.json`, `.pymarkdown.yml`, `.pymarkdown.yaml`, `[tool.pymarkdown]` in `pyproject.toml` |
| Prettier | `.prettierrc*`, `prettier.config.*`, a `prettier` key in `package.json` |

- Dependencies: `rumdl`, `markdownlint-cli`, `markdownlint-cli2` or `prettier` in `package.json`; `rumdl` or `pymarkdownlnt` in
  `pyproject.toml` or `requirements*.txt`.

Decide:

- **One tool found**: use it. A bare `.markdownlint.*` file can mean any markdownlint CLI; use whichever one appears in
  dependencies, scripts, or hooks, and markdownlint-cli2 if none does.
- **Several found**: use the one CI or the hooks run. A formatter (Prettier) and a linter can both apply: run the formatter first,
  then the linter. Prettier counts only if it formats Markdown (no `*.md` in `.prettierignore`).
- **None found**: use the fallback, rumdl with this skill's [`assets/rumdl.toml`](assets/rumdl.toml). If `rumdl config file` reports
  a user-level config (`~/.config/rumdl/rumdl.toml` or `~/.rumdl.toml`), the user has chosen their own defaults: use those and skip
  `--config`.

### 2. Run It

How to run each tool, its fix command, its exit codes, and its inline-disable syntax are in
[references/tools.md](references/tools.md). In short:

- Prefer a project-local install that is already there (`npx --no-install`, `pnpm exec`, `uv run`), then a one-off run (`uvx rumdl`,
  `npx --yes markdownlint-cli2`). Do not run `npm install`, `pip install`, or similar in the project, even for a tool it declares:
  that creates `node_modules/`, lock files, or virtual environments the user did not ask for. If the project script cannot run
  without an install, run the same tool one-off with the script's arguments. Leave the working tree with only the Markdown changes.
- Fallback: `uvx rumdl check --config <skill-dir>/assets/rumdl.toml <paths>`. If `uvx` is missing, use `pipx run rumdl` or
  `npx --yes rumdl` with the same arguments.
- Lint only the files in scope. Running a formatter across a whole repository nobody asked about produces a large, unreviewable
  diff.

If no tool can run (no Node.js, uv, pipx, or network), apply the rules by hand from [references/rules.md](references/rules.md) and
tell the user that no linter was run.

### 3. Fix

1. **Autofix first.** Run the tool's fix command. Mechanical rules (blank lines, spacing, list markers, trailing whitespace, final
   newline) are faster and safer to fix by tool than by hand.
2. **Fix the rest by hand.** Re-run the check and fix what remains. These are the judgment calls: heading structure, duplicate
   headings, code block languages, alt text, link text, long lines that cannot reflow. [references/rules.md](references/rules.md)
   says how to fix each one.
3. **Repeat** until the check passes or only deliberate exceptions remain.

**In authoring mode with no project tool**, the file may predate you. Run the check, not the fix, on pre-existing files; fix
problems in the parts you wrote, and mention any older ones rather than reformatting the whole file. Files you created get the full
fix.

Some rules can only be fixed by writing new words: alt text (`MD045`), link text such as "here" (`MD059`), duplicate headings
(`MD024`), a missing H1 (`MD041`). If the user said not to change what the document says, leave these, and list each one with a
suggested fix in your report. Otherwise, make the smallest content change that satisfies the rule. Markup that only looks like
content is still formatting: a `$` prompt in front of a command, a bare URL's angle brackets, a bold line that should be a heading.
Fix those even when the user asked for no wording changes, and give a shell block the `bash` tag rather than `text`.

Fix the content, not the rules. Do not edit the project's configuration, add `<!-- markdownlint-disable -->` style comments, or
exclude files to make a check pass. A suppression is right only when the flagged construct is intended and no compliant form exists
(a deliberate `<br>` in a table cell, a long URL in a heading); then disable the one rule for the narrowest span, and tell the user.

### 4. Verify and Report

- Re-run the check; it must exit 0. If something remains by design, say what and why. The linter is the verification; do not install
  renderers or previewers to double-check the output.
- With the fallback, the result must also pass markdownlint, which most CI runs. rumdl misses two of its checks: `$` prompts in a
  block not tagged as shell (`MD014`) and alerts separated only by a blank line (`MD028`). Look for both before reporting.
- Confirm only formatting changed. `git diff --word-diff` should show whitespace, markers, and line breaks, not different words.
  Autofix can mangle text in rare cases (an `*` read as emphasis, a list renumbered); look at the diff before reporting.
- Report which tool and config you used, what changed, and anything left for the user. If you used the fallback, mention that the
  project has no Markdown linter configured and offer to add one (copy `assets/rumdl.toml` to `.rumdl.toml`). Do not add it unasked.

## Authoring Rules

Write Markdown that passes the default rules the first time. Follow the project's configuration where it differs, and match the
file's existing style when editing one.

- **Headings**: ATX style (`## Heading`), one space after the `#`s, one `#` heading per file, on the first line (after any front
  matter). Go down one level at a time. No trailing punctuation, and no duplicate heading text unless under different parents and
  the project allows it. Never use a bold line in place of a heading.
- **Blank lines**: one blank line before and after every heading, list, fenced code block, table, and blockquote. Never two in a
  row. End the file with exactly one newline.
- **Lists**: `-` for bullets; `1.` numbering in order (or all `1.`, consistently). Nest bullets under bullets by 2 spaces; indent
  content under an ordered item to align with its text (3 spaces for `1.`). One space after the marker.
- **Code**: fenced blocks with backticks, always with a language (`bash`, `json`, `text` when nothing fits). Do not prefix commands
  with `$` unless the block also shows their output; markdownlint flags it in any block, whatever the tag. Use a longer fence (four
  backticks) to show a fence inside a block.
- **Links and images**: no bare URLs in prose; use `[descriptive text](url)` or `<https://example.com>`. Link text says where it
  goes, never "here" or "click here". Every image has alt text. Fragment links (`#section`) must match a real heading's anchor.
- **Emphasis**: `*italic*` and `**bold**` (or the file's existing style, consistently), with no spaces inside the markers. Code
  spans have no padding spaces.
- **Tables**: leading and trailing pipes on every row, the same number of cells in each row, blank lines around the table. Follow
  the project's table style; markdownlint's `MD060` wants each table to use one style throughout. The fallback config uses compact
  cells (one space on each side, no padding to line up columns) with the delimiter row's dashes padded to the header widths. Give
  every column an explicit alignment marker in the delimiter row, chosen by what the column holds:

  | Column holds | Marker | Why |
  | :----------- | :----: | :-- |
  | Text, names, paths, identifiers, or a mix (the default) | `:---` | Reads naturally; states the default outright |
  | Numbers: counts, sizes, durations, percentages | `---:` | Digits line up by place value |
  | Only short words of similar length (`yes`/`no`, `true`/`false`, `pass`) | `:---:` | A narrow column of flags scans as a column |

  Markdown renders an unmarked column left-aligned anyway, but the marker records the choice so nobody has to guess. No linter
  checks this, so it is guidance: when a column is mixed or the choice is unclear, use `:---`.
- **Blockquotes**: two blockquotes separated only by a blank line trip `MD028`. For stacked GitHub alerts (`> [!WARNING]`), put a
  sentence of prose between them; joining them with a `>` line would turn the second alert into plain text.
- **Whitespace**: no trailing spaces and no tabs. For a hard line break, end the line with `\` rather than two invisible spaces.
- **Line length**: follow the project's setting. With the fallback config, keep prose lines within 132 characters; headings, code,
  and tables are exempt. Break long paragraphs at sentence or clause boundaries, not mid-phrase. The fallback's `rumdl fmt` rewraps
  every paragraph and list item to fill lines up to 132 columns, not only the ones that are too long, so expect line breaks to move.
- **HTML**: avoid inline HTML when Markdown can express it. Where it cannot (`<details>`, `<kbd>`, `<br>` in a table cell), expect
  `MD033` to need an allowance in the project config.

## Bundled Resources

- [references/tools.md](references/tools.md): per-tool commands, fix behavior, exit codes, configuration, and inline suppression.
  Read it when running anything other than the fallback, or when a tool behaves unexpectedly.
- [references/rules.md](references/rules.md): every rule, grouped by whether tools fix it, with how to fix the ones they do not.
  Read it when a rule fails that autofix did not clear, or when fixing by hand.
- [assets/rumdl.toml](assets/rumdl.toml): the fallback configuration. markdownlint defaults, except that prose wraps at 132 columns,
  headings, code blocks, and tables are exempt from the length limit, tables use compact cells with an aligned delimiter row
  (`MD060`, which rumdl leaves off by default), and every paragraph is rewrapped to fill 132 columns.
