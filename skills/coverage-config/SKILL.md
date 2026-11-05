---
name: coverage-config
description: >
  Set up, fix, or explain Coverage.py measurement for a Python project, with or without pytest-cov: branch coverage, source_pkgs,
  exclude_also, measuring subprocesses, multiprocessing, and pytest-xdist workers, combining data across a CI matrix or tox and nox
  environments with `[paths]` remapping, report formats, and a fail_under gate set from the current number. Use this skill whenever
  the user wants to add code coverage, measure it in CI, combine coverage from several jobs or operating systems, or gate a build on
  it, or asks why coverage shows 0%, "No data was collected", "module was never imported", missing subprocess or worker coverage,
  pragmas that are ignored, numbers that differ between `pytest --cov` and `coverage run`, or debugger breakpoints that stopped
  working after coverage was added. Not for writing tests to raise coverage or deciding what to exclude (use coverage-gaps), or
  general pytest configuration (pytest-setup).
compatibility: >
  Requires Coverage.py 7.10 or later for the patch setting; written against Coverage.py 7.17.2 and pytest-cov 7.1.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/skills/coverage-config
  version: 1.0.0
---

# Coverage Configuration

Coverage measurement should be configured once, in `[tool.coverage]`, so that `pytest --cov`, `coverage run -m pytest`, a local run,
and every CI job produce the same number from the same rules. Almost every "coverage is weird" report is two of those paths
disagreeing, or a setting that silently replaced a default.

## Before You Change Anything

- **Find how coverage runs today:** the CI workflow, `Makefile`, `noxfile.py`, `tox.ini`, and pytest's `addopts`. Note whether the
  project uses pytest-cov (`--cov` flags) or `coverage run`.
- **Check versions.** `coverage --version` shows the version and the measurement core. Coverage.py 7.17 needs Python 3.11 or later,
  so a Python 3.10 environment resolves 7.16 or older. Avoid exactly 7.17.1, whose `coverage combine` fails on SQLite older than
  3.34 (RHEL 8, Ubuntu 20.04). The `patch` setting below needs 7.10 or later, and pytest-cov 7 requires it.
- **Find the config.** Coverage.py reads the first of `.coveragerc`, `.coveragerc.toml`, `setup.cfg`, `tox.ini`, and
  `pyproject.toml` that has coverage settings; `pyproject.toml` comes last. `coverage debug config` prints what it actually loaded.
  Consolidate into `pyproject.toml` unless the project keeps tool config elsewhere.
- **Measure the current number** with the project's command before changing anything, so you can explain every difference.

## The Configuration

```toml
[tool.coverage.run]
branch = true
source_pkgs = ["csvtool"]          # the importable package name, not "src"
relative_files = true              # needed to combine data recorded in different directories or machines
patch = ["subprocess"]             # only if tests start Python subprocesses; also turns on parallel mode

[tool.coverage.report]
show_missing = true
skip_covered = true
exclude_also = [
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "@(typing\\.)?overload",
    "(typing\\.)?assert_never\\(",
]
# fail_under = 91                  # see "The Gate"
```

| Setting | Why |
| :------ | :-- |
| `branch = true` | Line coverage can be complete while an `if` never took its false path. Off by default |
| `source_pkgs` | Limits measurement to the project and reports files no test imported. `source = ["src"]` also works but is ambiguous between a directory and a package |
| `relative_files` | Stores paths relative to the project, so data from CI runners, containers, and Windows combines |
| `patch = ["subprocess"]` | Measures Python processes started by `subprocess`, `os.system`, and the exec and spawn families. Required for CLI tests that run `python -m pkg`, and for `coverage run -m pytest -n auto` |
| `exclude_also` | Adds exclusion patterns to the defaults |
| `show_missing`, `skip_covered` | The report lists missing lines and branches, and only for files that have some |

**Use `exclude_also`, never `exclude_lines`.** `exclude_lines` replaces the default patterns, including `pragma: no cover`, so every
pragma in the code silently stops working. The defaults already exclude `# pragma: no cover`, lines that are only `...`, and
`if TYPE_CHECKING:` blocks (the last two since 7.10). Patterns are regular expressions matched anywhere in a line. Which code
deserves an exclusion is the coverage-gaps skill's job; keep this list to patterns for code that cannot run under test.

**Leave `core` unset.** Coverage.py picks the fastest measurement core that supports the configuration: `sysmon` by default on
Python 3.14 and later. Forcing `core = "sysmon"` on 3.12 or 3.13 with `branch = true` falls back with a warning, because sysmon
supports branch coverage there only from 3.14, and it never supports dynamic contexts or some concurrency libraries.

## Choose How to Run It

Keep what the project uses. For a new setup:

| Use | When |
| :-- | :--- |
| `coverage run -m pytest`, then `coverage report` | CI matrices that combine data, non-pytest entry points, the most control. Needs `patch = ["subprocess"]` for xdist workers |
| `pytest --cov` (pytest-cov) | One command locally, xdist handled for you, `--cov-context=test` to record which test ran each line |

Both read `[tool.coverage]`, so pass behavior through the config, not flags. `--cov-branch` on the command line with no `branch` in
the config gives different numbers from the two paths; put `branch = true` in the config instead. Pass `--cov` with no value, or
`--cov=` when it is the last option, so the configured `source_pkgs` applies.

### Keep Coverage Out of `addopts`

`--cov` in pytest's `addopts` turns coverage on for every run, which causes three common complaints:

- **`coverage run -m pytest` reports 0% and "No data was collected"**, because pytest-cov starts a second measurement inside the
  first and the outer run records nothing.
- **Debugger breakpoints stop working**, because coverage and the debugger compete for Python's tracing hook. This is mainly a
  Python 3.13-and-earlier problem; on 3.14 coverage defaults to `sys.monitoring`, which debuggers can share. pytest has no way to
  remove an `addopts` entry, so the only escape is `--no-cov` on every debug run.
- **Running one test fails the build** when `--cov-fail-under` is in `addopts`.

Put the coverage flags in the CI command, task runner, or `Makefile` target instead. If the team insists on coverage by default,
tell them `pytest --no-cov` is how to debug.

## Subprocesses, Multiprocessing, and `xdist`

- **Subprocesses:** `patch = ["subprocess"]` covers child Python processes. It turns on `parallel`, so each process writes its own
  `.coverage.*` file. Reporting commands combine them automatically since 7.14; run `coverage combine` explicitly when you need a
  single `.coverage` file, for example to upload from CI. Child processes started with a custom environment through `exec*e` or
  `spawn*e` need `COVERAGE_PROCESS_START` copied into it.
- **xdist:** pytest-cov combines worker data itself. Under `coverage run -m pytest -n auto`, workers are subprocesses: without
  `patch = ["subprocess"]` nothing is recorded at all.
- **multiprocessing:** add `concurrency = ["multiprocessing"]` and `sigterm = true` (no effect on Windows), and make the code call
  `pool.close()` and `pool.join()`; a process that is killed rather than exiting writes no data.
- **gevent, greenlet, eventlet:** set `concurrency` to the library; these need the C extension core.

## Combining Across a CI Matrix

Each job records its own data; one final job combines and reports. That is the only way the gate sees the union of every Python
version and operating system. The full GitHub Actions workflow, tox and nox variants, and `[paths]` examples are in
[references/ci-combine.md](references/ci-combine.md). Read it when you edit CI.

The essentials: every job writes uniquely named data files (`parallel = true` does that), uploads them as an artifact that includes
hidden files, and the combine job downloads all of them, runs `coverage combine`, then `coverage report`. A `[tool.coverage.paths]`
entry is needed when the recorded paths differ in more than separators, such as non-editable installs in `site-packages` or
different checkout directories:

```toml
[tool.coverage.paths]
source = ["src/", "*/site-packages/"]
```

The first entry must exist where you combine. Since 7.16, `\` and `/` differences are normalized automatically.

## The Gate

`fail_under` makes `coverage report` exit with status 2 when the total is below it.

- **Keep an existing gate** as it is. Raising or lowering it is the user's decision.
- **For a new gate, use the number you just measured, rounded down to a whole percent.** Read it with
  `coverage report --format=total --precision=2`: without `--precision`, the total is rounded to the nearest whole number, so 91.78
  prints as 92 and a gate of 92 fails at once. A gate at exactly 91.78 with `precision = 2` fails on harmless noise; one at 91 still
  catches real drops. Raise it as tests are added.
- **Do not invent a target** such as 80% or 100% the project has never met; that turns setup into an unrequested project of writing
  tests. Mention the gap and offer the coverage-gaps skill instead.
- **Gate the combined report**, not each matrix job; a single job legitimately misses other platforms' code.

For pull requests, `diff-cover` checks only the lines a change touched; see the coverage-gaps skill.

## Reports

| Report | Command | For |
| :----- | :------ | :-- |
| Terminal | `coverage report` | People and logs |
| Markdown | `coverage report --format=markdown >> "$GITHUB_STEP_SUMMARY"` | The CI job summary |
| Total only | `coverage report --format=total` | Scripts and gates; add `--precision=2` before rounding down for a gate, since the default rounds to nearest |
| JSON | `coverage json -q -o coverage.json` | Tools and agents: `files.<path>.missing_lines` and `missing_branches`. With `-o -`, a failed `fail_under` appends its message after the JSON |
| XML (Cobertura) | `coverage xml` | diff-cover, Codecov, Coveralls, IDEs |
| HTML | `coverage html --skip-covered` | Reading a file's gaps in context; upload as a CI artifact |

## Troubleshooting

| Symptom | Cause | Fix |
| :------ | :---- | :-- |
| 0% and "No data was collected" under `coverage run -m pytest` | `--cov` in `addopts` | Remove it from `addopts` |
| `# pragma: no cover` lines reported as missing | `exclude_lines` replaced the defaults | Rename it to `exclude_also` and drop any re-added `pragma: no cover` |
| `pytest --cov` and `coverage run` disagree | `--cov-branch` or `--cov=` given on one path only, or stale data | Move settings into `[tool.coverage]`; `coverage erase` before comparing |
| "Module ... was never imported" | `--cov` or `source_pkgs` names something that is not the import name: a typo, the distribution name (`my-lib` for `my_lib`), or a package that is not installed in the test environment | Use the import name, and install the project into the environment |
| Subprocess or worker code at 0% | Not measured | `patch = ["subprocess"]` |
| Function bodies covered but their `def` and `class` lines missing | Coverage started after the module was imported, often by a plugin or `conftest.py` loaded first | Start coverage first: `coverage run -m pytest`, or pytest-cov's `--cov`; do not import the package from an early plugin |
| Files missing from the report entirely | No `source`, or a namespace package without `__init__.py` | Set `source_pkgs`; add `include_namespace_packages = true` under `[report]` |
| Combine reports the same file twice, or paths that do not exist | Paths recorded in different places | `relative_files = true` and `[tool.coverage.paths]` |
| Breakpoints do not stop | Coverage tracing during a debug run | Run without `--cov`, or with `--no-cov` |

`coverage debug config` shows the settings in force, and `coverage run --debug=trace -m pytest` (or `COVERAGE_DEBUG=trace`) says,
file by file, whether it is measured and why not.

## Checking Your Work

- Every way the project runs coverage (local command, CI command, `pytest --cov` if it is installed) reports the same total.
- Subprocess-only code (a CLI's `main`) shows as covered when its tests ran it.
- A line with `# pragma: no cover` is excluded, and a deliberately lowered `fail_under` shows the gate failing with exit status 2.
- Plain `pytest` runs without coverage, and a single test runs without failing a gate.
- Tell the user what changed, the measured number and the gate, and anything you could not verify, such as a CI workflow you could
  not run.
