# Combining Coverage in CI

Each test job measures one Python version on one operating system. The gate belongs on the union of all of them, so every job saves
its raw data and one final job combines, reports, and enforces `fail_under`. This replaces a hosted coverage service for the gate;
keep the service only if the team wants its pull-request comments.

## Contents

- [Configuration](#configuration)
- [GitHub Actions](#github-actions)
- [`tox`](#tox)
- [`nox`](#nox)
- [Path Remapping](#path-remapping)
- [Pitfalls](#pitfalls)

## Configuration

```toml
[tool.coverage.run]
branch = true
parallel = true            # unique .coverage.<host>.<pid>.<random> file per process
relative_files = true
source_pkgs = ["mypkg"]
patch = ["subprocess"]     # if tests start Python subprocesses

[tool.coverage.report]
show_missing = true
skip_covered = true
fail_under = 91            # the current combined total, rounded down
```

## GitHub Actions

Put `coverage` (and `pytest`) in the dev dependency group so each job runs the same versions the lock file pins.

```yaml
jobs:
  tests:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.12", "3.13"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: ${{ matrix.python }}
      - run: uv run coverage run -m pytest
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-data-${{ matrix.os }}-${{ matrix.python }}   # every matrix dimension, or uploads collide
          path: .coverage.*
          include-hidden-files: true                                  # .coverage files are dotfiles
          if-no-files-found: error

  coverage:
    needs: tests
    if: always()             # report even when a test job failed
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
      - uses: actions/download-artifact@v5
        with:
          pattern: coverage-data-*
          merge-multiple: true
      - run: uv run coverage combine
      - run: uv run coverage report --format=markdown >> "$GITHUB_STEP_SUMMARY"
      - run: uv run coverage html --skip-covered
      - run: uv run coverage report    # exits 2 below fail_under
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: coverage-html
          path: htmlcov
```

With pytest-cov instead, run `uv run pytest --cov --cov-report=` in each job (the empty `--cov-report=` skips the per-job terminal
report). pytest-cov manages parallel mode itself and leaves one combined file per job, so give it a unique name with
`env: COVERAGE_FILE: .coverage.${{ matrix.os }}-${{ matrix.python }}` on that step; the upload pattern above still matches. Keep
`--cov-fail-under` off the per-job command.

## `tox`

Give each environment its own data file name, then combine in a final environment:

```ini
[testenv]
setenv = COVERAGE_FILE = {toxworkdir}/.coverage.{envname}
commands = coverage run -m pytest {posargs}

[testenv:coverage]
depends = py312, py313
skip_install = true
deps = coverage
setenv = COVERAGE_FILE = {toxworkdir}/.coverage
commands =
    coverage combine {toxworkdir}
    coverage report
```

tox installs the package into each environment's `site-packages`, so add the `[paths]` mapping below.

## `nox`

```python
@nox.session(python=["3.12", "3.13"])
def tests(session):
    session.install("-e", ".", "--group", "dev")
    session.run("coverage", "run", "-m", "pytest", env={"COVERAGE_FILE": f".coverage.{session.name}"})


@nox.session
def coverage(session):
    session.install("coverage")
    session.run("coverage", "combine")
    session.run("coverage", "report")
```

## Path Remapping

Coverage records absolute file paths unless `relative_files = true`, and even relative paths differ when a package is imported from
`site-packages` instead of `src/`. `[tool.coverage.paths]` tells `combine` which paths are the same file. The first entry in each
list must exist where you combine; the others are patterns for where the data was recorded:

```toml
[tool.coverage.paths]
source = [
    "src/",
    "*/site-packages/",
    ".tox/*/lib/python*/site-packages/",
    "D:\\a\\myproj\\myproj\\src\\",
]
```

Since Coverage.py 7.16, path separators are converted to the local style on combine, so a Windows job's `src\pkg\x.py` and a Linux
job's `src/pkg/x.py` match without a mapping. Use `coverage combine --debug=pathmap` to see how each path was remapped.

## Pitfalls

- **One job's file overwrites another's:** artifact names must include every matrix dimension, and data files must be parallel
  (`parallel = true`, or a distinct `COVERAGE_FILE` per environment).
- **The combine job finds nothing:** `upload-artifact` skips dotfiles unless `include-hidden-files: true`.
- **The total is lower than every job's:** a path mapping is missing, so the same file appears under two names, each partly covered.
  Check `coverage report` for duplicate file names.
- **Coverage.py 7.17.1** fails `coverage combine` on older SQLite; pin past it.
- **A data file from an older run** is combined in: `coverage erase` before local runs, and never commit `.coverage*`.
