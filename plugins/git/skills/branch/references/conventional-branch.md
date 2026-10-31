# Conventional Branch 1.1.0 Reference

Sources: the specification at <https://conventionalbranch.org/> (machine-readable form:
<https://conventionalbranch.org/v1.1.0/spec.json>), its enforcement guide at <https://conventionalbranch.org/enforce/>, and the
project's agent skill at <https://github.com/conventional-branch/conventional-branch/blob/main/skills/conventional-branch/SKILL.md>,
all licensed CC BY 4.0 by the Conventional Branch authors. Summarized and adapted here.

## Contents

- [Specification rules](#specification-rules)
- [Grammar](#grammar)
- [Validating without Python](#validating-without-python)
- [Conformance cases](#conformance-cases)
- [Team extensions](#team-extensions)
- [Bots and automation](#bots-and-automation)
- [Enforcement tools](#enforcement-tools)
- [Background](#background)

## Specification Rules

1. A branch name is either a trunk branch (`main`, `master`, `develop`) with no prefix, or `<type>/<description>`.
2. The type is one of a fixed set. Purpose types: `feature` (alias `feat`), `bugfix` (alias `fix`), `hotfix`, `release`, `chore`. AI
   agent source types: `ai`, `claude`, `codex`, `copilot`, `cursor`. Any other type, such as `docs/` or `unknown/`, is invalid under
   the specification itself.
3. The description uses lowercase `a-z`, digits `0-9`, hyphens to separate words, and dots (typically for version numbers, and
   allowed in any description: `chore/upgrade-node-v20.11`).
4. Hyphens and dots may not repeat (`--`, `..`), sit next to each other (`-.`, `.-`), or begin or end the description.
5. The description may not be empty and may not contain `/`.
6. A single-character or digits-only description is valid (`feature/a`, `chore/123`), though rarely a good name.
7. Ticket numbers may be included in the description (`feature/issue-123-new-login`).
8. All 1.0.0 names remain valid in 1.1.0, which added only the AI agent source types.

## Grammar

ABNF:

```abnf
branch-name     = trunk-branch / prefixed-branch
trunk-branch    = "main" / "master" / "develop"
prefixed-branch = type "/" description
type            = "feature" / "feat" / "bugfix" / "fix"
                / "hotfix" / "release" / "chore"
                / "ai" / "copilot" / "cursor"
                / "claude" / "codex"
description     = desc-segment *("-" desc-segment)
desc-segment    = 1*(ALPHA / DIGIT) *("." 1*(ALPHA / DIGIT))
ALPHA           = %x61-7A   ; lowercase a-z
DIGIT           = %x30-39   ; 0-9
```

The regular expression in `spec.json` is the authoritative validator. It uses no backreferences or lookaround, so it works unchanged
in Python, JavaScript, Go (RE2), PCRE, GitHub rulesets, and GitLab push rules:

```regex
^(?:main|master|develop|(?:feature|feat|bugfix|fix|hotfix|release|chore|ai|copilot|cursor|claude|codex)/[a-z0-9]+(?:\.[a-z0-9]+)*(?:-[a-z0-9]+(?:\.[a-z0-9]+)*)*)$
```

## Validating Without Python

POSIX `grep -E` does not accept `(?:`, and `grep -P` is a GNU extension missing on macOS. This equivalent form, with plain groups,
works with `grep -E` everywhere:

```shell
pattern='^(main|master|develop|(feature|feat|bugfix|fix|hotfix|release|chore|ai|copilot|cursor|claude|codex)/[a-z0-9]+(\.[a-z0-9]+)*(-[a-z0-9]+(\.[a-z0-9]+)*)*)$'
printf '%s' "$name" | grep -qE "$pattern" && echo ok || echo invalid
```

In PowerShell, `-cmatch` (case-sensitive) accepts the authoritative expression as is: `$name -cmatch '<expression>'`. Plain `-match`
ignores case and would accept `Feature/Login`.

To accept a repository's extra types, add them to the type alternation.

## Conformance Cases

From the specification's `tests/fixtures.json`. `scripts/test_check_branch.py` runs all of them against `scripts/check_branch.py`.

| Branch | Valid | Why |
| :----- | :---- | :-- |
| `main`, `master`, `develop` | yes | Trunk branches |
| `feature/add-login-page` | yes | New feature |
| `feat/add-login-page` | yes | Alias for `feature` |
| `fix/header-bug` | yes | Alias for `bugfix` |
| `hotfix/security-patch` | yes | Urgent fix |
| `release/v1.2.0` | yes | Dotted version |
| `chore/upgrade-node-v20.11` | yes | Dots allowed in any description |
| `feature/issue-123-new-login` | yes | Ticket number |
| `chore/123`, `feature/a` | yes | Digits-only and single-character descriptions |
| `ai/refactor-auth-flow` | yes | Vendor-neutral agent prefix |
| `claude/security-patch` | yes | Claude Code agent prefix |
| `Feature/Add-Login` | no | Uppercase |
| `Main` | no | Trunk names are lowercase too |
| `feature/new--login` | no | Consecutive hyphens |
| `feature/new..login` | no | Consecutive dots |
| `feature/-new-login` | no | Leading hyphen |
| `feature/new-login-` | no | Trailing hyphen |
| `feature/.new`, `feature/new.` | no | Leading or trailing dot |
| `release/v1.-2.0` | no | Hyphen next to a dot |
| `fix/header bug` | no | Space |
| `fix/header_bug` | no | Underscore |
| `unknown/some-task` | no | Unknown type |
| `feature` | no | Type without description |
| `feature/` | no | Empty description |
| `/add-login` | no | Missing type |
| `feature/a/b` | no | Slash in description |

Git's own rules are looser than the specification in every respect but one: Git rejects a path component ending in `.lock`, so
`chore/remove-yarn.lock` conforms to the grammar but cannot be created. Write `chore/remove-yarn-lockfile`.

## Team Extensions

The specification keeps its type list short on purpose: a branch is temporary and usually holds several kinds of commit, so its name
states the purpose of the work, not a classification of each change. Teams may add types (for example `docs/`, `refactor/`,
`experiment/`) or treat other long-lived branches (`staging`, `production`) as trunk-like. Such names are valid for that team, not
under the specification, so the extension should be written down where both people and validators read it.

The usual place is commit-check's configuration, `cchk.toml` (or `commit-check.toml`) at the repository root or in `.github/`:

```toml
[branch]
conventional_branch = true
require_description_grammar = true
allow_branch_types = [
  "feature", "feat", "bugfix", "fix", "hotfix", "release", "chore",
  "ai", "claude", "codex", "copilot", "cursor",
  "docs",                                   # team extension
]
allow_branch_names = ["main", "master", "develop", "staging"]
ignore_authors = ["dependabot[bot]", "renovate[bot]", "github-actions[bot]"]
```

Without this file, commit-check's default type list is a superset of the specification's: it also accepts the Conventional Commits
types (`docs/`, `refactor/`, ...), `dependabot/`, `renovate/`, and `agents/`. Without `require_description_grammar = true`
(commit-check 2.19 and later), it checks only the type prefix, not the description.

## Bots and Automation

Dependency and release bots name their own branches, and most names do not conform (`dependabot/npm_and_yarn/lodash-4.17.21`,
`renovate/lodash-4.x`, `release-please--branches--main`). Either exclude them from enforcement (GitHub ruleset `exclude` patterns,
commit-check `ignore_authors`) or configure the bot: Renovate accepts `"branchPrefix": "chore/"` with `"branchNameStrict": true`;
Dependabot and release-please cannot reliably be made to conform. These branches are not this skill's to create or rename.

## Enforcement Tools

- "commit-check" (`commit-check --branch`, or the `check-branch` pre-commit hook): local check at every commit; configured as above.
- "commit-check-action": the same check in GitHub Actions, reported on the pull request.
- "GitHub rulesets" (`branch_name_pattern` with the expression above), "GitLab push rules" (Premium or Ultimate), "Bitbucket Data
  Center pre-receive hooks": server-side, cannot be bypassed.
- "`pre-push` hook" using the `grep -E` form above: no dependencies; share it with `git config core.hooksPath .githooks`.

If the repository has any of these, a name that fails them will be rejected; fix the name rather than the configuration.

## Background

- The prefixes come from git-flow (around 2010) and tools like Bitbucket's branching model. Conventional Branch adds a precise,
  shared definition: fixed types, a grammar, a published regex, and conformance cases.
- Lowercase matters beyond style: Git stores branch refs as files, and macOS and Windows file systems are usually case-insensitive,
  so `Feature/login` and `feature/login` collide there but are distinct on Linux.
- Agent source prefixes exist so reviewers and tools can recognize agent-opened pull requests. They are optional; a purpose prefix
  is equally valid for an agent's branch.
