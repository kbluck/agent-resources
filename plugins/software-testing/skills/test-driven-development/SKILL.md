---
name: test-driven-development
description: >
  Build features and fix bugs test-first with red-green-refactor: write one failing test, watch it fail for the right reason,
  write the least code that makes it pass, then refactor while green. Use this skill whenever you implement a feature, add a
  function or endpoint, change behavior, fix a bug, or refactor or break up code without changing what it does, in any language,
  even if the user never says
  "TDD" or "test first". Also use it when the user asks for TDD, a regression test, or a failing test that reproduces a bug, and
  whenever you catch yourself writing production code before a test that exercises it. Not for how to write a good individual
  test, mocks, or fixtures (use the best-practices skill), or for investigating a failure whose cause is still unknown.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/software-testing/skills/test-driven-development
  version: 1.0.0
---

# Test-Driven Development

Write the test first. Watch it fail. Write the least code that makes it pass. Then clean up.

The reason for the order is evidence. A test you watched fail, for the reason you expected, has proven it can detect the missing
behavior. A test written after the code usually passes on its first run, and a test that has only ever passed has proven nothing: it
might be asserting on the wrong thing, or not running at all.

So the rule is: **no production code without a failing test that demands it.** If you notice you have written code first, set it
aside, write the test, watch it fail against the code without your change, then bring the code back.

The project's test conventions win over anything here. If the user explicitly asks you to skip tests or work another way, do what
they ask and mention what is left untested.

## Start with a Test List

Before the first test, write down the behaviors the request implies, one line each: every rule it states, then the edge cases those
rules raise (empty input, boundaries, invalid input, and the awkward members of each category, such as letters that have no simple
ASCII form when the rule is "accented letters become ASCII"). The best-practices skill has a checklist of edges. Work through the
list one cycle at a time, adding to it as you discover cases. Anything you decide not to handle, tell the user.

## The Cycle

```text
   RED                 GREEN                 REFACTOR
   write one     -->   write the least  -->  clean up with     --+
   failing test        code to pass          tests still green   |
     ^                                                           |
     +-----------------------  next behavior  <------------------+
```

### Red: Write One Failing Test

Write a single test for the next small piece of behavior. Small means one rule, one case, one branch: "rejects an empty email", not
"validates the form".

- Name it for the behavior, so the name reads as a requirement.
- Use real code; reach for a double only for something slow, nondeterministic, or external. See the best-practices skill.
- Assert on the outcome a caller would observe.

### Verify Red: Watch It Fail

Run just that test with the project's runner. Do not skip this step; it is the whole point of writing the test first.

Confirm three things:

1. **It fails**, not passes. A test that passes before the change is not testing the change. Either the behavior already exists, or
   the test is wrong.
2. **It fails on the assertion**, not with an import error, a typo, or a missing fixture. Those failures prove nothing about the
   behavior. In compiled languages, add the minimal stub (signature only, returning a default) so the test compiles, then run it
   again to see the assertion fail.
3. **The failure message says what you expected**: the expected value against the actual one, or the error that should have been
   raised.

### Green: Write the Least Code That Passes

Write the simplest code that makes this test pass. Hard-coding a return value is acceptable when it is genuinely the simplest thing;
the next test will force the general solution. Do not add features, options, or error handling that no test asks for yet.

### Verify Green: Watch It Pass

Run the test again and confirm it passes. Then run the surrounding file or module, and the whole suite at natural checkpoints, to
confirm nothing else broke. The output should be clean, with no new warnings or noise.

### Refactor: Tidy While Green

Only with every test passing: remove duplication, improve names, extract helpers, simplify. Run the tests after each change. Do not
add behavior during refactoring; new behavior starts with a new red test.

Then pick the next behavior and go around again.

## Bug Fixes Start with a Reproduction

For a bug, the first red test is one that reproduces it:

1. Write a test that exercises the reported scenario and asserts the correct behavior.
2. Run it and confirm it fails *the way the bug report describes*. If it passes, you have not reproduced the bug yet; keep narrowing
   the test before touching the code.
3. Fix the code and watch the test pass.
4. Keep the test. It is the regression test that stops the bug coming back.

If you do not yet understand why the bug happens, find the cause first, then return here to write the reproduction.

## Refactoring Existing Code

Refactoring changes structure without changing behavior, so the tests come first in a different way: make sure the behavior you are
about to move is covered *before* you move it. If it is not, add characterization tests that pin down what the code does today, and
check they pass. Then refactor in small steps, running the tests after each one.

## When Test-First Gets Hard

| Situation | What to do |
| :-------- | :--------- |
| You do not know what the design should be | Spike in a scratch branch or file to learn, then discard it and rebuild test-first |
| The code is hard to test (globals, hidden I/O, no seams) | Write a higher-level test around it first, then introduce a seam so a unit test can reach it |
| Pure layout, styling, or generated code | Test-first adds little; verify it another way and say so |
| Configuration or build changes | The "test" may be running the build or the app; still watch it fail before and pass after |
| An existing test suite is already red | Do not build on a red baseline. Report the failures and ask before continuing |

## Rationalizations to Catch

| You think | Reality |
| :-------- | :------ |
| "Too simple to need a test" | Simple code breaks too, and the test takes a minute |
| "I'll write the tests after" | Tests written after pass on the first run and prove nothing until you break the code to check them |
| "I already tested it by hand" | A manual check leaves no record and cannot be re-run on the next change |
| "TDD will slow me down" | It is slower than skipping tests and faster than debugging what skipping them produced |
| "Just this once" | The cases that feel safe to skip are the ones you thought least about |

Stop and restart the cycle if any of these happen: you wrote code before its test, a new test passed on its first run, you cannot
explain why a test failed, or you are adding behavior during a refactor.

## Before You Finish

- [ ] Every new behavior has a test, and you saw each one fail before the code that makes it pass existed.
- [ ] Each test failed on its assertion, with the message you expected.
- [ ] The code is no more general than the tests require.
- [ ] The whole suite passes in a fresh run, with clean output.
