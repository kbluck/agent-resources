---
name: pytest-writing
description: >
  Write and review pytest tests for Python code in idiomatic pytest: fixtures with the right scope and yield teardown,
  parametrize with readable ids, pytest.raises with match, approx, tmp_path and monkeypatch for isolation from the real
  environment, test doubles that patch where a name is looked up, and async tests under pytest-asyncio or AnyIO. Use this skill
  whenever you add, extend, or review tests in a Python project that uses pytest, write conftest.py fixtures, test code that reads
  environment variables, files, the home directory, the clock, randomness, or the network, mock a dependency, or test async code,
  even if the user only says "add tests for this module". Builds on software-testing:best-practices for what makes a test worth
  keeping. Not for pytest configuration or plugin setup (use pytest-setup), diagnosing failing or flaky tests (pytest-triage), or
  coverage gaps (coverage-gaps).
compatibility: >
  Requires pytest 8.0 or later; written against pytest 9.2 and pytest-asyncio 1.4. Uses the project's own test runner.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/python-testing/skills/pytest-writing
  version: 1.0.0
---

# Writing `pytest` Tests

This skill is the pytest-specific half of writing good tests. What makes a test worth keeping (it fails when the behavior breaks, it
checks outcomes rather than mocks, it was seen to fail) is in the `software-testing:best-practices` skill, and the
red-green-refactor order of work is in `software-testing:test-driven-development`. Follow those; this skill covers how to express
them in pytest.

The project's existing tests are the style guide. Match their layout, naming, fixture style, and mocking library.

## Before You Write

- **Read the neighbors.** Open the existing tests and every `conftest.py` above the directory you are writing into. Run
  `pytest --fixtures <dir>` to list the fixtures already available, and reuse them before writing new ones.
- **Read the config.** Note `asyncio_mode`, `filterwarnings`, `strict` or `--strict-markers`, the registered markers, and whether
  pytest-mock, Hypothesis, or a snapshot plugin is installed. A test that ignores these fails on its first run.
- **Find the seams.** Note what the code under test reads from outside itself: environment variables, files, the home directory, the
  current time, randomness, the network, module-level state. Each one needs to be controlled by the test, or the test will pass on
  your machine and fail on someone else's.

## Shape

Plain functions and plain `assert`, in files named `test_*.py`. Group related tests in a `class TestThing:` (no `__init__`, no
`TestCase` base) only when the grouping helps. Name tests for the behavior: `test_withdraw_beyond_overdraft_raises`.

A test returns nothing. A test that returns a value gets a `PytestReturnNotNoneWarning` (a failure under
`filterwarnings = ["error"]`), because the value is ignored and was almost always meant to be an `assert`. A test function that
contains `yield` is an error.

## Fixtures

- **Function scope by default.** Widen to `module` or `session` only for something expensive that tests never mutate, such as a
  compiled schema or a read-only data file. Mutable state in a wide fixture leaks between tests.
- **`yield` for teardown.** Code after `yield` runs even when the test fails. Do one state change per fixture, so a failure halfway
  through setup cannot leave the earlier change behind.
- **Factories for variations.** When tests need several objects or one field changed, have the fixture return a builder:

  ```python
  @pytest.fixture
  def make_account():
      def make(owner="ana", balance="0", **overrides):
          return Account(owner, balance=Decimal(balance), **overrides)
      return make
  ```

- **Put shared fixtures in the nearest `conftest.py`**, never in a module the tests import. pytest finds fixtures by name, and
  importing them or `conftest` itself breaks under some import modes.
- **`autouse` only for isolation everyone needs**, such as clearing an environment prefix or blocking the network, and keep it in
  the narrowest `conftest.py` that covers the tests that need it. Anything else should be requested by name, so a reader can see it.
- **No assertions in fixtures.** A failure there reports as an ERROR in setup, not as the test failing.
- Use the `name=` argument, not a leading underscore, when the fixture function name would shadow something.

## Parametrize

Use `@pytest.mark.parametrize` for a table of inputs and expected outputs, in place of a loop of asserts or near-identical copies.
Each case then reports on its own.

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("1", True, id="one"),
        pytest.param(" Yes ", True, id="padded-mixed-case"),
        pytest.param("off", False, id="off"),
    ],
)
def test_parse_bool(raw, expected):
    assert parse_bool(raw) is expected
```

`pytest.param(..., marks=pytest.mark.xfail(reason="#123", strict=True))` marks a single case.

- Give ids whenever the values are objects, long strings, or easy to confuse. Under strict mode duplicate ids are an error.
- Values are passed as they are, not copied. Never put a mutable object in the table that a test might change; build it in the test.
- Pass a list or tuple, never a generator; generators are deprecated as `argvalues` in pytest 9.1.
- Stacked `parametrize` decorators produce every combination. Use that on purpose, not by accident.
- When cases need different setup or assertions, write separate tests.

## Assertions

| Checking | Write |
| :------- | :---- |
| An exception | `with pytest.raises(ValueError, match=r"port out of range: 0"):` around the single statement that raises |
| A float or float collection | `assert total == pytest.approx(29.0)`; pass `abs=` when comparing near zero |
| A warning | `with pytest.warns(DeprecationWarning, match="utcnow"):` |
| An exception group | `with pytest.RaisesGroup(ValueError, TypeError):` (pytest 8.4+) |
| Logging | The `caplog` fixture: `assert "retrying" in caplog.text`, or inspect `caplog.records` |
| Printed output | The `capsys` fixture: `out, err = capsys.readouterr()` |

`match` is a regular-expression search, so wrap literal text containing `.`, `(`, `[`, or `$` in `re.escape`. Use the narrowest
exception type the code promises; `pytest.raises(Exception)` passes for typos and `AttributeError`s too.

Asserts in a helper module lose pytest's detailed failure output unless the module is registered with
`pytest.register_assert_rewrite("tests.helpers")` in the root `conftest.py` before it is imported. Prefer helpers that return a
value the test asserts on.

## Isolation from the Real Environment

These fixtures undo their changes after each test, even when it fails. Use them instead of touching `os.environ`, the working
directory, or module attributes directly.

| Need | Use |
| :--- | :-- |
| A scratch directory | `tmp_path` (a `pathlib.Path`). Never the legacy `tmpdir`, which returns a `py.path` object |
| Set or remove an environment variable | `monkeypatch.setenv("APP_PORT", "8080")`, `monkeypatch.delenv("APP_PORT", raising=False)` |
| Replace a module attribute or constant | `monkeypatch.setattr(loader, "DEFAULT_PATH", tmp_path / "settings.toml")` |
| Change the working directory | `monkeypatch.chdir(tmp_path)` |

For code that reads a family of environment variables, clear the whole family so a value on the developer's machine cannot leak into
the test:

```python
@pytest.fixture(autouse=True)
def clean_app_env(monkeypatch):
    for name in [n for n in os.environ if n.startswith("APP_")]:
        monkeypatch.delenv(name)
```

For code that reads the home directory or a default path, patch the module-level name the code reads (`DEFAULT_PATH`). Pointing
`HOME` (and `USERPROFILE` on Windows) at `tmp_path` helps only when the code calls `Path.home()` at call time; a constant built at
import time already holds the real path. Tests must never read or write the real home directory.

Control time and randomness too. Inject a clock where the code allows it; otherwise use the library the project already has
(`time-machine`, `freezegun`). Seed or inject random generators.

## Test Doubles

Prefer, in order: the real object; a fake the library provides for testing (`httpx.MockTransport`, `respx`, `responses`, an
in-memory database); a small hand-written fake passed in through the constructor; and only then a patch.

When you patch, patch the name **where the code under test looks it up**. If `app/signup.py` does
`from app.email import send_email`, patch `app.signup.send_email`; patching `app.email.send_email` changes nothing the code sees.

| Tool | Use for |
| :--- | :------ |
| `monkeypatch.setattr` | Swapping a function or attribute for a simple stub |
| `mocker` (pytest-mock), if installed | Asserting calls, spies (`mocker.spy`), and automatic cleanup. Do not use `mocker.patch` as a context manager |
| `unittest.mock` | The same, without pytest-mock. Use `patch(..., autospec=True)` or `create_autospec` so a call with the wrong signature fails |
| `AsyncMock` | Awaitable stubs; assert with `assert_awaited_once_with` |

Use `autospec=True` on every `patch`: without it, a mock accepts calls the real function would reject, so a renamed parameter passes
the tests and breaks production. More on when not to mock is in `software-testing:best-practices`.

## Async Tests

Check `asyncio_mode` in the pytest config before writing anything async.

- **`auto` mode:** write `async def test_...` and `async def` fixtures with plain `@pytest.fixture`. No marks are needed.
- **`strict` mode (the default when unset):** mark each async test with `@pytest.mark.asyncio` (or set
  `pytestmark = pytest.mark.asyncio` in the module), and decorate async fixtures with `@pytest_asyncio.fixture`. A plain
  `@pytest.fixture` on an `async def` is not handled in strict mode: the test errors with "requested an async fixture ... with no
  plugin or hook that handled it".
- If `asyncio_default_fixture_loop_scope` is not set, set it to `"function"` in the config (see the pytest-setup skill, if
  installed).

Read [references/async.md](references/async.md) when the tests need a shared event loop, AnyIO or trio, concurrency assertions,
async HTTP fakes, or cleanup of async resources.

## Property-Based and Snapshot Tests

If the project uses Hypothesis, read [references/hypothesis.md](references/hypothesis.md) before writing `@given` tests;
function-scoped fixtures behave differently under it. If it uses syrupy, write `assert result == snapshot`, create snapshots with
`pytest --snapshot-update`, read each new snapshot to confirm it is correct before committing it, and never refresh snapshots to
make a failing test pass without checking why it failed.

## Before You Finish

- Run each new test file alone (`pytest tests/test_loader.py -q`), then the whole suite, with the project's command.
- Show the new tests do not depend on each other or on run order: run them alone and with the suite, and if pytest-randomly is
  installed, run the suite twice (it shuffles on every run).
- Break the code under test once per behavior you claim to cover, and watch a test fail; then restore it.
- No new warnings, no `tmpdir`, no direct `os.environ` writes, no real network, clock, or home directory, and no unregistered
  markers.
