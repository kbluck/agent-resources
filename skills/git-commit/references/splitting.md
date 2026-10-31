# Splitting changes into atomic commits

Agents cannot drive `git add -p` or `git add -i`, because both wait for keyboard input. Use these non-interactive techniques instead.

## Whole files

Stage the files for the first commit by path, commit, then repeat for the next group.

```bash
git reset -q                         # start from an empty index (keeps working tree changes)
git add -- src/parser.ts src/parser.test.ts
git commit -F <tmp>/msg-1.txt        # fix(parser): accept empty input
git add -- README.md
git commit -m "docs: correct install command"
```

Only reset the index if you have noted what the user had staged and they did not intend it as a single commit.

## Individual hunks in one file

When one file contains two unrelated changes in separate hunks, stage a subset of its hunks with a patch applied to the index:

1. Save the file's diff: `git diff -- path/to/file > <tmp>/full.patch` (put the patch outside the repository).
2. Copy it to `<tmp>/part.patch` and delete the hunks that do not belong in this commit. Keep the `diff --git`, `index`, `---`, and `+++` header lines. Delete whole hunks only, from one `@@` line up to (not including) the next `@@` line. Hunk line numbers do not need adjusting; `git apply` locates hunks by context.
3. Check, then stage: `git apply --cached --check <tmp>/part.patch && git apply --cached <tmp>/part.patch`.
4. Verify: `git diff --staged -- path/to/file` should show only the intended hunks, and `git diff -- path/to/file` the rest.
5. Commit, then stage the remainder normally with `git add -- path/to/file`.

The working tree is never touched, so nothing is lost if a step fails; `git reset -q -- path/to/file` undoes the staging.

If two unrelated edits fall inside the same hunk (adjacent lines), regenerate the diff with less context to separate them: `git diff -U1 -- path/to/file` (or `-U0`, which then needs `git apply --cached --unidiff-zero`). If they still cannot be separated, commit them together and mention both in the message, or ask the user.

## Whole new versions of a file

For complex cases, you can stage an exact intermediate version of a file without touching the working tree:

```bash
blob=$(git hash-object -w <tmp>/intermediate-version)
git update-index --cacheinfo 100644,"$blob",path/to/file
```

Use `100755` for executable files. Verify with `git diff --staged` before committing.

## Ordering and integrity

- Put preparatory work (refactors, renames, new helpers) before the commit that uses it.
- Each commit should build and pass tests on its own. If an intermediate state cannot work, merge those pieces into one commit instead of splitting.
- After the last commit, `git status --porcelain` should show only what the user intends to leave uncommitted.
