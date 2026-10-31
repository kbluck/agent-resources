# Markdown Rules

The markdownlint rule set, which rumdl, markdownlint-cli2, markdownlint-cli, and PyMarkdown all implement. Source:
[markdownlint Rules.md](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md). Defaults below are markdownlint's; the
project's configuration may change any of them.

## Contents

- [Rules autofix handles](#rules-autofix-handles)
- [Rules that need judgment](#rules-that-need-judgment)
- [Rules that autofix can get wrong](#rules-that-autofix-can-get-wrong)
- [Off by default](#off-by-default)
- [Configuration examples](#configuration-examples)

## Rules Autofix Handles

Run the tool's fix command and these clear without help. Fix by hand only when no tool can run.

| Rule | Alias | Requirement |
| :--- | :---- | :---------- |
| MD004 | ul-style | Same bullet marker throughout (default: whichever the file uses first) |
| MD005 | list-indent | Items at the same level are indented the same |
| MD007 | ul-indent | Nested bullets indent 2 spaces per level |
| MD009 | no-trailing-spaces | No trailing whitespace, except exactly 2 spaces as a hard line break |
| MD010 | no-hard-tabs | No tab characters, including in code blocks |
| MD011 | no-reversed-links | `[text](url)`, not `(text)[url]` |
| MD012 | no-multiple-blanks | At most one blank line in a row |
| MD018 | no-missing-space-atx | `# Heading`, not `#Heading` |
| MD019 | no-multiple-space-atx | One space after the `#`s |
| MD020 | no-missing-space-closed-atx | Closed headings have spaces inside: `# Heading #`, not `#Heading#` |
| MD021 | no-multiple-space-closed-atx | One space inside each end of a closed heading |
| MD022 | blanks-around-headings | A blank line above and below each heading |
| MD023 | heading-start-left | Headings start in column 1 |
| MD027 | no-multiple-space-blockquote | One space after `>` |
| MD030 | list-marker-space | One space after a list marker |
| MD031 | blanks-around-fences | A blank line above and below each fenced code block |
| MD032 | blanks-around-lists | A blank line above and below each list |
| MD037 | no-space-in-emphasis | `**bold**`, not `** bold **` |
| MD038 | no-space-in-code | `` `code` ``, not `` `  code  ` `` (a single space each side is allowed) |
| MD039 | no-space-in-links | `[text](url)`, not `[ text ](url)` |
| MD047 | single-trailing-newline | The file ends with exactly one newline |
| MD049 | emphasis-style | Same italic marker throughout (`*` or `_`) |
| MD050 | strong-style | Same bold marker throughout (`**` or `__`) |
| MD058 | blanks-around-tables | A blank line above and below each table |

## Rules That Need Judgment

Tools report these but cannot fix them, because the fix depends on what the document means. This is where most of the work is.

### Structure

- **MD001 heading-increment**: levels go down one at a time (`##` then `###`, never `##` then `####`). Promote the skipped heading
  rather than inserting an empty one. Raising levels can be wrong when the deeper heading belongs under a section that is missing;
  read the outline first.
- **MD003 heading-style**: one heading style per file. Convert Setext (`Title` over `=====`) to ATX (`# Title`).
- **MD024 no-duplicate-heading**: no two headings with the same text. Make each one specific (`## Install on Linux`,
  `## Install on macOS`). Repeated headings under different parents are normal in changelogs; if the project uses that pattern,
  `siblings_only: true` is the fix, which is a config change to suggest, not to make.
- **MD025 single-h1**: one top-level heading. Demote the extras, and their subsections with them. A `title:` in front matter counts
  as the H1.
- **MD036 no-emphasis-as-heading**: a paragraph that is only bold or italic text reads as a heading. Make it a real heading at the
  right level, or, if it is a label, put the text after it on the same line (`**Note:** text`). Lines ending in punctuation are not
  flagged.
- **MD041 first-line-h1**: the file starts with a top-level heading (after front matter). Add one that names the document. Files
  that are fragments or included into another page often turn this off in config.
- **MD043 required-headings**: only when configured; match the configured outline.

### Code

- **MD014 commands-show-output**: drop `$` prompts from a block of commands with no output. Keep them, and the output, when the
  block shows a session. Autofix handles the simple case. This is a formatting fix, not a wording change. markdownlint checks every
  fenced block; rumdl checks only blocks tagged as shell, so retagging a block as `text` hides the prompts from rumdl but not from
  markdownlint.
- **MD040 fenced-code-language**: every fence names a language. Pick it from the content: `bash`, `sh`, or `shell` for shell,
  `powershell`, `console` for a session with prompts and output, `json`, `yaml`, `toml`, `diff`, `text` for plain output or prose. A
  `language_only` setting forbids anything after the language (`js title="x"`).
- **MD046 code-block-style**: one block style per file. Convert indented code blocks to fences, which can carry a language.
- **MD048 code-fence-style**: one fence character per file, usually backticks. A tilde fence is fine for showing backtick fences,
  but a longer backtick fence (four or more) does the same job and keeps the style consistent.

### Links and Images

- **MD034 no-bare-urls**: wrap a bare URL as `<https://example.com>` or give it link text. Autofix adds the angle brackets; giving
  it descriptive text is better in prose.
- **MD042 no-empty-links**: `[text]()` or `[text](#)` has no destination. Find the right URL or remove the link and keep the text.
- **MD045 no-alt-text**: describe what the image shows or why it is there (`![Login form with the error banner](login.png)`), not
  its filename. A decorative image can use HTML `alt=""`, which `MD033` may then flag.
- **MD051 link-fragments**: `#fragment` must match a heading's anchor. GitHub's anchor is the heading text, lowercased, with spaces
  turned into hyphens and punctuation other than hyphens and underscores dropped: `## Step 2: Run it` becomes `#step-2-run-it`.
  Duplicate headings get `-1`, `-2` suffixes. Autofix corrects case only.
- **MD052 reference-links-images**: `[text][label]` needs a `[label]: url` definition somewhere in the file. Add it or switch to an
  inline link.
- **MD053 link-image-reference-definitions**: a `[label]: url` definition that nothing uses. Autofix removes it; check first that it
  is not a typo for a label that is used.
- **MD054 link-image-style**: only when configured; convert links to the allowed style.
- **MD059 descriptive-link-text**: link text such as "here", "link", "more", or "click here" says nothing out of context. Rewrite
  the sentence so the link text names the target: `see the [installation guide](install.md)`.

### Tables

- **MD055 table-pipe-style**: same leading and trailing pipe style on every row; add the missing pipes, usually both ends.
- **MD056 table-column-count**: every row has the same number of cells as the header. Add empty cells or fix a stray `|` in the
  content (escape a literal pipe as `\|`).
- **MD060 table-column-style**: each table's pipes follow one style: `aligned` (pipes line up), `compact` (one space around each
  cell), or `tight` (no spaces). The default, `any`, accepts any of them but not a mix within one table, which is what a table with
  some padded rows and one long row produces. Autofix usually realigns it; if it cannot (rows with escaped pipes or code spans), pad
  the cells by hand.

### Other

- **MD013 line-length**: see the next section.
- **MD026 no-trailing-punctuation**: remove `.,;:!` from the end of a heading. Question marks are allowed by default.
- **MD028 no-blanks-blockquote**: a blank line between two blockquotes is ambiguous. Join them with a `>` line if they are one
  quote, or put text between them if they are two. Two GitHub alerts (`> [!NOTE]`) are always two: put a sentence between them,
  since joining them makes the second marker plain text. markdownlint flags stacked alerts; rumdl does not.
- **MD029 ol-prefix**: ordered lists number `1. 2. 3.` or all `1.`. A list that restarts at 1 after a code block was probably meant
  to continue: indent the code block under the item (3 spaces for `1.`) so the list is not broken.
- **MD033 no-inline-html**: replace HTML with Markdown where possible (`<b>` becomes `**`, `<a href>` becomes a link). Elements with
  no Markdown form (`<details>`, `<summary>`, `<kbd>`, `<sup>`, `<br>` in a table cell) need `allowed_elements` in config; tell the
  user rather than changing the file.
- **MD035 hr-style**: one horizontal rule style per file, usually `---`.
- **MD044 proper-names**: only when `names` is configured; autofix applies the capitalization outside code.

## Rules That Autofix Can Get Wrong

Read the diff after autofix for these.

- **MD013 line-length**: markdownlint never fixes it. rumdl fixes it only with `reflow = true`. To fix by hand, break the line at a
  sentence or clause boundary. Never break inside a link, code span, or URL, and never add a line break that changes rendering (a
  line starting with `-`, `+`, `1.`, `#`, or `>` after wrapping becomes a list item, heading, or quote). Lines that cannot be
  shortened (a long URL alone, a table row, a heading) are exempt by default or by the fallback config; if the project config still
  flags them, reference-style links move long URLs out of the line.
- **MD029 ol-prefix**: renumbering a list split by an unindented block hides the real problem; see above.
- **MD034 no-bare-urls**: angle brackets around something that only looks like a URL, such as `user@host` in a command, change its
  meaning. Put such text in a code span instead.
- **MD049 / MD050**: an `_` inside a word (`snake_case`) or a `*` used as multiplication is not emphasis; put it in a code span if a
  tool misreads it.
- **MD009 no-trailing-spaces**: removing two trailing spaces removes a hard line break. If the break mattered, use `\` at the end of
  the line instead.

## Off by Default

`MD013` is on by default with an 80-column limit, which most projects relax or disable. `MD043`, `MD044`, and `MD054` do nothing
until configured. In markdownlint, `MD060` defaults to `any`, which allows any table style as long as each table is consistent.
rumdl turns `MD060` off unless it is enabled, so a rumdl-only check passes tables that markdownlint rejects; the fallback config
enables it with `style = "compact"` and `aligned-delimiter = true`.

## Configuration Examples

The fallback's settings, as markdownlint configuration (`.markdownlint.jsonc`), for projects that use a markdownlint CLI:

```jsonc
{
  "default": true,
  "MD013": { "line_length": 132, "headings": false, "code_blocks": false, "tables": false },
  "MD060": { "style": "compact", "aligned_delimiter": true }
}
```

Common additions, to suggest when a project's content calls for them:

```jsonc
{
  "MD024": { "siblings_only": true }, // changelogs repeat "Added", "Fixed"
  "MD033": { "allowed_elements": ["details", "summary", "kbd", "br"] },
  "MD041": false                      // files included into other pages
}
```
