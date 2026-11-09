---
name: rumdl-language-server
description: >
  Use rumdl's Markdown language server instead of grep, sed, or reading every file whenever you work with the headings and links of
  Markdown docs. It answers exactly: which file covers a topic, what a file's sections are, what links to a file or section, the
  exact anchor to link to, where a link goes, and it renames a heading together with every link to it. Use this skill before you
  move, rename, split, merge, or delete a Markdown file or section, since every relative link to it and from it has to change;
  before you rename, reword, or renumber a heading in a .md file; and when you add a cross-reference, ask "what links here?" or
  "where is X documented?", explore an unfamiliar docs folder, or see MD051 or MD057 broken-link diagnostics, even if the user never
  mentions an LSP or rumdl. Not for fixing lint or formatting (use the formatting skill) or for structure and wording (use the
  authoring skill).
compatibility: >
  Uses the harness's LSP tool when rumdl's server is registered with it. Otherwise runs the bundled scripts/rumdl_lsp.py, which needs
  Python 3.8+ and one of rumdl, uv (uvx), Bun (bunx), or Node.js (npx) to run rumdl.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/markdown/skills/rumdl-language-server
  version: 1.0.0
---

# Rumdl Language Server

A set of Markdown documents is a graph: files link to files by relative path and to sections by heading anchor. rumdl's language
server indexes that graph for the whole workspace, with every heading, its anchor, and every link, and answers questions about it
with the same rules its link checks (`MD051`, `MD057`) use. Grep sees only text. Ask the server first, every time the question is
about headings or links.

## Ask the Server, Not Grep

The habit to break is reaching for `grep -rn`, `sed -i`, or `cat` on every file to answer questions the server answers exactly. Make
the server your first move on any task that touches Markdown headings or links, before any grep or `cat` of a `.md` file, and your
last move when checking the result.

| Instead of | Ask the server | Because grep |
| :--------- | :------------- | :----------- |
| `grep -ri topic docs/` to find where something is documented | `headings QUERY` | Matches prose, code blocks, and comments; the server searches headings only |
| `cat` each file, or `grep '^#'`, to learn a file's sections | `outline FILE` | Reads whole files to get a few lines, and counts `#` lines in code blocks |
| `grep -rn guide.md` to find what links to a file | `references FILE` | Misses `./guide.md`, `../docs/guide.md`, and the same file named from other folders |
| `grep -rn '#install'` to find links to a section | `references FILE:LINE` | Cannot tell `guide.md#install` from `other.md#install`, or `#install` from `#install-1` |
| Slugifying a heading by hand to write a link | `anchors FILE` | Guesses `## Install & Run (v2)`; the anchor is `#install--run-v2` |
| `sed -i 's/#old/#new/g'` after renaming a heading | `rename FILE:LINE "New text"` | Rewrites same-named anchors in other files and in code examples, and misses shifted `-1` anchors |
| Opening the target file to see where a link lands | `definition` or `hover` on the link | Has to resolve the relative path and anchor in your head |
| `test -f` plus grep to check links are valid | `rumdl check FILE` | Checks existence, not anchors |
| `grep -rn old.md .` for nav files, HTML, and code | `mentions FILE` or `mentions FILE:LINE` | Also matches all the Markdown the server already answered for |

The server is also faster for anything past a handful of files: one query returns the answer, with no reading.

**Grep is for what the server does not index.** Use it only when you need:

- Text that is not a link or heading: a product name, a phrase, a version number, a TODO.
- Files the server does not index: outside the workspace, excluded by the rumdl config, or gitignored.
- Everything, when neither route below works (no rumdl and no Python). Say that the result is less certain.

Read a file when you need its content to edit it or to judge what a section says, not to discover its structure or links.

Links from files that are not Markdown (site navigation such as `mkdocs.yml` or `_toc.yml`, HTML, source code, CI config) are not in
the index either; `mentions` finds them by the file's path, bare name, or published URL, and leaves Markdown out.

The same goes for checking your work. "Is anything left pointing at the old name?" is a link question: `references` on the new
target, `mentions` on the old one, and `rumdl check` answer it. A grep sweep over Markdown adds nothing the server missed, and it
matches code examples and same-named anchors in other files that should not change.

## Reaching the Server

- **The bundled script** runs anywhere Python and rumdl do, and gives the most complete answers. `scripts/rumdl_lsp.py` (in this
  skill's folder) starts the server, waits for its index, asks one question, and prints the answer with 1-based `FILE:LINE:COL`
  positions. It also covers the server's known gaps (see [Limits](#limits)): it adds reference definitions
  (`[id]: guide.md#anchor`), drops matches inside inline code, and repairs rename's anchor bugs. Notes about those go to stderr. It
  reads files from disk, so save edits first. Each run takes a second or two.

  ```shell
  python3 <skill-dir>/scripts/rumdl_lsp.py <command> ...   # run from inside the repository; --root to point elsewhere
  ```

- **The harness's LSP tool.** The `markdown` plugin registers rumdl's server with Claude Code and Copilot CLI, run through whichever
  of rumdl, `uvx`, `bunx`, or `npx` is available. Claude Code's `LSP` tool then offers `goToDefinition`, `findReferences`, `hover`,
  `documentSymbol`, and `workspaceSymbol`, each taking a file and a 1-based line and character, and the server's diagnostics arrive
  by themselves after each edit of a `.md` file. It is quick for looking around, but read-only (no rename, no anchors) and without
  the script's gap fixes. Its first `findReferences` or `workspaceSymbol` in a session can come back empty ("not fully indexed")
  while the server builds its index; ask again before believing it.

Use the LSP tool for quick navigation. Use the script for rename, anchors, and any "what links here?" whose answer you will act on.
To register the server or change its settings, see [references/setup.md](references/setup.md).

## What to Ask It

| Question | Script command | LSP tool operation |
| :------- | :------------- | :----------------- |
| Where is X documented? | `headings QUERY` | `workspaceSymbol` with a query |
| What sections does this file have? | `outline FILE` | `documentSymbol` |
| What exact anchor do I link to? | `anchors FILE [PREFIX]` | None |
| Where does this link go? | `definition FILE:LINE:COL`, anywhere on the link | `goToDefinition` inside the link's `(...)` |
| What does that section say? | `hover FILE:LINE:COL`, anywhere on the link | `hover` inside the link's `(...)` |
| What links to this section? | `references FILE:LINE` (the heading's line) | `findReferences` on the heading line |
| What else links where this link does? | `references FILE:LINE:COL` | `findReferences` inside the link's `(...)` |
| What links to this file at all? | `references FILE` | `findReferences` on a plain paragraph |
| Rename this heading and fix its links | `rename FILE:LINE "New text" [--apply]` | None |
| What non-Markdown files name this file or section? | `mentions FILE`, `mentions FILE:LINE`, or `mentions FILE#anchor` | None |

Exit status 1 from the script means the server found nothing, which is itself an answer: nothing links there, or the position is not
on a heading or link.

## When to Use It

### Renaming or Rewording a Heading

Changing a heading's text changes its anchor, and every link to the old anchor breaks.

1. Preview: `rename docs/guide.md:42 "New Heading Text"`. It lists each line it would change: the heading, and every link to it in
   every Markdown file, rewritten to the new anchor. Read it.
2. Apply: the same command with `--apply`. It ends with a check read back from the files as written: every Markdown link to the
   file, grouped by the heading it now reaches; any link to an anchor that no longer exists; and the site navigation, HTML, and code
   outside Markdown that still name the old anchor. Fix or report each of those last. Read the whole check, not a `head` or `tail`
   of it: the list is what you would otherwise grep for. Its first line gives the totals, so a cut-off read shows.
3. `rumdl check` the changed files.

The check is the verification. It covers reference definitions and the links to a renumbered duplicate heading, which the server
alone misses. Do not grep for the old anchor or heading text afterwards; that search can only turn up the code examples and other
files' anchors the rename rightly left alone.

### Moving, Splitting, Merging, or Deleting a File or Section

The server cannot rename files, but it can list everything that will break before you do.

1. `references docs/old.md` lists every Markdown link to the file; `references docs/old.md:LINE` lists links to one section. For a
   split, run it on each heading that moves.
2. `mentions docs/old.md` lists non-Markdown files that name the path, including published-site URLs (`docs/old/`).
3. Move the file (`git mv`), then update each link from both lists. Relative paths change with the linking file's folder, so compute
   each from its own location. Update the moved file's own outbound relative links too: `outline` it and `definition` any link you
   are unsure of.
4. Check for leftovers with the server, not grep: `rumdl check` the linking files and the moved file (`MD057` flags paths that no
   longer exist, `MD051` anchors that no longer exist), `references docs/new.md` should list the same links as step 1, and
   `mentions docs/old.md` (it works on a path that is gone) should list nothing. Between them they cover every file a grep for the
   old path would, without its false matches.

### Writing a Link to Another Document

Find the section with `headings QUERY`, get its anchor with `anchors FILE`, write the link, then confirm it with
`definition FILE:LINE:COL` on the new link. Do not derive an anchor by hand: punctuation, Unicode, duplicate headings, and
`{#custom}` ids all change it.

### Finding Your Way Around Unfamiliar Docs

`headings QUERY` finds which file and line discusses a topic; `outline FILE` shows a file's structure in a few lines; `hover` on a
link shows the start of the section it points to. Use them before opening files, and open only the ones you need to read or edit.

### Reading Diagnostics After an Edit

When the harness relays the server's diagnostics after you edit a `.md` file, they are rumdl's lint results for that file, with the
rule code (`MD040`) and a link to its rumdl.dev page. Fix the ones your edit caused, and follow the formatting skill for the rest.
Cross-file results (`MD051` on `other.md#anchor`, `MD057`) depend on the index, so the first diagnostics after the server starts can
lack them; `rumdl check FILE` gives the complete answer.

## Limits

- **Only headings rename.** Renaming a link or a file is not supported.
- **No colliding names.** The server refuses a rename whose new anchor matches another heading in the same file; the script says so.
  Pick a different name, or rename the other heading first.
- **Custom anchors hold**: renaming `## Title {#id}` changes only the text, and no links need updating.
- **GitHub-style anchors**: rename writes anchors in GitHub's slug style. If the project's `MD051` uses another `anchor-style`
  (MkDocs, kramdown), check the new links with `rumdl check`.
- **The index is the workspace's Markdown**, minus files excluded by the rumdl config or `.gitignore`. Links in other files are
  `mentions`'s job (see above). External URLs have no definition or references.
- **Server bugs** in rumdl 0.3.2: rename and references count link-like text in inline code, leave out reference definitions, and
  mangle numbered anchors (`#setup-1`); `MD051` does not check anchors in reference definitions. The script works around all but the
  last, so a broken reference definition is found only by `references` on its target. Details and repros:
  [references/upstream-bugs.md](references/upstream-bugs.md).

## Working with the Other Markdown Skills

- **formatting** owns lint and syntax: fixing diagnostics, `rumdl check --fix`, and suppressing a rule. Where an editor would offer
  the server's "Fix all" or "Ignore for this line" code actions, use the formatting skill's commands; they do the same thing.
- **authoring** owns structure and wording. When it renames sections or splits a file, use this skill for each heading or file it
  changes, so the restructure leaves no broken links.
- Run this skill's checks before the formatting skill's final lint pass.
