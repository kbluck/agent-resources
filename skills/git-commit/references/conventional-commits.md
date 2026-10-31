# Conventional Commits 1.0.0 reference

Source: <https://www.conventionalcommits.org/en/v1.0.0/#specification>. Key words are as defined in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

## Contents

- [Specification rules](#specification-rules)
- [What the rules mean in practice](#what-the-rules-mean-in-practice)
- [Semantic versioning](#semantic-versioning)
- [Edge cases](#edge-cases)
- [Tooling](#tooling)

## Specification rules

1. Commits MUST be prefixed with a type, which consists of a noun, `feat`, `fix`, etc., followed by the OPTIONAL scope, OPTIONAL `!`, and REQUIRED terminal colon and space.
2. The type `feat` MUST be used when a commit adds a new feature to your application or library.
3. The type `fix` MUST be used when a commit represents a bug fix for your application.
4. A scope MAY be provided after a type. A scope MUST consist of a noun describing a section of the codebase surrounded by parenthesis, e.g., `fix(parser):`
5. A description MUST immediately follow the colon and space after the type/scope prefix. The description is a short summary of the code changes.
6. A longer commit body MAY be provided after the short description, providing additional contextual information about the code changes. The body MUST begin one blank line after the description.
7. A commit body is free-form and MAY consist of any number of newline separated paragraphs.
8. One or more footers MAY be provided one blank line after the body. Each footer MUST consist of a word token, followed by either a `:<space>` or `<space>#` separator, followed by a string value (inspired by the [git trailer convention](https://git-scm.com/docs/git-interpret-trailers)).
9. A footer's token MUST use `-` in place of whitespace characters, e.g., `Acked-by`. An exception is made for `BREAKING CHANGE`, which MAY also be used as a token.
10. A footer's value MAY contain spaces and newlines, and parsing MUST terminate when the next valid footer token/separator pair is observed.
11. Breaking changes MUST be indicated in the type/scope prefix of a commit, or as an entry in the footer.
12. If included as a footer, a breaking change MUST consist of the uppercase text `BREAKING CHANGE`, followed by a colon, space, and description.
13. If included in the type/scope prefix, breaking changes MUST be indicated by a `!` immediately before the `:`. If `!` is used, `BREAKING CHANGE:` MAY be omitted from the footer section, and the commit description SHALL be used to describe the breaking change.
14. Types other than `feat` and `fix` MAY be used in your commit messages, e.g., `docs: update ref docs`.
15. The units of information that make up Conventional Commits MUST NOT be treated as case-sensitive by implementors, with the exception of `BREAKING CHANGE` which MUST be uppercase.
16. `BREAKING-CHANGE` MUST be synonymous with `BREAKING CHANGE`, when used as a token in a footer.

## What the rules mean in practice

- The header grammar is `type(scope)!: description`. No space before the colon, exactly one space after it, the `!` goes after the scope.
- The spec itself does not limit header length, mandate lowercase, or forbid a trailing period. Those come from the Angular convention and `@commitlint/config-conventional` (header max 100 by default; most teams use 72). Follow the repository's lint config when one exists.
- Types are case-insensitive to parsers, but use lowercase for consistency; `FEAT:` and `Feat:` look like mistakes and some linters reject them.
- Everything after the first blank line and before the footers is body. A paragraph whose first line looks like `Word: value` or `Word #value` will be parsed as a footer, so do not start body paragraphs that way.
- If `!` is present, the description must itself describe what breaks. A footer can then add migration detail.
- Footers follow Git's trailer format closely but not exactly. Git rejects tokens containing a space and `Token #value` separators, so a footer paragraph containing `BREAKING CHANGE:` or `Closes #12` is not parsed as trailers by `git interpret-trailers`, which also hides any `Refs:` or `Co-authored-by:` lines in it. `BREAKING-CHANGE:` and `Closes: #12` are valid in both systems.

## Semantic versioning

| Commits since last release include                 | Version bump    |
| -------------------------------------------------- | --------------- |
| any commit with `!` or a `BREAKING CHANGE` footer  | MAJOR (`X.0.0`) |
| otherwise, any `feat`                              | MINOR (`0.X.0`) |
| otherwise, any `fix`                               | PATCH (`0.0.X`) |
| only other types                                   | none by default |

Release tools (semantic-release, release-please, git-cliff, commitizen, changesets with conventional presets) can be configured to treat other types differently, for example bumping patch on `perf`. Check the repository's release config if the exact effect matters.

During initial development (`0.y.z`), many tools treat breaking changes as minor bumps. Still mark them; the history is accurate and the bump policy can change.

## Edge cases

**Reverts.** The spec does not define reverts. Name the reverted change by its header, which survives rebases and squashes, and say why it was reverted:

```text
revert: feat(notifications): add push opt-in

The opt-in dialog crashes on Android 12. Reverting until the
permission flow is fixed.

Refs: #412
```

`git revert` adds `This reverts commit <hash>.` to its default message. Keeping that line is harmless as a convenience, but the message must stand on its own if the hash later stops resolving. To write your own message non-interactively, run `git revert --no-commit <hash>` and then commit with `-F`. Some repositories keep Git's default `Revert "..."` header; follow history.

**Merge commits.** Git's default `Merge branch 'x'` messages are normally exempt, and most changelog tools skip merges. With squash merges, the squash commit's message is what lands on the main branch, so it should be a proper Conventional Commit describing the whole change.

**A commit that is several types.** Prefer splitting it. If it truly cannot be split, use the type with the greatest release significance (`feat` over `fix` over everything else) and mention the rest in the body.

**Wrong type used.** Before it is pushed or merged, the commit can be reworded (with the user's approval, since that rewrites history). After release, leave it; a mistyped commit is simply missed or misclassified by tools, which is not dangerous. Do not rewrite shared history to fix a type.

**Dependency updates.** `build(deps): bump lodash from 4.17.20 to 4.17.21`. Use `fix(deps):` only if the bump is made specifically to fix a user-facing bug or a security issue the project is affected by, since that is a change users care about. Development-only dependencies are often `build(deps-dev):` or `chore(deps-dev):` per repo style.

**Security fixes.** `fix:` with a clear but non-exploitable description; put advisory identifiers in a footer (`Refs: CVE-2026-12345`, `Refs: GHSA-xxxx-xxxx-xxxx`).

**Work in progress.** Do not commit WIP to a shared branch. On a private branch that will be squashed, `wip:` style commits are tolerable if the repository allows them; the squash message is what matters.

## Tooling

You may see these in a repository; their configs define the allowed types, scopes, and limits.

- **commitlint** (`commitlint.config.*`, `.commitlintrc*`): lints messages, usually from a `commit-msg` hook (husky, lefthook, pre-commit). Validate a message without committing: `echo "feat(api): add endpoint" | npx commitlint`.
- **commitizen** (`.czrc`, `[tool.commitizen]`): interactive prompts; do not run its interactive mode. `cz check --message "<msg>"` validates.
- **semantic-release**, **release-please**, **git-cliff**: read commit history to compute versions and changelogs. A wrong type here changes a release, which is why type accuracy matters.
