---
name: type-checking
description: >
  Type-check existing Python code with the Pyrefly CLI and fix what it finds: confirm the config and preset in force, separate
  environment problems (missing-import, untyped-import) from real type errors, fix each error where the bug is, suppress only
  narrowly with a reason, and verify a clean check with tests passing. Use this skill whenever the user asks to run Pyrefly or
  type-check Python, fix Pyrefly errors or a failing Pyrefly CI step, understand an error such as bad-argument-type, bad-return,
  missing-attribute, or unbound-name, clean up "# pyrefly: ignore" comments, or handle new errors after an upgrade. Also use it
  before finishing any task that changed Python in a project with a pyrefly configuration, even if types never came up. Not for
  adding annotations toward full coverage, implicit-any or unannotated-return errors, or pyrefly coverage and inference (use the
  type-coverage skill); first-time setup or migration from mypy or Pyright; tensor shapes; or projects checked only by mypy or
  Pyright.
compatibility: >
  Requires Pyrefly (written against 1.4), run the way the project runs it, or through uvx. Uses the project's own formatter, linter,
  and test runner.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/pyrefly/skills/type-checking
  based-on: https://pyrefly.org/blog/pyrefly-agentic-loop/
  version: 1.0.1
---

# Pyrefly Type Checking

Run Pyrefly over existing code, decide what each error really means, fix the code (or the annotation that is lying), and leave the
project checking clean under its own configuration. Type checking is fast and its errors are concrete, which makes it one of the
cheapest ways to catch a broken call, a wrong return, or a missing attribute before a test or a user does.

This skill works with the annotations the code already has. Adding annotations for coverage is the job of `type-coverage`; see
[When the Code Is Mostly Unannotated](#when-the-code-is-mostly-unannotated) for where the line falls.

The project's own Pyrefly config, Python version, and contributor guidance always win over the defaults here.

## Before You Start

**Run Pyrefly the way the project does.** Look for `pyrefly` in the dev dependencies, lock file, `Makefile`, `noxfile.py`,
pre-commit config, or CI, and use the same invocation (`uv run pyrefly`, `poetry run pyrefly`, `pixi run pyrefly`, or `pyrefly` in
the activated environment). The version matters: an upgrade alone can add or remove errors. If Pyrefly is not available, say so and
ask; do not add it to the project. `uvx pyrefly@<version>` runs it without touching the project and is a reasonable offer. Commands
below are written as bare `pyrefly`.

**Make sure Pyrefly sees the project's environment.** Pyrefly resolves third-party imports from the site-packages of the interpreter
it finds: an active venv or conda env, else a `.venv`, `venv`, or `env` directory near the project, else `python3` on the `PATH`.
Run through `uvx` with no project venv, and it finds uv's own throwaway interpreter, so every third-party import becomes
`missing-import`. If import errors flood in, check the interpreter before touching any code.

**Find out which config governs the code, and how strict it is.**

```shell
pyrefly dump-config <file>   # which config file, which interpreter, which search and site-packages paths
```

Then read that config file for `preset`, `[errors]`, `[[sub-config]]`, `baseline`, and `min-severity`.

| What you find | What it means for this run |
| :------------ | :------------------------- |
| `pyrefly.toml`, or `[tool.pyrefly]` in `pyproject.toml` | Normal case. Use it as is. |
| No Pyrefly config, but mypy or Pyright config nearby | Pyrefly migrates that config in memory. Results approximate what `pyrefly init` would write. |
| No config at all | Pyrefly uses the `basic` preset: syntax errors, missing imports, and a few other high-confidence checks only. It skips unannotated function bodies. **A clean run here proves very little.** |
| `preset = "legacy"` or `check-unannotated-defs = false` | Bodies of fully unannotated functions are not checked at all. |
| `baseline = "..."` | Errors recorded in the baseline are hidden from the CLI. Only new errors are reported. |
| `min-severity` | Lowers the bar for what prints and what fails the run. |

With no config, say so plainly: the clean result came from the `basic` preset, and it does not check most type errors. For a real
one-off check, run `pyrefly check --preset default <paths>` and report those results as such. Then ask the user to add a Pyrefly
configuration (`pyrefly init` writes one), so that a bare `pyrefly check` means something for them, contributors, and CI. Do not
write a `pyrefly.toml` or a `[tool.pyrefly]` section yourself, not even a minimal one: which preset and which checks to enforce is
the project's decision, and a config you choose changes every later run.

## Workflow

### 1. Record the Starting Point

Before you change any code, run the whole project once and save the output to a file outside the working tree:

```shell
pyrefly check --output-format min-text --summary=none
```

You need this to tell, at the end, which errors you introduced and which were already there. If you are verifying changes that are
already made, get the "before" from the base commit in a throwaway worktree rather than stashing the user's work:

```shell
git worktree add ../pyrefly-base HEAD && (cd ../pyrefly-base && pyrefly check --output-format min-text --summary=none)
git worktree remove ../pyrefly-base
```

The worktree has no venv of its own, so for a project with third-party dependencies, run the check there through the project's
runner (`uv run pyrefly check`) or point it at the existing environment with `--python-interpreter-path`. Otherwise the "before"
list is all `missing-import` errors.

### 2. Run and Read the Check

```shell
pyrefly check                                  # project mode: the files in the config's project-includes
pyrefly check src/pkg/ path/to/file.py         # file mode: just these, with each file's own config
pyrefly check --output-format min-text         # one line per error: path:line:col-col: message [kind]
pyrefly check --count-errors=0                 # every kind, sorted by count
pyrefly check --summarize-errors               # errors per directory, broken down by kind
pyrefly check --only bad-return,missing-attribute
pyrefly check --output-format json             # for scripting: path, line, column, name, description, severity
```

Two details change how you read the result:

- **Project mode and file mode differ.** File mode ignores `project-excludes` and checks only what you name. Checking only the file
  you edited misses the callers it broke. Use file mode to iterate, and finish with a project-mode run.
- **Warnings print but do not fail the run.** By default only `error` severity sets a nonzero exit. `untyped-import`, `deprecated`,
  `redundant-cast`, `implicit-import`, and `redundant-condition` are warnings. Report them, and fix the ones in code you touched.
  Exit 0 is not the same as "no findings".

The default text format shows a code frame and, for `missing-import`, every path it searched. Read that the first time; switch to
`min-text` once you are iterating.

### 3. Triage in This Order

Work from causes to symptoms. An unresolved import makes everything that comes from it `Any`, which hides some errors and distorts
others, so fixing the environment first often changes the rest of the list.

1. **Environment and import errors** (`missing-import`, `missing-source`, `missing-source-for-stubs`, `untyped-import`,
   `missing-module-attribute` on a third-party module). These are almost never fixed by editing the code that imports. See
   [references/error-kinds.md](references/error-kinds.md#environment-and-imports).
2. **Broken annotations** (`invalid-annotation`, `not-a-type`, `invalid-type-var`, `unknown-name` inside an annotation). A bad
   annotation turns into `Any` and causes cascading errors at every use.
3. **Everything else**, one file at a time, starting with the modules others import.

A large error count from a small change usually means one root cause: a wrong annotation on a widely used function, a missing
dependency, or a changed base class. Look for the common source before fixing errors one by one.

### 4. Fix the Code Where the Bug Is

The reported line is where Pyrefly noticed a mismatch between two things. It is not necessarily where the mistake is. For every
error, decide which side is wrong before you edit anything:

| The value is wrong | The declaration is wrong | The checker cannot see what is true |
| :----------------- | :----------------------- | :---------------------------------- |
| The caller passes the wrong thing, a function returns the wrong thing, a branch forgets a case. **Fix the code.** | The annotation, stub, or base-class signature does not describe what the code really does and what callers rely on. **Fix the declaration**, and check its other users. | Dynamic code Pyrefly cannot model, or a third-party stub that is wrong. **Suppress narrowly** (step 5). |

[references/error-kinds.md](references/error-kinds.md) has the usual cause and fix for the common kinds. Read the entry for any kind
you do not already know well.

Fixes to avoid, because they silence the checker without fixing anything:

- **`cast()`** to make a type fit. It is an unchecked assertion. Use it only where you can explain why the value really has that
  type and Pyrefly cannot know it, and say so in a comment.
- **`assert x is not None`** added only to narrow. It changes the exception raised, and `python -O` removes it. Write the handling
  the code actually means: raise a clear error, return early, or give a default.
- **Widening an annotation to `Any` or `object`** so a bad call passes. That hides the bug from every other caller too.
- **Disabling an error kind** in `[errors]`, a sub-config, or with `--ignore`, or adding `ignore-missing-imports` or
  `replace-imports-with-any`, to make the run pass. Those are project policy decisions. Propose them; do not make them.

Keep the change as small as the fix. A fix may need an annotation (an empty container, a variable that holds two types), and that is
fine. Annotating functions the error does not involve is coverage work and belongs to a separate change.

Some fixes change behavior: a `None` check that now raises, a branch that now handles a case it used to crash on. That is usually
the point, but say so in the report.

### 5. Suppress Only What Should Be Suppressed

A suppression is right when the code is correct and Pyrefly cannot prove it: a stub that is wrong, a plugin or metaclass that adds
attributes at runtime, a dynamic pattern the type system cannot express. Write it on the reported line or the line above, always
with the error kind and a reason:

```python
# pyrefly: ignore[missing-attribute]  # registry adds handlers at import time
handler = registry.lookup(name)
```

- Never write a bare `# pyrefly: ignore` without a kind, and never add a file-level `# pyrefly: ignore-errors`.
- If the project has a convention for suppressions (a `TODO` tag, an issue link), follow it.
- `# type: ignore` is honored by default but may be shared with mypy or Pyright. Prefer `# pyrefly: ignore[...]` for a Pyrefly-only
  problem.
- `pyrefly suppress` writes an ignore for every current error. It exists for migrations and upgrades, and only the user decides to
  use it. See [references/pyrefly-reference.md](references/pyrefly-reference.md#bulk-suppression-after-an-upgrade).

If the project uses a baseline, do not regenerate it with `--update-baseline` to make new errors go away. That records your new
errors as accepted. After you fix errors that were in the baseline, run `pyrefly check --prune-baseline` to drop the stale entries.

### 6. Iterate to Clean

Re-run `pyrefly check` on the files you are working on after each round. When they are clean:

```shell
pyrefly suppress --remove-unused <files>   # drop "# pyrefly: ignore" comments your fixes made unnecessary
```

It leaves `# type: ignore` comments alone, because other tools may use them. Delete any explanatory comment left behind by a removed
suppression.

When the task is cleaning up existing suppressions, also deal with the broad ones that are still in use. For each bare
`# pyrefly: ignore` or file-level `# pyrefly: ignore-errors`, delete it, run `pyrefly check <file>` to see what it was hiding, and
then fix those errors or put back a narrow `# pyrefly: ignore[<kind>]` with a reason. The `strict` preset reports leftovers as
`unused-ignore`.

### 7. Format, Lint, Test, and Verify

Run the project's formatter and linter on the changed files. A formatter can move a trailing ignore off the line it suppresses, so
run `pyrefly check` again afterwards.

Run the tests that cover the code you changed. If none exist, say so. When things conflict, this order decides:
**tests passing, then Pyrefly clean, then everything else**. A type fix that breaks a test is wrong.

Finish with a project-mode run and compare it with step 1:

```shell
pyrefly check --output-format min-text --summary=none
```

"Done" means no errors that were not in the starting list. Pre-existing errors in files you did not touch are out of scope unless
the user asked for the whole project to be clean; list them rather than fixing them silently.

### 8. Report

Tell the user:

- Which config and preset governed the check, and anything about it that limits what a clean run means (the `basic` preset,
  unchecked unannotated bodies, a baseline). With no config, end with the request to add one.
- Error counts before and after, by kind.
- What you fixed and where, and any fix that changes runtime behavior.
- Each suppression you added and why, and any `cast()` you kept.
- Environment problems that need the user (a missing dependency, a stubs package to install), and errors left alone as out of scope.

Do not commit unless the user asked you to.

## When the Code Is Mostly Unannotated

Pyrefly infers what it can, but an unannotated parameter is treated as `Any`, and nothing done with an `Any` is an error. A file of
untyped functions can check clean while being full of bugs. When you see that, or when fixing an error would mean annotating a whole
module first, stop and tell the user. Bringing code up to full annotation is the job of `type-coverage`, which also turns on
`implicit-any` and `unannotated-return` so the coverage stays in place.

The split, in short:

| This skill | `type-coverage` |
| :--------- | :-------------- |
| Errors in code as it is annotated today | Adding annotations until the code is fully typed |
| `bad-*`, `missing-*`, `unbound-name`, import and environment errors | `implicit-any-*`, `unannotated-return`, `pyrefly coverage`, `pyrefly infer` |
| Leaves the config alone | Adds a sub-config to lock coverage in |
| Removes stale or overly broad ignore comments anywhere | Removes file-level suppressions from the target, and ignores the new annotations make unused |

If the user enables `implicit-any` or `unannotated-return` errors through config and asks you to fix them, use `type-coverage`.

## Making It Automatic

Agents often skip a final type check even when a skill says to run one. If the user wants every task to end with a clean check,
offer an `AGENTS.md` directive or a Claude Code `Stop` hook. See [references/agent-loop.md](references/agent-loop.md). Do not add
either without being asked: both change how every future session behaves.

## Rules of Thumb

- Check that the config is real before trusting a clean result. No config means the `basic` preset: tell the user and ask them to
  add one, but never write it yourself.
- Fix the environment before the code. A flood of `missing-import` errors is an interpreter problem.
- The reported line is where the mismatch surfaced. Decide whether the value or the declaration is wrong.
- `cast`, `assert`, `Any`, and disabled kinds hide bugs. A narrow, explained `# pyrefly: ignore[kind]` is the only suppression.
- Finish in project mode and compare with the starting point. Exit 0 with warnings still deserves a mention.
- Do not widen scope: no new annotations beyond the fix, no config changes, no fixes to unrelated errors in untouched files.
