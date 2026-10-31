---
name: git-commit
description: 'Create well-formed Git commits: inspect the diff, group work into right-sized commits, stage the right files, write a concise Conventional Commits message that says why the change was made, and run git commit safely. Use this skill whenever the user asks to commit, make a commit, "/commit", save or check in their work, split or squash changes into commits, or wants a commit message written, reviewed, or fixed, even if they only ask for the message and do not want the commit made. Also use it when finishing a coding task that the user expects to be committed, and when choosing a commit type (feat, fix, chore, docs, ...), scope, or how to mark a breaking change. Not for pushing, opening pull requests, or rewriting published history.'
license: MIT
compatibility: Requires Git.
---

# Git Commit

Make commits that a reviewer can read, a bisect can trust, and a release tool can parse. Each commit holds one complete concern, leaves the project working, and carries a short message that tells a future reader why the change exists and where to look for more.

The default message format is [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). The repository's own rules always win over this skill.

## Two modes

- **Commit mode** (the default): the user wants the work committed. Inspect, group, write the message, commit, verify.
- **Message-only mode**: the user asks for a message ("write a commit message", "what should I call this commit?", "review this message") or says not to commit yet. Do steps 1 to 4 below, then present the message in a fenced code block and stop. Do not stage or commit anything. Add one plain sentence after the block summarizing what the message says, so the user can check it matches their intent.

If the input is a pasted diff or a description rather than a repository, work from that and use message-only mode.

## Workflow

### 1. Learn the repository's conventions

Look before you write. A repository that already has rules expects you to follow them, and its history shows its real style.

- Commit lint configuration: `commitlint.config.*`, `.commitlintrc*`, a `commitlint` key in `package.json`, `.czrc`, `cz.toml` / `[tool.commitizen]` in `pyproject.toml`, `cliff.toml`, `.releaserc*`, `lefthook.yml`, `.pre-commit-config.yaml`.
- Written guidance: `CONTRIBUTING.md`, `AGENTS.md`, `CLAUDE.md`, `.github/` templates.
- Recent history: `git log --oneline -15`. Note the types and scopes in use, capitalization after the colon, whether bodies are common, and how issues are referenced.

If the history does not use Conventional Commits (for example the kernel-style `subsystem: summary`, or plain capitalized sentences), match the established style and apply the rest of this skill (right-sized commits, imperative subject, short explanatory body). If a lint config restricts types, scopes, or lengths, those limits are binding because the commit hook will reject anything else.

### 2. Examine the changes

```bash
git status --porcelain
git diff --staged
git diff
git log --oneline @{upstream}..HEAD   # local commits not yet pushed, if a remote branch exists
```

Read the diff itself, not only the file names; the type and the reason come from the content. Read untracked files too. If there is nothing to commit, say so and stop; never create an empty commit unless asked.

Note what the user had already staged. Treat a deliberately staged set as the intended commit unless it clearly mixes unrelated concerns, in which case say so before restaging.

### 3. Decide what each commit contains

A commit is one *concern*: a reason for changing the code that a reader would want to understand, review, or revert as a unit. Aim for commits that are complete, not merely small.

**Keep together:**
- A change and everything it needs: tests, callers, docs, config, migrations. An intermediate commit should never fail to build or pass tests.
- Incidental edits prompted by the main change. A typo fixed in a docstring you were already rewriting, or a README line updated because the feature changed it, belongs in that feature's commit.
- Successive attempts at the same concern. If the work went through several iterations (first try, fix to the first try, review tweak), the history should show one commit with the final result, not the path to it. See [Combining commits](#combining-commits).

**Separate:**
- Concerns that are independent: different reasons, each of which would make sense alone. A crash fix and an unrelated new CLI flag are two commits. A typo in a file nothing else touched, fixed in passing, is its own `docs` commit.
- Pure formatting churn mixed with real changes: commit it separately (`style:`) so the real diff stays readable.
- Distinct concerns in the same file, when the hunks are separable. See [references/splitting.md](references/splitting.md) for staging individual hunks without interactive tools.

A useful test: if the honest subject needs "and" to join two changes, it is probably two commits, unless one is incidental to the other, in which case the subject names only the main change.

When the grouping is genuinely ambiguous, ask the user. When it is clear, proceed and report what you did. Order separate commits so each builds on the last: preparatory refactors before the feature that uses them.

### 4. Write the message

```text
<type>[(<scope>)][!]: <description>

[body]

[footer(s)]
```

**Type.** Pick the type that describes the change's effect on the project. `feat` and `fix` are defined by the spec; the rest come from the widely used Angular / `@commitlint/config-conventional` set. Use the repository's list if it has one.

| Type       | Use for                                                              | Release effect |
| ---------- | -------------------------------------------------------------------- | -------------- |
| `feat`     | New capability for users of the code (API, CLI, UI)                  | minor          |
| `fix`      | Correcting wrong behavior that users of the code would notice        | patch          |
| `perf`     | Making existing behavior faster or cheaper, nothing else             | none\*         |
| `refactor` | Restructuring code without changing behavior                         | none           |
| `docs`     | Documentation only, including code comments and READMEs              | none           |
| `style`    | Formatting, whitespace, import order; no logic change                | none           |
| `test`     | Adding or correcting tests only                                      | none           |
| `build`    | Build system, packaging, or dependency changes                       | none           |
| `ci`       | CI pipeline configuration                                            | none           |
| `chore`    | Maintenance that fits nothing above (tooling config, `.gitignore`)   | none           |
| `revert`   | Undoing an earlier commit                                            | depends        |

\* Some release configs bump the patch version for `perf`. Any type with a breaking change triggers a major bump.

Choosing between close types:
- `fix` vs `feat`: if users could not do it at all before, it is `feat`; if it was supposed to work and did not, it is `fix`.
- `refactor` vs `fix`/`feat`: if observable behavior changes at all, it is not a refactor.
- `chore` is a last resort, not a default. A dependency bump is `build`; a test fix is `test`; a doc change is `docs`.

**Scope.** Optional. A short noun naming the area affected: a module, package, or component (`auth`, `parser`, `api`, `deps`). Reuse scopes from history; do not invent `user` when the repo uses `users`. Omit the scope when the change is global or no single area fits.

**Subject (description).**
- Imperative mood, completing "If applied, this commit will ...": `add`, `fix`, `remove`, not `added`, `adds`, or `adding`.
- Drop articles (`a`, `an`, `the`): `fix crash on empty input`, not `fix a crash on the empty input`. The subject is a headline; the body is ordinary prose and keeps its articles.
- Lowercase first word after the colon unless the repo capitalizes, and no trailing period.
- Keep the whole header within 72 characters; around 50 is better.
- Specific: name the thing and the effect. `fix(cart): prevent duplicate items on rapid clicks`, not `fix: bug fix` or `update cart.js`.

**Body.** Give every `feat` and `fix`, and every breaking change, a body. For other types, add one only when the reason is not obvious from the subject (`docs: fix typo in install guide` needs nothing more).

The body is a signpost, not documentation. In a few sentences, tell a future reader why this change exists: the problem or need, and, if it is not obvious, the essential effect of the solution. Then stop. Most bodies are one short paragraph; two or three is the upper end.

Leave out:
- **The journey.** Not the investigation, the approaches tried and abandoned, the iterations, the bugs hit along the way, or review back-and-forth. The commit records the final result; describe that.
- **The inventory.** Not a file-by-file or line-by-line list of what changed. The diff already shows that.
- **Material that belongs elsewhere.** Usage, design rationale in depth, gotchas, and how the code works belong in documentation, code comments, or the code itself, where they stay current. If such detail matters, put it there and let the body point to it ("See docs/caching.md.").
- **Commit hashes.** See [Referencing other changes](#referencing-other-changes).
- Future tense ("this will fix") and first person ("I changed").

**Line length.** Wrap every line of the body and footers at 72 columns. Many tools display messages unwrapped, and `git log` indents them by 4 more columns. Long URLs and code that cannot break may run over.

**Footers.** One blank line after the body, one per line, in Git trailer form `Token: value`. Tokens use `-` instead of spaces (`Reviewed-by`, `Co-authored-by`, `Refs`). If a value wraps, indent its continuation lines with a space; Git and Conventional Commits parsers both read that as one value.
- Issue references: follow the repo's style. `Closes #123` / `Fixes #123` auto-close issues on GitHub and GitLab; `Refs: #123` links without closing. Git's trailer parser only recognizes the `Token: value` form, so prefer `Closes: #123` unless the repo uses the other. Never invent issue numbers; omit the footer if you do not have one.
- Attribution trailers (`Co-authored-by`, tool attribution lines): add them only when the user, the repository, or the harness configuration asks for them.

**Breaking changes.** Any change that requires users of the code to change theirs (removed or renamed public API, changed defaults, dropped platform support, incompatible config or data format) must be marked, whatever its type:
- Add `!` before the colon: `feat(api)!: remove v1 endpoints`.
- Add a footer written exactly `BREAKING CHANGE: <what breaks and what to do>` or `BREAKING-CHANGE: ...` (uppercase; the spec treats them as equivalent).
- Use both: the `!` shows in one-line logs, the footer tells users what to do.

Choosing the footer token: Git does not accept a token containing a space, so a `BREAKING CHANGE:` line makes `git interpret-trailers`, and tools built on it, ignore every trailer in that paragraph, including `Refs` and `Co-authored-by`. Use the repository's established form. Otherwise, write `BREAKING-CHANGE:` when the message has other trailers, and `BREAKING CHANGE:` when it stands alone (some older release tools recognize only that spelling).

See [references/conventional-commits.md](references/conventional-commits.md) for the full spec rules, SemVer mapping, and edge cases (reverts, merge commits, initial development, wrong type). See [references/examples.md](references/examples.md) for worked examples and common mistakes.

### 5. Stage and commit

Stage exactly the files for this commit, by explicit path:

```bash
git add -- src/auth/token.ts src/auth/token.test.ts
git add -- 'src/**/*.test.ts'      # quote globs so git, not the shell, expands them
git reset -q -- path/to/unrelated   # unstage what does not belong
```

- Avoid `git add -A` / `git add .` unless you have checked that every changed and untracked file belongs in this commit.
- Do not use `git add -p`, `git add -i`, `git rebase -i` without a scripted editor, or `git commit` without `-m`/`-F`: they wait for interactive input.
- Check the staged set: `git diff --staged --name-only`. Never commit secrets or machine-local files (`.env`, `*.pem`, `id_rsa`, credentials JSON, tokens in config). If one is present, leave it unstaged and tell the user; suggest a `.gitignore` entry if it is not already ignored.
- Do not commit generated artifacts, build output, or large binaries unless the repository already tracks them.

Commit with the message in a file. Write the message, already wrapped at 72 columns, to a temporary file outside the repository, then:

```bash
git commit -F <path-to-message-file>
```

This preserves your line breaks exactly and avoids shell quoting problems with backticks, `$`, `!`, and quotes on every platform. A subject-only message can use `git commit -m "<subject>"` instead. Avoid putting a body in `-m` arguments: each `-m` becomes one unwrapped paragraph.

### 6. Verify

```bash
git log -1 --format='%B' --stat
git log -1 --format='%B' | awk 'length > 72'   # should print nothing
git status --porcelain
```

Confirm the message is intact, lines are wrapped, the right files went in, and nothing intended was left behind. Report each commit to the user by its subject line (a short hash is fine in chat).

## Combining commits

Too many commits is as much a problem as too few. When several unpushed commits are really attempts at the same concern, fold them into one before you finish:

- Your own last commit, same concern: stage the follow-up change and `git commit --amend -F <message-file>` (or `--amend --no-edit` if the message still fits).
- Several recent commits: `git reset --soft <base>` to collapse them into the index, then commit once with a message describing the final result.
- An older commit, with others after it: `git commit --fixup=<target>` then `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <target>~1`. The environment variable accepts the generated todo list, so no editor opens.

Only rewrite commits that have not been pushed or shared (check `git log @{upstream}..HEAD`, or `git branch -r --contains <commit>`). Commits you made during the current task you may fold freely. For commits that already existed when you started, propose the squash and wait for the user's agreement, since it rewrites their history.

## Referencing other changes

Do not use commit hashes as lasting references, in commit messages or anywhere else in the project (code comments, docs, changelogs, TODOs). Rebases, squash merges, and history cleanup routinely replace or delete commits, leaving the hash pointing nowhere. Tags have the same weakness unless something guarantees they are maintained when history is rewritten.

Prefer not to point at specific changes at all. When a reference genuinely helps, describe the change by what it did ("the empty-input fix in the parser"), or cite something durable outside the history: an issue, a pull request, a release version, a document. If a hash is the only handle (as in Git's default revert message), treat it as a convenience that may no longer resolve, and make the surrounding text understandable without it.

## Safety rules

These protect the user's work and history, so treat them as firm unless the user explicitly says otherwise.

- **Hooks.** Never use `--no-verify` to get past a failing hook. A failing pre-commit or commit-msg hook means no commit was created: read the output, fix the cause (or reword the message for commit-msg), restage, and run the same commit again. Do not reach for `--amend` here; with no new commit, it would modify the previous one. If a hook reformats files, restage them and commit again.
- **Published history.** Do not amend, rebase, or reset commits that have been pushed or shared, and never force-push, unless the user asks.
- **No destructive cleanup.** Do not `reset --hard`, `checkout -- .`, `clean`, or otherwise discard uncommitted work.
- **No configuration changes.** Do not change `user.name`, `user.email`, signing settings, or hooks. If a commit fails for identity or signing reasons, report it.
- **No push.** Committing does not imply pushing. Push only when asked.
- **Committing at all.** Do not commit on your own initiative unless the user or the project's instructions have asked you to commit as you work.
