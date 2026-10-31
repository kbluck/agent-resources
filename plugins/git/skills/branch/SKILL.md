---
name: branch
description: >
  Name, create, check, and rename Git branches following Conventional Branch (feature/, bugfix/, hotfix/, release/, chore/, and the
  AI agent prefixes such as claude/): pick the type, write a short kebab-case description, branch from the right starting point
  without losing uncommitted work, and switch to it. Use this skill whenever the user asks to create, start, open, or cut a branch,
  "/branch", asks what to name or call a branch, wants a branch name checked against the convention or fixed, or wants a branch
  renamed. Also use it before committing when the work is sitting on main, master, or develop and needs its own branch first. Not
  for switching between existing branches, merging, rebasing, deleting, pushing, or opening pull requests.
compatibility: >
  Requires Git (2.23 or later for git switch; older versions use git checkout -b). Python 3 is optional, for
  scripts/check_branch.py.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/git/skills/branch
  version: 1.0.0
---

# Git Branch

Give each line of work a branch whose name tells a reader what it is for and that tools can parse: `feature/add-oauth-login`,
`bugfix/header-overflow`, `release/v1.2.0`. Create it from the right starting point, and never lose or scramble the user's
uncommitted work while doing so.

The default convention is [Conventional Branch 1.1.0](https://conventionalbranch.org). The repository's own rules always win over
this skill.

## Four Modes

- **Create mode** (the default): the user wants a branch to work on. Follow the [workflow](#workflow) below.
- **Name-only mode**: the user asks for a name ("what should I call this branch?", "suggest a branch name") or says not to create it
  yet. Do steps 1 to 4, present the name in a fenced code block, and stop. If the name is not obvious from the request, add one
  sentence saying which type you chose and why.
- **Check mode**: the user asks whether a name, or the current branch, conforms. See [Checking a name](#checking-a-name). Report; do
  not rename unless asked.
- **Rename mode**: the user wants an existing branch renamed, usually to conform. See [Renaming a branch](#renaming-a-branch).

## The Format

```text
<type>/<description>
```

**Purpose types** say what the work is for. Use the full names unless the repository uses the aliases.

| Type | Alias | Use for |
| :--- | :---- | :------ |
| `feature/` | `feat/` | New capability or an enhancement to existing code, including refactors and performance work |
| `bugfix/` | `fix/` | Correcting wrong behavior, at normal priority |
| `hotfix/` | | An urgent fix for something broken in production, usually shipped outside the normal release flow |
| `release/` | | Preparing a release: version bumps, changelog, final fixes (`release/v1.2.0`) |
| `chore/` | | Work that changes no product behavior: dependencies, docs, CI, build, tooling, tests-only, config |

**AI agent source types** say who opened the branch rather than what it is for: `claude/` (Claude Code), `codex/`, `copilot/`,
`cursor/`, and the vendor-neutral `ai/`.

**Trunk branches** `main`, `master`, and `develop` take no prefix. Never create a branch with a trunk name; branch from the trunk
instead.

**Description rules.** Lowercase `a-z`, digits `0-9`, hyphens between words, and dots only inside version numbers. No spaces,
underscores, uppercase, slashes, or other punctuation. No doubled separators (`--`, `..`), no hyphen next to a dot (`v1.-2`), and no
separator at the start or end. Exactly one `/`, between type and description, so `feature/proj-123/login` is invalid; write
`feature/proj-123-login`.

The authoritative check is this expression (portable to Python, JavaScript, Go, and RE2):

```regex
^(?:main|master|develop|(?:feature|feat|bugfix|fix|hotfix|release|chore|ai|copilot|cursor|claude|codex)/[a-z0-9]+(?:\.[a-z0-9]+)*(?:-[a-z0-9]+(?:\.[a-z0-9]+)*)*)$
```

See [references/conventional-branch.md](references/conventional-branch.md) for the grammar, conformance cases, team extensions,
bots, and enforcement tools. See [references/examples.md](references/examples.md) for worked examples and anti-patterns.

## Workflow

### 1. Learn the Repository's Conventions

A repository that enforces branch names will reject anything else at commit, push, or pull request time, and its existing branches
show its real style. Look first:

- Enforcement config: `cchk.toml` or `commit-check.toml` at the root or in `.github/` (`[branch]` table: `allow_branch_types` adds
  or narrows types, `allow_branch_names` adds trunk-like names), a `check-branch` hook in `.pre-commit-config.yaml`, a `pre-push`
  hook in `.githooks/` or wherever `git config core.hooksPath` points, a branch-name job in `.github/workflows/` or
  `.gitlab-ci.yml`.
- Written guidance: `CONTRIBUTING.md`, `AGENTS.md`, `CLAUDE.md`.
- Existing branches: `git branch -a --format='%(refname:short)'`. Note full names versus aliases (`feature/` or `feat/`), how
  tickets appear (`issue-123-`, `proj-123-`), and any extra types (`docs/`, `refactor/`).
- The environment: if the harness, the user, or the project's instructions mandate a branch name or prefix (some hosted agent
  sessions do), use it.

When the repository allows extra types, use them where they fit; they are a team extension and valid there. When the repository
consistently uses a different scheme altogether (for example `username/topic`), follow it and mention that it is not Conventional
Branch. A configured validator is binding either way.

### 2. Choose the Type

Name the purpose of the whole branch, not of its first commit. A feature branch will also carry tests, docs, and small fixes; it is
still `feature/`.

- `feature/` vs `bugfix/`: if users could not do it at all before, it is a feature; if it was supposed to work and did not, it is a
  bug fix.
- `bugfix/` vs `hotfix/`: `hotfix/` only for an urgent fix to production that cannot wait for the normal release. When in doubt,
  `bugfix/`.
- Refactors and performance work change code, so they are `feature/` (an enhancement), not `chore/`, unless the repository defines
  `refactor/` or `perf/`.
- `chore/` is for work that changes no product behavior. It is not a catch-all for "small".
- When the purpose is genuinely unclear, use `feature/` and say so, rather than asking about something this cheap to rename before
  pushing.

**Agent prefixes.** Use a purpose type by default, even though you are an agent. Use `claude/` (or `ai/`) only when the user asks
for it, the repository's instructions say agent branches should use it, or the repository's existing branches show that convention.
A purpose type tells reviewers and pipelines what the branch does; the agent prefix only says who opened it, which the pull request
already records. When you do use an agent prefix, use the one for the agent you are (`claude/` for Claude Code), or `ai/` if the
repository prefers a vendor-neutral name.

### 3. Write the Description

Name the work, in 2 to 5 words, so someone scanning a branch list knows what it holds.

- Say what changes, not the category again: `bugfix/header-overflow-on-mobile`, not `bugfix/fix-header-bug` or `bugfix/bug`.
- Be specific: `feature/csv-export-for-reports`, not `feature/new-feature` or `feature/updates`.
- If the user gives a ticket or issue number, put it first: `feature/issue-123-oauth-login`, `bugfix/proj-482-null-avatar`
  (lowercase the key). Never invent one.
- Keep the whole name under about 50 characters. Drop articles and filler words.
- No usernames, dates, or "wip"; Git already records who and when, and every branch is work in progress.

**Normalizing.** Convert the user's words to the description rules: lowercase; turn spaces, underscores, slashes, and other
punctuation into hyphens; transliterate accented letters (`café` → `cafe`); collapse repeats; trim the ends. Keep version dots
(`v1.2.0`), but a dot next to a hyphen or at an end must go. When normalizing changes what the user typed in a way they might care
about (a dropped `#`, `C++` becoming `c`, a mixed-case ticket key), show the final name so they can object.

### 4. Validate the Name

Check it before creating it. Run the bundled checker (use `python` or `py` if `python3` is not on the path):

```shell
python3 <skill-dir>/scripts/check_branch.py feature/oauth-login
python3 <skill-dir>/scripts/check_branch.py --allow-type docs docs/api-guide   # repository-defined types
```

It prints `ok` or each reason the name fails, and exits non-zero on failure. Without Python, use the `grep -E` form of the
expression in [references/conventional-branch.md](references/conventional-branch.md#validating-without-python); the form above does
not work with POSIX `grep -E`, and macOS has no `grep -P`.

Then check that Git can create it:

- `git check-ref-format --branch <name>` must succeed. It catches the one case the grammar allows and Git does not: a name ending in
  `.lock`.
- `git show-ref --verify --quiet refs/heads/<name>` succeeds if the branch already exists locally; also look for `origin/<name>` in
  `git branch -r`. If it exists, ask whether the user meant to switch to it, or pick a more specific name. Never overwrite it.
- Git stores branches as paths, so a branch named exactly like a type (`feature`, `bugfix`, `release`, ...) blocks every branch
  under that prefix, and vice versa. Check with `git show-ref --verify --quiet refs/heads/<type>`. If the blocked type has an alias,
  switch to it: `feat/` for a blocked `feature/`, `fix/` for a blocked `bugfix/`, and the other way round. The alias means the same
  thing to every conforming tool, so nothing is lost, and the user's existing branch stays untouched. Tell the user which branch
  blocked the prefix and that you used the alias. Ask instead when the alias is blocked too, when the type has no alias (`hotfix/`,
  `release/`, `chore/`), or when the repository's validator does not allow the alias. Never rename or delete the blocking branch to
  make room.

### 5. Choose the Starting Point

**If the user has uncommitted changes, branch from where they are.** This is the common case: work was done on `main` and now needs
a branch before it is committed. `git switch -c <name>` creates the branch at the current commit and carries the working tree and
index over unchanged. Do not switch to another base first, stash, or pull; any of those can lose, mix, or conflict with that work.

If the user also wants the branch based on the latest trunk, fetch and branch from the remote ref in one step: `git fetch origin`
then `git switch --no-track -c <name> origin/<trunk>`. Git carries the uncommitted changes across when the files they touch did not
change upstream, and refuses with an error, changing nothing, when they did. If it refuses, branch from the current commit instead
and tell the user the branch is behind the trunk.

**If the tree is clean**, start from the branch the work should build on:

- New, independent work: the trunk, as the remote has it. Find the trunk with `git symbolic-ref --short refs/remotes/origin/HEAD`
  (strip the `origin/`); if that fails, use whichever of `main`, `master`, or `develop` exists, and ask if more than one does and
  nothing says which is primary. Then fetch and branch from the remote-tracking ref:

  ```shell
  git fetch origin
  git switch --no-track -c <name> origin/<trunk>
  ```

  This starts from the latest trunk without touching the local trunk branch, so it cannot fail on a diverged local `main`.
  `--no-track` stops the new branch from treating the trunk as its upstream, which would point a later `git pull` and `git push` at
  the trunk.
- Work that continues the current branch, or a branch the user names: branch from that.
- `hotfix/`: from what is in production (usually the trunk, or a release branch or tag if the repository ships from those).
- No remote: branch from the local trunk, or from the current commit if the user is already on it.

If the user is on an unrelated branch, the tree is not clean, and the new work should start from the trunk, ask: carrying their
changes onto a different base is a decision for them.

### 6. Create, Verify, and Report

```shell
git switch -c <name> [<start-point>]       # Git older than 2.23: git checkout -b <name> [<start-point>]
git branch --show-current
git status --short
```

Confirm the current branch is the new name and that `git status` shows the same changes as before. Tell the user the branch name,
what it was created from, and whether uncommitted changes came along. Do not push; mention `git push -u origin <name>` for when they
are ready.

## Checking a Name

Run `scripts/check_branch.py` with the names to check, or with none to check the current branch. Pass the repository's extra types
and names (`--allow-type`, `--allow-name`) if its config defines any. Report each failure with its reason and a conforming
alternative, written by the rules in steps 2 and 3. Say when a name is valid for the repository but not for the specification (an
extra type), since that matters if the name leaves the repository. Offer to rename; do not do it unasked.

## Renaming a Branch

Never rename a trunk branch as part of this skill.

**Not pushed** (`git rev-parse --abbrev-ref <old>@{upstream}` fails and `origin/<old>` is absent from `git branch -r`): rename it.

```shell
git branch -m <old> <new>       # or, for the current branch: git branch -m <new>
```

**Pushed**: renaming only the local copy changes nothing others see, and the remote branch may be the head of an open pull request,
checked out by teammates, or referenced by CI. Explain this and get explicit confirmation before touching the remote. Then prefer
the hosting platform's rename, which keeps pull requests attached, for example on GitHub
`gh api -X POST repos/{owner}/{repo}/branches/<old>/rename -f new_name=<new>`, and update the local branch to match:

```shell
git branch -m <old> <new>
git fetch origin --prune
git branch -u origin/<new> <new>
```

Pushing a new branch and deleting the old one instead closes any pull request whose head was the old branch; do that only if the
user accepts it. Report the old and new names and whether the remote changed.

## Safety Rules

These protect the user's work and other people's view of the repository, so treat them as firm unless the user explicitly says
otherwise.

- **Keep uncommitted work.** Never `reset --hard`, `checkout -- .`, `clean`, `stash`, or switch away from changes to make a branch.
  `git switch -c` from the current commit is always safe.
- **No overwriting.** Never use `git switch -C`, `git checkout -B`, `git branch -f`, or `git branch -M`; they silently replace an
  existing branch.
- **No remote changes unasked.** Creating a branch does not imply pushing it. Do not push, delete, or rename remote branches, or
  open pull requests, unless asked.
- **Leave the trunk alone.** Do not commit to, reset, rename, or pull into the local trunk branch as a side effect of branching.
- **No configuration changes.** Do not change Git config, hooks, or validator settings to make a name pass. If a configured
  validator rejects the name, fix the name.

## Relationship with Commits

Branch types are deliberately fewer than commit types: a branch holds several commits and names their shared purpose. The usual
pairing, for writing commits on the branch (see the `commit` skill):

| Branch | Typical commits |
| :----- | :-------------- |
| `feature/oauth-login` | `feat(auth): add OAuth login`, plus `test`, `docs` |
| `bugfix/header-overflow` | `fix(ui): stop header overflowing on mobile` |
| `chore/update-dependencies` | `build(deps): bump express to 4.21.0` |
| `release/v1.2.0` | `chore(release): 1.2.0` |
