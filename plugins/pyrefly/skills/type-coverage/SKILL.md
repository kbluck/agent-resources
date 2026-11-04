---
name: type-coverage
description: >
  Migrate existing Python code to full type-annotation coverage under Pyrefly and lock it in: measure with pyrefly coverage,
  remove file-level suppressions, enable implicit-any and unannotated-return for the target in a sub-config, add precise
  annotations instead of Any or ignore comments, fix the type errors the new annotations expose, then format, test, and report
  coverage before and after. Use this skill whenever the user wants to add type hints or annotations to Python code in a project
  that uses Pyrefly (a pyrefly.toml or [tool.pyrefly] section), make a file "fully typed" or "strictly typed", raise or enforce
  type coverage, fix implicit-any or unannotated-return errors, or use pyrefly coverage or pyrefly infer, even if they only say
  "type this module". Not for fixing type errors in code as it is annotated today, a failing Pyrefly check, or ignore-comment
  cleanup (use the type-checking skill); first-time setup or migration from mypy or Pyright; tensor shapes; or projects checked only
  by mypy or Pyright.
compatibility: >
  Requires Pyrefly (written against 1.4), run the way the project runs it, or through uvx. Uses the project's own formatter,
  linter, and test runner.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/pyrefly/skills/type-coverage
  based-on: https://github.com/pytorch/pytorch/tree/main/.agents/skills/pyrefly-type-coverage
  version: 1.0.0
---

# Pyrefly Type Coverage

Take a target (a file, a module, or a package) to the point where every public and private function parameter, return type, class
attribute, and module variable is annotated with the most precise type that is true, Pyrefly reports it clean with the
annotation-completeness checks switched on, and the project's Pyrefly config keeps those checks on so coverage cannot quietly slip
back.

This skill adds annotations. Checking and fixing code as it is annotated today (a failing `pyrefly check`, a `bad-argument-type`
after an edit, cleaning up ignore comments) is the job of `type-checking`; see [Where This Skill Stops](#where-this-skill-stops) for
where the line falls.

The project's own Pyrefly config, Python version, naming conventions, and contributor guidance always win over the defaults here.

## Before You Start

**Find out how the project runs Pyrefly.** Look for `pyrefly` in the dev dependencies, lock file, `Makefile`, `noxfile.py`,
pre-commit config, or CI, and run it the same way (`uv run pyrefly`, `pixi run pyrefly`, `poetry run pyrefly`, or plain `pyrefly` in
the activated environment). The version matters: an upgrade alone can add or remove errors. If Pyrefly is not available, say so and
ask; do not install it into the project. `uvx pyrefly@<pinned-version>` runs it without touching the project and is a reasonable
offer. Commands below are written as bare `pyrefly`.

**Find the config that governs the target.** Pyrefly reads `pyrefly.toml`, or `[tool.pyrefly]` in `pyproject.toml`, searching upward
from the file. `pyrefly dump-config <file>` shows which one applies. If there is none, Pyrefly falls back to an in-memory migration
of any mypy or Pyright config, or else to the permissive `basic` preset. Setting Pyrefly up is a separate job (`pyrefly init`); stop
and ask before starting it.

From the config, note:

| Setting | Why it matters |
| :------ | :------------- |
| `python-version`, else `requires-python` | Decides which annotation syntax is allowed. Use the lowest version the project supports. |
| `preset` | `strict` already enables `implicit-any`, but no preset except `all` enables `unannotated-return`. `legacy` skips the bodies of unannotated functions, so annotating them exposes body errors that were always there. |
| `[errors]` | Root error settings. A sub-config inherits them. |
| Existing `[[sub-config]]` entries that match the target | The first matching entry wins. See step 3. |
| `permissive-ignores`, `enabled-ignores` | Which tools' suppression comments Pyrefly honors. Defaults: `# pyrefly:` and `# type:` only. |

Also find the project's formatter and linter, its test command, and the tests that cover the target.

**Size the work.** For a package, go one module at a time, starting with the modules that others import, so precise types flow
outward into their dependents. Make sure the working tree is clean or the user's changes are committed, so your diff is reviewable
on its own.

## Workflow

### 1. Measure the Starting Point

```shell
pyrefly coverage check <target> --fail-under 100   # lists coverage-missing and coverage-partial symbols
pyrefly coverage report <target> | jq .summary      # coverage and strict_coverage, plus counts
```

Coverage counts parameters, returns, module variables, and class attributes. An annotation that resolves to `Any` counts toward
`coverage` but not `strict_coverage`. Only public symbols count (no leading underscore, or listed in `__all__`), so private helpers
never show up here; `pyrefly check` in step 3 catches those. Keep the two numbers for the final report.

Also run a whole-project `pyrefly check` and keep the list of errors it reports. Without it, you cannot tell later whether an error
in another file is one your annotations caused or one that was already there.

### 2. Remove File-Level Suppressions

A file-level directive hides every error in the file, including the ones this work is meant to surface.

- Remove `# pyrefly: ignore-errors`, `# pyrefly: ignore-errors[<code>]`, and a file-level `# type: ignore` at the top of the file.
- `# mypy: ignore-errors`, `# pyre-ignore-all-errors`, and other tools' directives are ignored by Pyrefly unless
  `permissive-ignores` or `enabled-ignores` turns them on. If Pyrefly honors them here, remove them. If another checker that still
  runs in the project relies on one, leave it and tell the user, since removing it changes that checker's results too.
- Leave line-level ignores for now. Step 6 removes the ones that become unused.

A file-level directive anywhere below the first line of code is inert, and Pyrefly flags it as `misplaced-ignore`. Remove those too.

### 3. Enable the Annotation Checks for the Target

Preview the work list without editing any config:

```shell
pyrefly check <file> --error implicit-any --error unannotated-return --summarize-errors
```

Then make it permanent with a sub-config entry, so the target stays covered after you leave:

```toml
[[sub-config]]
matches = "src/pkg/module.py"     # a file, or "src/pkg/**" for a whole package
[sub-config.errors]
implicit-any = true
unannotated-return = true
```

In `pyproject.toml` the same entry is `[[tool.pyrefly.sub-config]]` with `[tool.pyrefly.sub-config.errors]`. `matches` is relative
to the config file.

- `implicit-any` is an umbrella. It enables every implicit-`Any` sub-kind: `implicit-any-parameter`, `implicit-any-attribute`,
  `implicit-any-empty-container`, `implicit-any-lambda`, and `implicit-any-type-argument`. `unannotated-return` is separate and has
  to be named. Do not add `unannotated-parameter` or `unannotated-attribute`: they are deprecated names for the `implicit-any-*`
  kinds.
- **The first matching sub-config wins.** When several entries match a file, Pyrefly uses the `errors` of the first one in file
  order and ignores the `errors` of every later match, even when the first entry sets no errors of its own. The root `[errors]`
  table is still merged underneath. So put the new entry *above* any broader entry that also matches the target, and copy that
  entry's error settings into yours. Otherwise either your entry is shadowed and nothing changes, or the broader entry's settings
  stop applying and unrelated errors flood in.
- If the target already sits under an entry that turns these checks on, there is nothing to add.
- If the user asked for annotations only, with no config changes, skip the entry and keep using the `--error` flags.

See [references/pyrefly-reference.md](references/pyrefly-reference.md) for presets, the full sub-config rules, suppression comments,
and every command flag used here.

Confirm the entry took effect: a plain `pyrefly check <file>`, with no flags, should now report the `unannotated-return` and
`implicit-any-*` errors from the preview. If it reports none while coverage says symbols are untyped, an earlier entry is shadowing
yours.

### 4. Optional: Let `pyrefly infer` Take a First Pass

```shell
pyrefly infer <file>
```

It writes annotations in place for some parameters, returns, and containers (`--parameter-types=false`, `--return-types=false`, and
`--containers=false` turn parts off). The feature is experimental and the Pyrefly docs recommend reviewing every change. Treat its
output as a draft:

- Parameter types inferred from call sites are often too narrow. A function that only iterates its argument wants `Iterable[int]`,
  not the `list[int]` one caller happened to pass.
- It skips many returns, so expect to finish by hand.
- Its output is not formatted (`scale: int=2`), so the formatter run in step 7 is required.

Skip it for small files or heavily dynamic code, where reviewing its guesses costs more than writing the annotations.

### 5. Add Annotations

Work out each type from the function body, its return paths, and its call sites. Use the language server's find-references (or
search) to read at least three call sites before deciding a parameter is "dynamic". Then annotate, using the strictest rung of this
ladder that is true:

1. The most specific concrete type the code supports.
2. A union, an abstract type (`Iterable[X]`, `Mapping[K, V]`, a `Protocol`), or a type variable when the output type follows an
   input type.
3. `object`, when anything is accepted and only used generically. Pyrefly makes callers narrow it before use.
4. `Any`, only when rungs 1 to 3 genuinely fail and you can say why (for example, the value is passed straight into an untyped
   library that dictates its shape).

Be most suspicious of a wide **return** type: a function nearly always knows more about what it produces than its callers do.

**Never suppress the target kinds.** `unannotated-return` and every `implicit-any-*` error can always be fixed by writing an
annotation; even `Any` is better than `# pyrefly: ignore` on one of them. The only exception is a signature the project freezes on
purpose, such as a test that snapshots `inspect.signature` or a public-API dump; there, adding an annotation breaks the test, so
suppress on the line Pyrefly reports (usually the `def` line) and say why.

The usual fix for each kind:

| Error kind | Typical cause | Fix |
| :--------- | :------------ | :-- |
| `unannotated-return` | `def f(x: int):` | Add `-> T`, including `-> None`. |
| `implicit-any-parameter` | `def f(x):` | Annotate the parameter. `self` and `cls` are exempt. |
| `implicit-any-attribute` | `self.cache = None` in a method | Declare it at class level: `cache: dict[str, int] \| None`. |
| `implicit-any-empty-container` | `items = []` with nothing to infer from | `items: list[str] = []`. |
| `implicit-any-type-argument` | bare `list`, `dict`, `tuple`, `Callable`, `type` | Parameterize: `list[int]`, `tuple[int, ...]`, `Callable[[int], str]`. |
| `implicit-any-lambda` | `key = lambda x: x.name` with no context | Give the lambda a typed context (`Callable[[User], str]`), or use a `def`. |

See [references/annotation-guide.md](references/annotation-guide.md) for syntax by Python version, imports, type variables and
`ParamSpec`, `TypeGuard` and `TypeIs`, `Self`, `TYPE_CHECKING` imports, and the runtime traps below in detail.

**Annotations are not always inert at runtime.** Check before annotating in these cases:

- In a `@dataclass`, attrs class, `NamedTuple`, `TypedDict`, Pydantic model, or ORM model, a class-level annotation creates a field.
  Annotating a plain class attribute there changes the constructor. Use `ClassVar[...]` for true class-level values.
- Pydantic, FastAPI, Typer, `functools.singledispatch`, and anything calling `typing.get_type_hints` evaluate annotations at
  runtime. Types imported only under `if TYPE_CHECKING:` break them.

### 6. Handle the Other Errors That Surface

New annotations make Pyrefly check code it previously treated as `Any`, so expect `bad-return`, `bad-argument-type`,
`missing-attribute`, and similar errors. These are real findings. Handle each by where it comes from (the `type-checking` skill
covers fixing these error kinds in more depth):

| Where it is reported | What to do |
| :------------------- | :--------- |
| In the target, caused by code in the target | Fix it, or fix your annotation if the annotation is what is wrong. |
| In the target, caused by a wrong annotation or stub elsewhere (an imported function's return type, a third-party stub gap) | Suppress narrowly on that line with the code and a reason. Do not paper over it with `cast()`. |
| In another file, and it was already there | Leave it and mention it in the report. It belongs to `type-checking`, not this migration. |
| In another file, newly caused by your annotations | Your annotation is too narrow or wrong, or the caller has a real bug. Fix the annotation if it is wrong; otherwise report the caller to the user rather than leaving the project's check red. |

An `assert x is not None` added only to quiet the checker is not a fix. It changes the exception raised, and `python -O` strips it.
Write the handling the code actually means (raise a clear error, return early, or restructure so the value cannot be `None`), and if
that changes behavior, say so in the report.

A narrow suppression names its error code and goes on the reported line or the line above it:

```python
# pyrefly: ignore[missing-attribute]  # plugin registry adds attributes at import time
handler = registry.lookup(name)
```

Use the line-above form when a trailing comment would exceed the line length; Pyrefly honors both. Never write a bare
`# pyrefly: ignore` without a code. If the project has a convention for suppression comments (a `TODO` tag, an issue link), follow
it.

Re-run `pyrefly check <file>` after each round. Tightening a helper often turns existing ignores into dead ones, so finish with:

```shell
pyrefly suppress --remove-unused <file>   # deletes unused pyrefly ignores; keeps "# type: ignore", which other tools may use
```

Delete any explanatory comment left behind by a removed suppression.

### 7. Format, Lint, and Test

Run the project's formatter and linter on every file you changed, and leave those files passing both, including problems on lines
you did not touch. A changed file that fails the project's own checks is not finished, and "annotations only" does not exempt it:
formatting is part of a clean change, not scope creep. If the linter reports something only a real code change could fix, tell the
user instead of fixing it. Added imports and longer signatures often break import order and line length, and a formatter can move an
inline ignore off the line it suppresses, so run `pyrefly check` once more afterwards.

Then run the tests that cover the target. Find them by name and by import (`grep -rl "import pkg.module\|from pkg.module import"` in
the test tree). If none exist, tell the user rather than skipping silently: annotation work can change behavior (the runtime traps
in step 5, a narrowed `isinstance` branch, an `X | None` that was really `X`).

When something fails, this order decides: **tests passing, then Pyrefly clean, then annotation strictness.** If an annotation breaks
a test, loosen it one rung on the ladder before you consider reverting the file.

### 8. Verify and Report

```shell
pyrefly check <file>                                  # no flags: the config is what enforces it
pyrefly coverage check <target> --fail-under 100      # coverage of the public symbols
pyrefly check                                         # whole project: compare with the list from step 1
```

Report to the user:

- Coverage and strict coverage, before and after.
- The config entry you added, and any existing entry you reordered or copied settings from.
- Each `Any` that remains and why, and each suppression you added and why.
- Errors you found in other files and left alone, and anything that needs a decision.

Do not commit unless the user asked you to. Leave the diff for review.

## Where This Skill Stops

`type-checking` and this skill split Pyrefly work by what the code needs: fixing what Pyrefly reports about the annotations the code
has, or adding the annotations it lacks.

| `type-checking` | This skill |
| :-------------- | :--------- |
| Errors in code as it is annotated today | Adding annotations until the target is fully typed |
| `bad-*`, `missing-*`, `unbound-name`, import and environment errors | `implicit-any-*`, `unannotated-return`, `pyrefly coverage`, `pyrefly infer` |
| Leaves the config alone | Adds a sub-config to lock coverage in |
| Removes stale or overly broad ignore comments anywhere | Removes file-level suppressions from the target, and ignores the new annotations make unused |

The errors that new annotations expose in the target (step 6) are part of this job: finding them is the point of annotating, and the
work is not finished while they stand. Errors elsewhere in the project that predate the work are not; report them, and fix them with
`type-checking` only if the user asks.

Hand over to `type-checking` when the request turns out to be about existing errors rather than missing annotations: the user wants
a red Pyrefly check fixed, or the target already has full coverage and still reports `bad-*` errors.

## Rules of Thumb

- Fix with annotations, not suppressions. A target-kind ignore is never the answer outside a frozen signature.
- Precise beats wide, and `object` beats `Any`. Wide returns need the strongest justification.
- The first matching `[[sub-config]]` wins. Put specific entries above broad ones.
- Use current error-kind names: `implicit-any-parameter`, not `unannotated-parameter`; `bad-override-param-name`, not
  `bad-param-name-override`.
- Do not widen scope: no renames, refactors, or fixes to unrelated pre-existing errors in other files. Formatting and lint fixes in
  the files you changed are in scope.
- Respect the project's Python floor and conventions over this skill's defaults.
