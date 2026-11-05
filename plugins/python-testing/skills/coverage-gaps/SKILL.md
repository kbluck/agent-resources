---
name: coverage-gaps
description: >
  Close gaps in Python test coverage honestly: read Coverage.py's missing lines and partial branches (arrows between line numbers), rank
  them by risk, write tests that check the behavior of the code that matters, exclude only code that genuinely cannot run under
  test (with exclude_also patterns or a pragma that states its reason), and check new code with diff-cover and assertion strength
  with mutation testing. Use this skill whenever coverage is below a fail_under gate or a target, a pull request lowers coverage,
  the user asks to raise, improve, or reach some percentage of coverage, asks what is untested, or asks to add "# pragma: no cover"
  or exclusions, even if they only say "CI fails on coverage". Not for setting up or repairing coverage measurement itself (use
  coverage-config) or the style of the tests you write (pytest-writing).
compatibility: >
  Written against Coverage.py 7.17.2. The bundled script needs only Python 3.10 or later and reads any Coverage.py JSON report,
  grouping gaps by function when the report includes function data.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/python-testing/skills/coverage-gaps
  version: 1.0.0
---

# Closing Coverage Gaps

Coverage shows which code the tests did not run. It cannot show that the code they did run was checked: a test that calls a function
and asserts nothing covers every line of it. So the way to raise coverage is to test the behavior the missing lines implement, with
assertions that would fail if that behavior broke. A number reached any other way (pragmas on reachable code, new `omit` entries, a
lower gate, assertion-free tests) makes the report less true and the code no safer.

When the user asks for a shortcut such as "just add `# pragma: no cover` to whatever is missing", do the honest version: test what
can be tested, exclude what truly cannot run, and explain the difference in your report. Hiding real logic from the gate is a
decision for the user to make knowingly, not something to do quietly on their behalf.

## Measure

Run the tests the way the project measures coverage (see the coverage-config skill, if installed, when that is broken or unclear),
then list the gaps with the bundled script, which groups them by file and function and shows the source of each:

```bash
coverage run -m pytest          # or the project's own command, e.g. pytest --cov
coverage json -q -o coverage.json
python scripts/uncovered.py coverage.json
```

`scripts/uncovered.py` is in this skill's directory; run it with any Python 3.10+, from the directory where coverage ran. It needs
no dependencies. `coverage report -m --skip-covered` gives the same information in less readable form. Note the starting total so
you can report before and after.

### Reading the Missing Column

| Entry | Means |
| :---- | :---- |
| `31` | Line 31 never ran |
| `51-54` | Lines 51 through 54 never ran |
| `30->31` | Line 30 ran, but never jumped to line 31: an `if` that was never true, or never false |
| `7->6` | A jump back to line 6 never happened: a loop body that always exited on its first pass |
| `2->exit` | The function was never left from line 2: for example a loop that always returned early and never ran out of items |

A branch whose destination line never ran is shown as the missing line, not as a separate branch.

## Triage Each Gap

| What the missing code is | What to do |
| :----------------------- | :--------- |
| Behavior: validation, error handling, a boundary, a retry, a rollback, a fallback | Write a test. This is most gaps and the reason the gate exists |
| A branch only one platform takes (`sys.platform == "win32"`) | If it is simple selection logic, test it with `monkeypatch.setattr(module.sys, "platform", "win32")`. If it really needs that OS, measure it in a CI job on that OS and combine the data |
| Unreachable by construction: `assert_never(...)`, `raise NotImplementedError` in an abstract method, `@overload` and `Protocol` stubs | Exclude with a project-wide `exclude_also` pattern |
| Debug-only or entry-point glue: `if __name__ == "__main__":`, a `__repr__` used only in debugging | Test it if it has logic; otherwise an `exclude_also` pattern is reasonable |
| Defensive code for a case the callers cannot produce | Ask whether it should exist. If it should, reach it through a fake or injected failure; if not, tell the user |
| Dead code nothing calls | Tell the user and offer to delete it; do not write a test that exists only to call it |

Work in order of risk: money, data loss, security, and error paths in code that talks to the outside world first; cosmetic
`__repr__` methods last.

## Write the Tests

- **Test the behavior, not the line.** "Withdrawing more than the balance plus overdraft raises `InsufficientFunds` and leaves the
  balance unchanged" covers the line and pins down what it is for. Assert on results, state, raised exceptions, and logged messages
  (`caplog`), never just that the code ran.
- **Reach error paths with fakes, not luck.** Pass in a transport that raises `ConnectionError`, a clock that has already expired,
  or a collaborator that fails on its second call. Inject `sleep` or a clock so retry tests run instantly.
- **Cover both sides of a branch** when the partial-branch entry says only one was taken, and the boundary itself: exactly at the
  limit and one past it.
- **Follow the project's test style** and the pytest-writing skill. One test per behavior, parametrized when the cases are a table.
- **Prove each new test can fail.** Break the line it covers (invert the condition, remove the rollback) and watch the test fail,
  then restore it. A test that still passes is covering without checking.

Then run the coverage again, confirm the lines are no longer listed, and confirm the whole suite still passes.

## Excluding Code

Exclusions are for code that cannot run under test, never for code nobody has tested yet. Coverage.py's own documentation puts it
plainly: excluding untested logic just to clear the report hides coverage problems.

Prefer a pattern in `[tool.coverage.report] exclude_also` over scattered pragmas; it states a rule once and applies everywhere:

```toml
[tool.coverage.report]
exclude_also = [
    "(typing\\.)?assert_never\\(",
    "raise NotImplementedError",
    "@(typing\\.)?overload",
    "if __name__ == .__main__.:",
]
```

Always `exclude_also`, never `exclude_lines`, which discards the defaults including `pragma: no cover`. Lines that are only `...`
and `if TYPE_CHECKING:` blocks are excluded by default since Coverage.py 7.10.

When a one-off pragma is the right call, give the reason on the same line:

```python
if sys.platform == "win32":  # pragma: no cover - no Windows runner in CI yet (#212)
```

A pragma on a line that opens a block (`if`, `def`, `class`, `except`) excludes the whole block. `# pragma: no branch` marks a
branch that can only go one way, such as a `while` loop that always exits through `break`.

## When the Gate Still Cannot Be Met Honestly

Stop and report instead of forcing it. List the remaining gaps, why each one is hard to test, and the options: more test
infrastructure, a CI job on another platform, a deliberate exclusion the user approves, or a lower gate the user decides on. Do not
change `fail_under`, `omit`, or the measured `source` yourself to get green.

## New Code and Assertion Strength

- **Patch coverage:** to check only the lines a branch changed, generate XML and compare with the base branch:
  `coverage xml && diff-cover coverage.xml --compare-branch=origin/main --fail-under=100`. In CI, fetch the base branch first
  (`git fetch origin main`), or diff-cover fails with "ambiguous argument". This is the fairest gate for pull requests in a codebase
  whose total is far from where it should be.
- **Mutation testing** answers the question coverage cannot: would a test notice if this line were wrong? mutmut changes the code in
  small ways and reports each change the tests did not catch. Run it on a critical module, not the whole project; set
  `mutate_only_covered_lines = true` under `[tool.mutmut]` to skip code coverage already shows as untested. It needs `fork`, so on
  Windows it runs only under WSL. Treat each surviving mutant as either a missing assertion or an equivalent change.

## Report

Tell the user the coverage before and after (total, and branches if measured), the behaviors you added tests for, every exclusion
you added and its reason, what remains uncovered and why, and any bugs the new tests found. If you declined part of the request,
such as blanket pragmas, say what you did instead and what it would take to do it their way.
