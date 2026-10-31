# Commit message examples

## Contents

- [By type](#by-type)
- [Breaking changes](#breaking-changes)
- [Footers](#footers)
- [Body: signpost, not story](#body-signpost-not-story)
- [Grouping changes into commits](#grouping-changes-into-commits)
- [Anti-patterns](#anti-patterns)

## By type

Subject-only commits are fine for types other than `feat` and `fix` when the subject says everything:

```text
docs: correct spelling of CHANGELOG
style: apply prettier to src/components
ci: add Node 22 to test matrix
build(deps): bump express from 4.19.2 to 4.21.0
test(parser): cover nested array input
chore: ignore JetBrains workspace files
```

`feat`: why the capability is wanted, and the one fact a reader needs.

```text
feat(payments): add Apple Pay to checkout

Mobile users abandon checkout at the card form more than at any other
step. Apple Pay skips that form on supported devices; other platforms
see no change.

Refs: #88
```

`fix`: the symptom and its cause, briefly.

```text
fix(api): include last item on each results page

The pagination offset compared with `>` instead of `>=`, so every page
silently dropped its final record.

Closes: #201
```

`refactor`: why restructure, and that behavior is unchanged.

```text
refactor(users): extract email validation into shared helper

The same validation was copied into four modules and had started to
drift. All four now call one helper. No behavior change.
```

If any module's behavior did change, this is a `fix`, not a `refactor`.

`perf`: the cost removed, with a number if you have one.

```text
perf(dashboard): lazy-load chart components

Importing every chart type up front added about 180 KB to the initial
bundle. Charts now load on first render.
```

`build`: the non-obvious part only.

```text
build: migrate eslint config to flat format

ESLint 9 drops support for .eslintrc. Rules are unchanged.
```

`revert`: name the reverted change by its subject and say why. Git's default `This reverts commit <hash>.` line may stay as a convenience, but the message must make sense if that hash later disappears.

```text
revert: feat(notifications): add push opt-in

The opt-in dialog crashes on Android 12. Reverting until the
permission flow is fixed.

Refs: #412
```

## Breaking changes

`!` plus a migration footer (preferred):

```text
feat(api)!: remove v1 REST endpoints

The v1 endpoints were deprecated in 3.2 with six months' notice.

BREAKING CHANGE: /api/v1/* now returns 410 Gone. Migrate clients to
 /api/v2; see docs/v2-migration.md for the field mapping.
```

Wrapped footer values continue on lines indented by one space, which Git and Conventional Commits parsers both join into one value.

Breaking change on a non-`feat` type:

```text
build!: require Node 20 or later

Node 18 is end-of-life and no longer tested.

BREAKING CHANGE: package fails to start on Node 18.
```

With other trailers present, use the hyphenated token so Git still parses them:

```text
fix(config)!: let environment variables override config file

Operators expect the environment to win, as it does in every other
service we ship.

BREAKING-CHANGE: deployments that set a value in both places now get
 the environment value.
Refs: #77
```

## Footers

Several footers, each in `Token: value` form:

```text
fix: prevent racing of requests

Responses could arrive out of order and overwrite newer results. Only
the response to the latest request is applied now, which also makes
the old mitigation timeouts unnecessary.

Reviewed-by: Z
Refs: #123
```

Co-authors (only when requested or configured):

```text
feat(export): add CSV export for reports

Finance needs report data in spreadsheets without copy and paste.

Co-authored-by: Ada Example <ada@example.com>
```

## Body: signpost, not story

Too much. This narrates the journey, inventories the diff, and duplicates what belongs in code comments:

```text
fix(cache): fix stale entries after config reload

While investigating reports of stale data I first suspected the TTL
logic, so I added logging around expiry, but that turned out to be
fine. Then I noticed that reload() creates a new Config object but
the cache still holds a reference to the old one. I tried passing the
config into get() but that touched 40 call sites, so instead I made
the cache subscribe to the reload event. Changes:
- cache.py: add on_reload handler, clear entries, rebind config
- config.py: emit reload event
- test_cache.py: add test
Note that the handler must run before listeners registered later,
because ...
```

Right-sized. The reason and the effect; ordering detail goes in a code comment next to the handler:

```text
fix(cache): drop stale entries on config reload

The cache kept a reference to the config it was created with, so
values computed under the old config survived a reload. The cache now
clears itself and rebinds when the config reloads.
```

## Grouping changes into commits

Working tree: a new `--json` flag in `cli.py`, a crash fix for empty input in `parser.py` with its test, an unrelated typo fixed in `README.md`, and a local `.env`.

```text
fix(parser): handle empty input without crashing
feat(cli): add --json output flag
docs: fix typo in usage section
```

`.env` stays unstaged, and the user is told. But if the README edit documents the new `--json` flag (and fixes a typo in the line it touches), it belongs in the `feat(cli)` commit, not a separate `docs` commit: it was prompted by that change.

Over-granular history from iterating on one concern:

```text
feat(search): add fuzzy matching
fix(search): handle empty query in fuzzy matching
fix(search): fix off-by-one in fuzzy scoring
test(search): fix flaky fuzzy test
style(search): reformat
```

If none of this has been pushed, it is one commit: `feat(search): add fuzzy matching`, describing the final result. The fixes are corrections to unreleased work, not changes anyone downstream needs to see.

## Anti-patterns

| Instead of                           | Write                                                         | Why                                         |
| ------------------------------------ | ------------------------------------------------------------- | ------------------------------------------- |
| `fix bug`                            | `fix(cart): prevent duplicate items on rapid add-to-cart`     | Say which bug and what effect               |
| `update auth.ts`                     | `fix(auth): reject expired refresh tokens`                    | File names are in the diff already          |
| `feat: Added a user search.`         | `feat: add user search`                                       | Imperative, no articles, lowercase, no period |
| `misc changes` / `various fixes`     | One commit per concern                                        | Each concern deserves its own entry         |
| `fix: address review comments`       | Fold into the commit being reviewed                           | Review rounds are journey, not history      |
| `chore: update stuff`                | The real type (`build`, `docs`, `test`, ...) and subject      | `chore` is not a catch-all                  |
| `refactor: fix login redirect`       | `fix(auth): redirect to original page after login`            | Behavior changed, so it is a fix            |
| `feat(api): remove v1` (no marker)   | `feat(api)!: remove v1 endpoints` + breaking-change footer    | Unmarked breaks ship as minor releases      |
| `WIP`                                | Finish the change, or stash it                                | WIP commits break bisect and changelogs     |
| Body: "Changed X to Y in file Z"     | Body: why X was wrong                                         | The diff shows what; the body shows why     |
| Body: "First I tried A, then B..."   | Body: the final change and its reason                         | History records results, not the search     |
| Body: "Follow-up to a1b2c3d"         | Body: "Follow-up to the empty-input fix" or `Refs: #123`      | Hashes vanish after rebases and squashes    |
