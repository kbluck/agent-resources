---
name: pytest-triage
description: >
  Run pytest efficiently and find the root cause when it goes wrong: failing or erroring tests, collection errors, exit codes such
  as 5 (no tests collected) and 4 (usage error), tests that pass alone but fail in the full suite or the reverse, order-dependent
  and flaky failures, failures only under pytest-xdist or only in CI, and hung runs. Use this skill whenever a pytest run fails,
  errors, hangs, collects nothing or fewer tests than expected, or behaves differently between runs or machines, or the user
  pastes pytest output and asks what is wrong, even if they only say "CI is red", "the tests are flaky", or "works on my machine".
  Not for writing new tests (use pytest-writing), configuring pytest (pytest-setup), coverage failures (coverage-py-setup or
  coverage-gaps), or replacing sleeps in timing-dependent tests (software-testing:condition-based-waiting).
compatibility: >
  Requires pytest 8.0 or later; written against pytest 9.2. Uses the project's own test command.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/python-testing/skills/pytest-triage
  version: 1.0.0
---

# Triaging `pytest` Failures

The goal is the root cause, shown by a reproduction, then fixed where it lives. A red suite made green by skipping, retrying,
reordering, or loosening an assertion has not been fixed; it has been hidden, and it will come back somewhere harder to debug.

## Before You Run Anything

Collecting tests imports code, and every `conftest.py` on the path runs its hooks and autouse fixtures. In an unfamiliar repository,
read the pytest config and the `conftest.py` files first: look for autouse fixtures that touch a database, the network, or files
outside the repository, and for plugins in `pytest_plugins` or `-p` options. Run tests the way the project does (`uv run pytest`,
`tox -e py312`), because a different environment is a different experiment.

## Read the Result First

| Exit code | Meaning | First move |
| :-------- | :------ | :--------- |
| 0 | All collected tests passed | Check the count is what you expect; a pass of too few tests is a collection problem |
| 1 | Some tests failed | Read the first failure |
| 2 | Interrupted: Ctrl-C, or errors during collection | Look for collection errors above the summary |
| 3 | Internal error | Usually a plugin or hook crashing; read the INTERNALERROR traceback, often a warning raised as an error |
| 4 | Usage error: bad option, unknown config key, missing plugin, broken `conftest.py` import | Read the first line of output |
| 5 | No tests were collected | Not a pass. See [Nothing or Too Little Collected](#nothing-or-too-little-collected) |
| 6 | Warning count exceeded `--max-warnings` (pytest 9.1+) | Fix the warnings |

Within a run, `FAILED` means the test body's assertion or code failed; `ERROR` means setup or teardown failed, so the fault is in a
fixture, not the test. A collection `ERROR` means the module could not be imported.

## Keep the Loop Fast and the Output Small

| Goal | Command |
| :--- | :------ |
| Re-run only what failed last time, stop at the first failure | `pytest --lf -x -q --tb=short` |
| One test by node ID | `pytest "tests/test_convert.py::test_eur_conversion" -q` (parametrized: `...::test_x[case-id]`) |
| More detail on one failure | `-vv` for full diffs, `-l` for local variables, `--tb=long` |
| See print output | `-s` (disables capture) |
| See fixture setup and teardown order | `--setup-show` |
| What would run, without running it | `--collect-only -q` |
| Slowest tests | `--durations=10` |
| Turn off a plugin while isolating a problem | `-p no:randomly`, `-p no:cacheprovider`, `-n0` for xdist, `--no-cov` for pytest-cov |

`--pdb` and `--trace` open an interactive debugger, which needs a person at the terminal; as an agent, use `-l`, `-vv`, and targeted
prints with `-s` instead. Pipe long output through `tail -n 80` or use `-q --tb=short`, and look at the first failure before the
rest; later failures are often the same cause.

## Find the Cause

**Assertion failures:** decide whether the code or the expectation is wrong before changing either. Check the expectation against
the docstring, the requirement, or the test's history (`git log -p` on the test). Change an expected value only when you can say why
the old one was wrong.

**Collection errors:** an `ImportError` usually means a missing dependency, an uninstalled project (run it the way the project does
so the package is installed), or a test importing a helper that is not importable under the configured import mode. "import file
mismatch" means two test files share a basename under the default `prepend` import mode; rename one or add `__init__.py` files to
make the test directories packages.

**Warnings turned into errors:** under `filterwarnings = ["error"]`, a deprecation from a dependency upgrade fails tests that did
nothing wrong. Fix the call if it is the project's own; otherwise add a narrow `ignore:` entry with a reason (see the pytest-setup
skill, if installed).

## Passes Alone, Fails in the Suite

This is almost always state leaking from an earlier test, the polluter, into a later one, the victim. Reproduce it before fixing
anything:

1. Confirm the victim passes alone and fails in the full run. With pytest-randomly installed, note the printed seed and use
   `--randomly-seed=<seed>` to replay the failing order, or `-p no:randomly` for file order.
2. Find the polluter. Run the victim after each earlier test file, `pytest tests/test_admin.py tests/test_convert.py::test_eur`,
   halving the list until one file and then one test remains. Two tests, polluter then victim, is the reproduction.
3. Read the polluter for what it changes and does not restore: module-level dicts, lists, and caches (`functools.cache` needs
   `cache_clear()`), class attributes, singletons, `os.environ` written directly, the working directory, logging configuration,
   registries, monkeypatching done by plain assignment, files outside `tmp_path`, or rows left in a shared database.
4. Fix it at the source. Make the polluter clean up after itself: `monkeypatch.setattr`, `monkeypatch.setenv`, a `yield` fixture
   that restores the state, or a fresh object per test. If many tests change the same global, add a fixture in the nearest
   `conftest.py` that resets it, and request it explicitly or make it autouse only for that directory.
5. Verify: the polluter-then-victim pair passes, the victim alone passes, the whole suite passes, and the order reversed or
   randomized passes too.

Never fix order dependence by renaming files to change the order, marking the victim `skip` or `xfail`, or adding
pytest-rerunfailures.

**The reverse, fails alone but passes in the suite,** means the victim depends on setup some earlier test happens to do. Make the
dependency explicit as a fixture the victim requests.

## Flaky: Fails Sometimes

- **Measure it.** Run the test in a loop until it fails
  (`for i in $(seq 30); do pytest "<nodeid>" -q -p no:randomly || break; done`) so you know the failure rate and can tell when a fix
  has worked.
- **Randomness:** seed it, or use the pytest-randomly seed. Hypothesis failures print a seed and a `@reproduce_failure` blob.
- **Time:** tests that read the real clock fail around midnight, month ends, and DST changes, or in another timezone. Freeze or
  inject the clock.
- **Timing and async:** a fixed `sleep` racing real work belongs to the `software-testing:condition-based-waiting` skill.
- **Floating point:** compare with `pytest.approx`.
- **Set and dict ordering, hash randomization:** compare sorted values or sets, not ordered output.

## Only Under `xdist`, Only in CI

**xdist:** tests run in several processes in an order you do not control. Reproduce with the same worker count (`-n 4`) and compare
with `-n0`. The usual causes are shared files, ports, or database names; give each test its own with `tmp_path`, port 0, or the
`worker_id` fixture. Session fixtures run once per worker, not once per run. Keep tests that must share one resource together with
`@pytest.mark.xdist_group` and `--dist loadgroup`.

**CI only:** reproduce with the CI command in a clean environment. List what differs: Python version, operating system (path
separators, case sensitivity, line endings, missing `SIGALRM` on Windows), timezone and locale, environment variables (`CI` is set,
and pytest 9 changes its output in CI mode), installed package versus source checkout, parallelism, and files that exist only on
your machine because they are gitignored.

## Hangs

Find the stuck test with `pytest-timeout` (`--timeout=60` prints every thread's stack when the limit is hit) or with
`faulthandler_timeout = 60` in the config. The `PYTEST_CURRENT_TEST` environment variable names the running test in a process
listing. Common causes: waiting on an event or queue with no timeout, a subprocess waiting for input, a deadlock between threads, or
a real network call.

## Nothing or Too Little Collected

Exit code 5, or a collected count lower than the number of tests in the files, means pytest is looking in the wrong place or for the
wrong names. Compare `pytest --collect-only -q | tail -n 1` with a count of `def test_` in the test directory, then check:

- `testpaths` names the directory that exists (pytest 9 warns "No files were found in testpaths" and falls back to the current
  directory).
- `python_files` matches the file names: the default is `test_*.py` and `*_test.py`; a custom value replaces both.
- `python_functions` and `python_classes` match; a `Test` class with an `__init__` is skipped with a warning.
- A `-k` or `-m` filter in `addopts` or the CI command does not exclude everything.
- `norecursedirs` or `--ignore` does not exclude the test directory.

Fix the configuration to match the files, not the files to match the configuration. The naming the tests already use is the team's
convention, even when it differs from yours: if most files are `*_test.py`, a `python_files` that allows only `test_*.py` is the
bug. Usually the fix is to delete a custom `python_files` so the default (which accepts both styles) applies. Rename only the
outliers that fit neither pattern, such as a file named for what it checks rather than as a test, to the style their neighbors use.
Renaming every file churns history and overrides a choice that was not yours to make. Then verify that every test function in the
directory is collected, not just more of them.

## Report

Tell the user the root cause in one or two sentences, the reproduction (the exact commands and what they showed), the fix and why it
addresses the cause, and the verification runs. If you found a real bug in the code under test, say so and ask before changing
behavior the tests did not ask about.
