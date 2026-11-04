# Pyrefly Reference

The Pyrefly commands, comments, and config rules this skill relies on, checked against Pyrefly 1.4 and the
[Pyrefly docs](https://pyrefly.org/en/docs/). Where your installed version disagrees, `pyrefly <command> --help` wins.

- [Commands](#commands)
- [Suppression comments](#suppression-comments)
- [Config: errors, presets, and sub-configs](#config-errors-presets-and-sub-configs)
- [Error kinds this skill touches](#error-kinds-this-skill-touches)

## Commands

| Command | What it does |
| :------ | :----------- |
| `pyrefly check <files>` | Check the files, using the config found for each file. Without files, checks the project's `project-includes`. |
| `pyrefly check <file> --error <kind>` | Raise a kind to error for this run only. Repeatable. `--warn`, `--info`, `--ignore` work the same way. |
| `pyrefly check <file> --only <kind>` | Show only one kind. |
| `pyrefly check <file> --summarize-errors` | Count errors by kind, for triage. |
| `pyrefly check --output-format json` | Machine-readable output. |
| `pyrefly dump-config <file>` | Show which config file governs a file and how imports resolve. |
| `pyrefly coverage check <path> --fail-under <pct>` | List `coverage-missing` and `coverage-partial` symbols; exit nonzero below the threshold. `--strict` counts `Any` as untyped. |
| `pyrefly coverage report <path>` | JSON report: `summary.coverage`, `summary.strict_coverage`, and per-module `symbol_reports` with locations. |
| `pyrefly infer <files>` | Write inferred annotations in place (experimental). `--parameter-types`, `--return-types`, `--containers`, `--imports` take `=false`. |
| `pyrefly suppress --remove-unused <files>` | Delete unused `# pyrefly: ignore` comments (and Pyre ones). `=type` or `=all` also removes unused `# type: ignore`. |
| `pyrefly suppress <files>` | Add an ignore comment for every current error. Not part of this workflow: it hides the errors this work is meant to fix. |

Coverage counts only public symbols: names without a leading underscore, plus anything in `__all__`. `self` and `cls` are not
counted, and overloads are merged. The optional `coverage` table in the config (`coverage.includes`, `coverage.excludes`) narrows
the files a project-wide coverage run reports on; it is ignored when you pass paths.

## Suppression Comments

| Comment | Scope | Notes |
| :------ | :---- | :---- |
| `# pyrefly: ignore[<code>]` | The line it is on, or the next line when it stands alone | The form to use. Always give the code. |
| `# pyrefly: ignore` | Same | Suppresses every kind on the line. Avoid. |
| `# type: ignore[...]` | Same | Honored by default, and may be shared with mypy or Pyright. |
| `# pyrefly: ignore-errors` | Whole file | Only at the top of the file, before any code. Below that it is inert and reported as `misplaced-ignore`. |
| `# pyrefly: ignore-errors[<code>]` | One kind, whole file | Same placement rule. |
| `# mypy: ignore-errors`, `# pyre-ignore-all-errors`, `# pyre-fixme`, `# pyright: ignore`, ... | Not honored by default | Honored only with `permissive-ignores = true` or when `enabled-ignores` lists the tool. Default `enabled-ignores` is `["type", "pyrefly"]`. |

Unused suppressions are reported by `unused-ignore` (for `# pyrefly: ignore`) and `unused-type-ignore` (for `# type: ignore`). Both
are off by default; `unused-ignore` is on in the `strict` preset.

A **baseline file** (`baseline = "baseline.json"`, `pyrefly check --update-baseline`) is the project-wide alternative to suppression
comments when adopting Pyrefly. It is a project-level setting, cannot be set per sub-config, and is not a tool for this skill. If
the target's errors are recorded in a baseline, they are hidden from the CLI but still shown in the IDE; run
`pyrefly check --prune-baseline` after fixing them so the baseline does not keep stale entries.

## Config: Errors, Presets, and Sub-Configs

**Severity.** Each key in `[errors]` takes `"error"`, `"warn"`, `"info"`, `"hint"`, `"ignore"`, `true` (default severity, or error
if the kind is off by default), or `false`. By default `pyrefly check` shows and fails on errors only; `min-severity` lowers that.

**Precedence.** CLI flags, then the config file, then the preset, then Pyrefly's defaults.

**Presets** (`preset = "..."`):

| Preset | Relevant effect |
| :----- | :-------------- |
| `basic` | Only high-confidence checks. Skips unannotated function bodies. Used automatically when no config exists. |
| `legacy` | For mypy migrations: `check-unannotated-defs = false`, `infer-return-types = "never"`, untyped imports become `Any`. |
| `default` | Each kind at its own default severity. Same as no preset. |
| `strict` | Adds `implicit-any` (all sub-kinds), `unused-ignore`, `missing-override-decorator`, and others. Does **not** add `unannotated-return`. |
| `all` | Every kind at error. |

**Sub-configs** override settings for files matching a glob. Only these keys are allowed: `errors`, `replace-imports-with-any`,
`replace-untyped-imports-with-any`, `check-unannotated-defs`, `infer-return-types`, `ignore-errors-in-generated-code`. Settings that
change which files are checked, the Python environment, or import resolution need a separate config file instead.

```toml
# pyrefly.toml
[[sub-config]]
matches = "src/pkg/**"
[sub-config.errors]
implicit-any = true
unannotated-return = true
```

```toml
# pyproject.toml
[[tool.pyrefly.sub-config]]
matches = "src/pkg/**"
[tool.pyrefly.sub-config.errors]
implicit-any = true
unannotated-return = true
```

Resolution rules, as observed in Pyrefly 1.4:

- A sub-config's `errors` merge over the root `[errors]`: keys it does not set keep the root's value.
- When several sub-configs match one file, the **first matching entry in file order** supplies the `errors`, and the `errors` of
  later matches are ignored, even when the first entry sets no errors. The docs' own example suggests later entries fill in unset
  options; 1.4 does not do that for `errors`. Order entries from most specific to least, and copy any settings a specific entry
  still needs from the broader ones.
- After editing, confirm with a plain `pyrefly check <file>` that the expected kinds are reported.

`extends = "<path>"` builds one config on another. Child scalars and lists replace the parent's; tables such as `[errors]` merge by
key.

## Error Kinds This Skill Touches

**Target kinds** (always fixable by annotating; default severity `ignore`, so they must be enabled):

| Kind | Raised when |
| :--- | :---------- |
| `unannotated-return` | A function has no return annotation. |
| `implicit-any` | Umbrella for the five kinds below. Enabling or disabling it cascades. |
| `implicit-any-parameter` | A parameter other than `self` or `cls` has no annotation. Formerly `unannotated-parameter`. |
| `implicit-any-attribute` | An attribute is inferred as `Any \| None` or `tuple[Any, ...]` because a method assigned `None` or `()` without a declaration. Formerly `unannotated-attribute`. |
| `implicit-any-empty-container` | `[]` or `{}` has nothing to infer its element type from. |
| `implicit-any-type-argument` | A generic (`list`, `dict`, `tuple`, `Callable`, `type`, a user generic) is used without type arguments. |
| `implicit-any-lambda` | A lambda parameter's type cannot be inferred from context. |

**Related kinds** worth knowing about:

| Kind | Default | Notes |
| :--- | :------ | :---- |
| `unannotated-protocol-member` | error | A `Protocol` member assigned in the class body without an annotation. |
| `untyped-function-decorator`, `untyped-class-decorator` | ignore | A decorator whose type is unknown erases the decorated object's type. Fixed by annotating the decorator (see `ParamSpec`). |
| `untyped-namedtuple` | ignore | `collections.namedtuple` instead of `typing.NamedTuple`. |
| `missing-override-decorator` | ignore | Overriding method lacks `@override`. On in `strict`. |
| `bad-override-param-name` | error | An override renames a positional parameter. Formerly `bad-param-name-override`. |
| `implicit-import` | warn | A submodule used through its parent package without being imported. |
| `misplaced-ignore` | warn | A file-level ignore directive below the first line of code. |
| `unused-ignore` | ignore | A `# pyrefly: ignore` that suppresses nothing. On in `strict`. |
| `untyped-import` | warn | A third-party package is used without its separate stubs package installed. |

Deprecated names (`unannotated-parameter`, `unannotated-attribute`, `bad-param-name-override`) are still accepted in config and
comments, but write the current names.
