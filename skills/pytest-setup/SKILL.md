---
name: pytest-setup
description: >
  Configure pytest for a Python project or modernize the configuration it has: settle on one config file, write the pytest 9
  native [tool.pytest] table (or [tool.pytest.ini_options] on 8.x), turn on strictness and warnings-as-errors, register markers,
  keep coverage and other per-run flags out of addopts, choose plugins (xdist, randomly, timeout, asyncio), and move a unittest
  suite onto pytest. Use this skill whenever the user wants to set up pytest, add, fix, consolidate, or upgrade pytest
  configuration (pytest.ini, pyproject.toml, tox.ini, setup.cfg, conftest.py layout), make the suite stricter or stop it hiding
  warnings, add a pytest plugin, or migrate from unittest or nose, even if they only say "clean up our test config". Not for
  writing test functions (use pytest-writing), diagnosing failing, flaky, or uncollected tests (pytest-triage), or coverage
  settings (coverage-config).
compatibility: >
  Requires pytest 8.0 or later; written against pytest 9.2. Runs pytest the way the project runs it (uv, pip, tox, nox, hatch).
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/skills/pytest-setup
  version: 1.0.0
---

# Setting up `pytest`

A good pytest configuration makes mistakes loud: a typo in the config, an unregistered marker, an `xfail` that started passing, or a
new deprecation warning fails the run instead of scrolling past. This skill sets that up and keeps everything else out of the way,
so `pytest` with no arguments runs the whole suite quickly and the same way for everyone.

The project's own conventions win. If it already has a style for config, markers, or plugins, extend it rather than replace it.

## Before You Change Anything

1. **Learn how tests run.** Look at the dev dependencies, lock file, `Makefile`, `noxfile.py`, `tox.ini`, and CI workflow, and use
   the same command (`uv run pytest`, `hatch test`, `tox -e py312`). If pytest is not installed, add it to the project's dev
   dependency group rather than installing it globally.
2. **Check versions.** `pytest --version` and `python --version` decide what is allowed: the native `[tool.pytest]` table and
   `strict = true` need pytest 9.0 or later. Recommend at least 9.0.3, which fixes an insecure temporary directory (CVE-2025-71176).
3. **Find every config file.** pytest reads exactly one, the first that matches, and never merges them: `pytest.toml` or
   `.pytest.toml`, then `pytest.ini` or `.pytest.ini`, then `pyproject.toml` (only if it has a pytest table), then `tox.ini`, then
   `setup.cfg`. The run header's `configfile:` line shows which one won, and pytest warns when it ignores a pytest table in
   `pyproject.toml`. Settings in the losing files have never applied, so read them as intentions, not as current behavior.
4. **Record a baseline.** Run the suite and note the collected, passed, skipped, and failed counts and the warnings. You will
   compare against these at the end to prove nothing was lost.

## The Configuration

Put the configuration in `pyproject.toml` and delete the other pytest sections once their settings have moved. On pytest 9 or later:

```toml
[tool.pytest]
minversion = "9.0"
testpaths = ["tests"]
addopts = ["-ra"]
strict = true
filterwarnings = ["error"]
log_level = "INFO"
markers = [
    "slow: takes more than a second; deselect with -m 'not slow'",
]
```

| Setting | Why |
| :------ | :-- |
| `testpaths` | Collection starts here instead of crawling the whole repository |
| `-ra` | The summary lists the reason for every skip, xfail, error, and failure |
| `strict = true` | Turns on `strict_config` (unknown options fail), `strict_markers`, `strict_xfail` (an unexpected pass fails), and `strict_parametrization_ids` |
| `filterwarnings = ["error"]` | A warning fails the test that raised it, so deprecations surface when they appear, not when the feature is removed |
| `log_level` | Captured log records at INFO and above are shown for failing tests |
| `minversion` | Older pytest refuses to run with a config it would misread |

`[tool.pytest]` takes real TOML types: `addopts` is a list, booleans are `true`, not `"true"`, and pytest rejects a string where it
expects a list. A file with both `[tool.pytest]` and `[tool.pytest.ini_options]` is an error, so convert in one step.

**On `strict = true`:** it also adopts strictness options added in future pytest releases, so the pytest docs advise it only when
the pytest version is pinned or locked. With a lock file (`uv.lock`, `poetry.lock`, pinned requirements), use it. Without one,
either pin pytest or set the four options individually: `strict_config = true`, `strict_markers = true`, `strict_xfail = true`,
`strict_parametrization_ids = true`.

On pytest 8.x, use the INI-style table with the equivalent flags:

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]
xfail_strict = true
filterwarnings = ["error"]
```

Drop settings that only restate defaults, such as `python_files = test_*.py *_test.py` or a `norecursedirs` that lists only build
and VCS directories. Keep any that differ from the defaults, and keep `python_files` whenever test files are named `*_test.py` or
anything else unusual.

### What Stays Out of `addopts`

`addopts` applies to every run, including an IDE running one test under a debugger. Keep it to options that are right for all of
them.

| Do not put in `addopts` | Why | Put it here instead |
| :---------------------- | :-- | :------------------ |
| `--cov`, `--cov-report`, `--cov-fail-under` | Coverage tracing breaks debugger breakpoints, slows every run, makes a one-test run fail the coverage gate, and makes `coverage run -m pytest` report 0% | The CI or task-runner command; see the coverage-config skill |
| `--disable-warnings`, `-p no:warnings`, `-W ignore` | Hides exactly what `filterwarnings = ["error"]` exists to surface | Narrow `ignore:` entries in `filterwarnings` |
| `-n auto` (pytest-xdist) | Breaks `--pdb` and interleaves output; hides order bugs until the suite is isolated | CI command, or `addopts` only once the suite is known to be isolated |
| `--showlocals` | Can print secrets into CI logs | Local runs |
| `--rootdir` | Not allowed there | The command line |

## Warnings as Errors

Turning on `filterwarnings = ["error"]` in an existing project usually fails some tests at once. Work through each warning:

- **Raised by the project's own code:** fix the code. For example, replace `datetime.utcnow()` with `datetime.now(datetime.UTC)`,
  and tell the user if the fix changes behavior (that one makes the value timezone-aware).
- **Raised by a third-party library you cannot change:** add a narrow ignore after `"error"`, with a comment saying why and when it
  can go. The format is `action:message:category:module`, the message is a regular expression matched at the start, and later
  entries win:

  ```toml
  filterwarnings = [
      "error",
      # botocore 1.40 uses datetime.utcnow(); remove after upgrading
      "ignore:datetime.datetime.utcnow:DeprecationWarning:botocore",
  ]
  ```

- **Expected by a test:** assert it with `pytest.warns` in that test; do not ignore it globally.

Never add a blanket `ignore::DeprecationWarning`; it undoes the setting.

## Layout and Imports

- **Test the installed package.** A `src/` layout with a top-level `tests/` directory, and the project installed into the
  environment (`uv sync`, or `pip install -e .`), means tests import what users import. Use `pythonpath = ["src"]` only when the
  project cannot be installed.
- **Prefer `pytest` to `python -m pytest`** in commands you add. The `-m` form puts the current directory on `sys.path`, which can
  hide a packaging bug.
- **Keep the project's import mode.** The pytest docs recommend `--import-mode=importlib` for new projects, but under it test
  modules cannot import each other or a `tests/helpers.py`. Switching an existing project breaks those imports, so do it only when
  asked, and move shared helpers into `conftest.py` fixtures or an importable package first.
- **`conftest.py` holds shared fixtures and hooks** for its directory and everything below it. Never `import conftest` or import
  fixtures into test modules; pytest finds them by name. Declare `pytest_plugins` only in the root `conftest.py`.

## Markers

Register every custom marker in `markers`, with a description. Under strict markers an unregistered marker is a collection error,
and since pytest 9.2 so is an unknown name in a `-m` expression. To find them, search the tests for `pytest.mark.<name>` and
`pytestmark`. Built-in marks (`skip`, `skipif`, `xfail`, `parametrize`, `usefixtures`, `filterwarnings`) and marks owned by
installed plugins (`asyncio`, `timeout`, `xdist_group`) are already registered.

## Plugins

Add a plugin when it solves a problem the project has, and add it to the dev dependency group.

| Plugin | Add it when | Configure |
| :----- | :---------- | :-------- |
| pytest-xdist | The suite takes long enough to matter and tests are isolated | `-n auto` in CI; `--dist loadgroup` with `@pytest.mark.xdist_group` for tests that share a resource. Session fixtures run once per worker |
| pytest-randomly | You want order dependence found before CI finds it | Nothing; it shuffles every run and prints its seed. Reproduce with `--randomly-seed=<seed>`, disable with `-p no:randomly` |
| pytest-timeout | Tests can hang in CI | `timeout = 300` as a backstop; `@pytest.mark.timeout(n)` for known slow tests. Windows uses the `thread` method, which ends the whole run |
| pytest-asyncio | Tests are `async def` (pytest 8.4+ fails them without an async plugin) | See below |
| pytest-mock | The project asserts on calls or uses spies | Nothing; provides the `mocker` fixture |
| hypothesis | Property-based tests | Profiles in `conftest.py`; the `ci` profile is derandomized |

**pytest-asyncio:** for a project that uses only asyncio, set `asyncio_mode = "auto"`. If it also uses AnyIO or trio, leave the
default `strict` mode, where tests need `@pytest.mark.asyncio` and async fixtures need `@pytest_asyncio.fixture`; AnyIO's own
`anyio_mode = "auto"` conflicts with pytest-asyncio's auto mode. In both cases set
`asyncio_default_fixture_loop_scope = "function"`. Left unset it emits a deprecation warning, and under `filterwarnings = ["error"]`
that warning crashes pytest with an INTERNALERROR before any test runs.

Do not add pytest-rerunfailures as a fix for flaky tests, `setup.py test`, pytest-runner, or nose; they are obsolete or hide
problems.

## Migrating from `unittest`

pytest runs `unittest.TestCase` classes as they are, including `setUp`, `tearDown`, `setUpClass`, `skip`, and `subTest` (pytest
9.0+). Only `load_tests` is unsupported. That makes the migration incremental:

1. **Run the existing suite under pytest unchanged.** Add pytest and the configuration above, then compare the counts with the
   unittest run, skips included. Fix any difference before converting anything.
2. **Switch the documented command** (README, CI, Makefile) to pytest. Once a file is converted, `python -m unittest` no longer sees
   its tests, so leaving the old command anywhere quietly drops tests.
3. **Convert file by file** to plain functions, or plain `class Test...:` groups with no `__init__`. `TestCase` methods cannot take
   fixtures or use `parametrize`, which is the main reason to convert.

| unittest | pytest |
| :------- | :----- |
| `self.assertEqual(a, b)`, `assertTrue(x)`, `assertIn(a, b)` | `assert a == b`, `assert x`, `assert a in b` |
| `with self.assertRaises(E) as cm:` then `assertIn("msg", str(cm.exception))` | `with pytest.raises(E, match="msg"):` (a regex search; use `re.escape` for literal text) |
| `self.assertRaises(E, f, x)` | `with pytest.raises(E):` then `f(x)` |
| `self.assertAlmostEqual(a, b, places=6)` | `assert a == pytest.approx(b, abs=1e-6)` |
| `setUp` / `tearDown` | A fixture that builds the object, with `yield` and cleanup when there is teardown |
| `setUpClass` building immutable data | A module-level constant, or a `scope="module"` fixture |
| `self.subTest(...)` in a loop over known inputs | `@pytest.mark.parametrize` with `ids` |
| `@unittest.skip("why")` | `@pytest.mark.skip(reason="why")` |

The `unittest2pytest` tool rewrites assertions mechanically; review its output. Check each converted file by breaking the code it
tests once and watching the converted test fail.

## Checking Your Work

- The run header shows `configfile:` pointing at the file you intended, with no "ignoring pytest config" warning.
- Collected, passed, and skipped counts match the baseline (`pytest --collect-only -q | tail -n 1` for the collected count), and no
  test was silently skipped or deselected.
- A quick negative check shows the strictness works: an unregistered marker or a misspelled option should now fail. Revert it.
- No coverage, warning-suppression, or debugger-hostile flags are left in `addopts`.
- Tell the user what moved where, every warning you fixed or ignored and why, and any behavior change in their code.
