# Branch Name Examples

## Contents

- [From request to name](#from-request-to-name)
- [Choosing the type](#choosing-the-type)
- [Starting points](#starting-points)
- [Anti-patterns](#anti-patterns)

## From Request to Name

| The user says | Branch |
| :------------ | :----- |
| "Start a branch for adding Google sign-in" | `feature/google-sign-in` |
| "New branch for JIRA PROJ-482, avatars crash when the URL is null" | `bugfix/proj-482-null-avatar-crash` |
| "Checkout prod is down, card payments failing, need a branch now" | `hotfix/card-payment-failures` |
| "Cut the 2.4.0 release branch" | `release/v2.4.0` |
| "Branch to bump all our npm deps" | `chore/update-npm-dependencies` |
| "I want to try splitting the parser into its own module" | `feature/extract-parser-module` |
| "Make a branch for issue #57: Export to CSV" | `feature/issue-57-csv-export` |
| "Branch for upgrading to Node 22.11" | `chore/upgrade-node-v22.11` |
| "Create a claude/ branch for the login redirect bug" | `claude/fix-login-redirect` |

Notes:

- The ticket key is lowercased and leads the description; the rest still names the work.
- `hotfix/` because production is broken now. "Fix the typo in the footer" is `bugfix/`, however quick.
- A refactor is `feature/` under the specification. If the repository allows `refactor/`, use that.
- With an agent prefix, the description still names the work. Nothing in the name says "bug", so pick words that do:
  `claude/fix-login-redirect` is fine here, since `claude/` carries no purpose.

## Choosing the Type

| Work | Type | Why |
| :--- | :--- | :-- |
| New endpoint, screen, CLI flag, option | `feature/` | New capability |
| Making something faster, refactoring internals | `feature/` | Enhancement to the code; no `perf/` or `refactor/` in the spec |
| Wrong result, crash, regression found in testing | `bugfix/` | Supposed to work and did not |
| Outage or security hole in production | `hotfix/` | Urgent, outside the normal release flow |
| Version bump, changelog, release candidate fixes | `release/` | Preparing a specific release |
| Dependency bumps, CI config, docs, linters, tests only | `chore/` | No change to what the product does |
| Feature plus its tests and docs | `feature/` | Name the purpose of the branch, not every commit |

## Starting Points

Uncommitted work on `main`, user says "put this on a branch":

```shell
git switch -c bugfix/empty-cart-total     # changes come along; main is untouched
```

Clean tree, new independent work:

```shell
git fetch origin
git switch --no-track -c feature/csv-export origin/main
```

Clean tree, user is on `feature/csv-export` and wants a follow-up that builds on it:

```shell
git switch -c feature/csv-export-scheduling
```

A local branch literally named `feature` exists, user asks for a feature branch for dark mode. `feature/dark-mode` cannot be
created, so use the alias and say why:

```shell
git show-ref --verify --quiet refs/heads/feature && echo blocked
git switch -c feat/dark-mode
```

The same applies to a branch named `bugfix` (use `fix/`), `feat` (use `feature/`), or `fix` (use `bugfix/`).

## Anti-Patterns

| Instead of | Write | Why |
| :--------- | :---- | :-- |
| `Feature/Add-Login` | `feature/add-login` | Lowercase only; mixed case collides on macOS and Windows |
| `feature/add_login` | `feature/add-login` | Hyphens separate words |
| `feature/PROJ-123/login` | `feature/proj-123-login` | One slash only; lowercase the key |
| `bugfix/fix-header-bug` | `bugfix/header-overflow` | The type already says it is a fix; name the problem |
| `feature/new-feature` | `feature/csv-export` | Says nothing a branch list does not already say |
| `jdoe/stuff`, `feature/jd-login` | `feature/oauth-login` | Git records the author; the name is for the work |
| `feature/login-2026-10-30` | `feature/oauth-login` | Git records the date |
| `wip/login`, `feature/login-wip` | `feature/oauth-login` | Every branch is work in progress |
| `docs/update-readme` (no config) | `chore/update-readme` | `docs/` is not a spec type unless the repo adds it |
| `release/v1.2.0.` | `release/v1.2.0` | No trailing dot |
| `chore/remove-yarn.lock` | `chore/remove-yarn-lockfile` | Git rejects names ending in `.lock` |
| `claude/...` by default | `feature/...` | Agent prefixes only when asked or already the repo's convention |
| `git checkout main && git pull && git checkout -b ...` with uncommitted work | `git switch -c ...` | Switching and pulling can conflict with or tangle the user's changes |
