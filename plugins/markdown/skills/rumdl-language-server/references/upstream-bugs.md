# Upstream Bugs in Rumdl's Language Server

Bugs found in rumdl 0.3.2 while writing this skill, reported upstream on 2026-11-09. `scripts/rumdl_lsp.py` works around bugs 1, 2,
and 4 and says on stderr when it does. Claude Code's `LSP` tool talks to the server directly, so its answers still have them.
Recheck each repro on a newer rumdl, and remove a workaround from the script once its bug is fixed.

| # | Bug | Issue | Affects | Script workaround |
| :- | :-- | :---- | :------ | :---------------- |
| 1 | Link-like text in inline code is indexed as a link | [#985](https://github.com/rvben/rumdl/issues/985) | Find references, rename | Drops matches inside inline code |
| 2 | Reference definitions are not in the link index | [#986](https://github.com/rvben/rumdl/issues/986) | Find references, rename | Adds definitions that point at the target |
| 3 | `MD051` does not check fragments in reference definitions | [#984](https://github.com/rvben/rumdl/issues/984) | `rumdl check`, diagnostics | None; the script's `references` lists them |
| 4 | Rename rewrites the front of a longer anchor (`#setup` in `#setup-1`) | [#987](https://github.com/rvben/rumdl/issues/987) | Rename | Drops those edits and moves the links correctly |

All repros use a fresh git repository with no rumdl config. Language-server positions are 0-based, as LSP sends them; `rumdl check`
lines are 1-based.

## 1. Inline Code Is Indexed as a Link

**Summary**: when a reference-style link (`[text][id]`) comes earlier on the same line, `textDocument/references` and
`textDocument/rename` treat `` `[text](file.md#anchor)` `` inside a later inline code span as a real link. Rename rewrites the code
span's text, which changes a literal example in the document. Without the reference-style link on the line, the code span is
correctly skipped; fenced code blocks are always skipped, and `rumdl check` is unaffected.

`t.md`:

```markdown
# T

## Sec

Text.
```

`a.md`:

```markdown
# A

See [one][r1] and `[code](t.md#sec)`.

[r1]: t.md
```

**Steps**: `textDocument/references` at `t.md` line 2, character 3 (the `## Sec` heading); then `textDocument/rename` at the same
position with `newName` `"Section Two"`.

**Expected**: no references, and a rename that edits only `t.md`.

**Actual**: references returns `a.md` line 2, character 26, inside the code span. Rename returns an edit in `a.md`, characters 31 to
34, that changes the code span to `` `[code](t.md#section-two)` ``. With `See [one](t.md) and` in place of `See [one][r1] and`,
neither happens.

## 2. Reference Definitions Are Missing from the Link Index

**Summary**: the workspace index records inline links but not reference definitions (`[id]: file.md#anchor`). So
`textDocument/references` on a heading or file omits them, and `textDocument/rename` of a heading leaves them pointing at the old
anchor. Go to definition on `[text][id]` or on the definition line works, so the definitions are parsed; they are just not indexed.
A heading rename therefore silently breaks every reference-style link to it.

`t.md` as in bug 1. `a.md`:

```markdown
# A

See [one][r1] and [two][r2].

[r1]: t.md#sec
[r2]: t.md
```

**Steps**: `textDocument/references` at `t.md` line 2 (the heading); `textDocument/references` at a position in `t.md` that is on no
heading or link (all links to the file); `textDocument/rename` at the heading with `newName` `"Section Two"`.

**Expected**: the heading's references include `a.md` line 4 (`[r1]`); the file's references include lines 4 and 5; the rename
changes line 4 to `[r1]: t.md#section-two`.

**Actual**: no references in either case, and the rename edits only `t.md`. After the rename, `[r1]` points at an anchor that does
not exist, and nothing reports it (see bug 3).

## 3. MD051 Does Not Check Fragments in Reference Definitions

**Summary**: `MD051` (link fragments should reference valid headings) checks inline links, same-file and cross-file, but not
reference definitions. `MD057` does check the path in a reference definition, so the gap is specific to fragments.

`t.md` as in bug 1. `a.md`:

```markdown
# A

See [one][r1], [two][r2], and [three](t.md#nope).

[r1]: t.md#nope
[r2]: #missing
```

**Steps**: `rumdl check --no-config .`

**Expected**: `MD051` on line 3 (`t.md#nope`), line 5 (`t.md#nope`), and line 6 (`#missing`).

**Actual**: only line 3 is reported. The language server's diagnostics are the same.

## 4. Rename Rewrites Longer Anchors That Start with the Old One

**Summary**: renaming a heading whose anchor is `setup` also edits cross-file links to `#setup-1` (the second heading with the same
text), replacing the `setup` part and producing `#first-setup-1`, which does not exist. Find references on the same heading
correctly returns only the `#setup` link, so the matching differs between the two requests. Separately, the rename does not update
links to `#setup-1` itself, although after the rename that heading's anchor becomes `#setup`; this second part may be intended, but
it breaks those links too.

`a.md`:

```markdown
# A

## Setup

One.

## Setup

Two.
```

`b.md`:

```markdown
# B

[x](a.md#setup-1) and [y](a.md#setup)
```

**Steps**: `textDocument/references` at `a.md` line 2, character 3; then `textDocument/rename` at the same position with `newName`
`"First Setup"`.

**Expected**: references returns `b.md` character 22 only (it does). Rename changes `a.md#setup` to `a.md#first-setup` and
`a.md#setup-1` to `a.md#setup`, since the second heading is now the only `Setup`.

**Actual**: rename returns two edits in `b.md` with `newText` `"first-setup"`: characters 31 to 36 (correct) and 9 to 14 (the front
of `setup-1`). Applying them gives `[x](a.md#first-setup-1)`, which `rumdl check` then reports as `MD051`.
