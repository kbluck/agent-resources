---
name: best-practices
description: >
  Write and improve automated tests that would actually fail if the behavior they cover broke, in any language or framework. Use
  this skill whenever you write, add, extend, or review unit, integration, or end-to-end tests; set up test infrastructure,
  fixtures, factories, or test data; decide what to test, which test level fits, or how much coverage is enough; add mocks, stubs,
  fakes, or spies; or are tempted to add a test-only method to production code. Also use it when tests pass but prove nothing,
  assert on mocks, depend on each other or on run order, or are hard to read. Not for the red-green-refactor order of work (use
  the test-driven-development skill), flaky or timing-dependent tests (use condition-based-waiting), or diagnosing why an existing
  test fails.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/software-testing/skills/best-practices
  version: 1.0.0
---

# Testing Best Practices

A test is worth keeping only if it would fail when the behavior it covers breaks. Everything here serves that goal: tests that check
real behavior, fail for one clear reason, run in any order, and read like a description of what the code is supposed to do.

The project's own test conventions always win over the defaults here. If it has a test style guide, a fixture library, a naming
scheme, or a preferred mocking tool, use it.

## Before You Write a Test

Find out how the project tests today, so new tests fit in and run where the others run:

- **Framework and runner.** Look at the dependency manifest, build files, CI config, and existing test files. Use the same
  framework, assertion style, and helpers.
- **Layout and naming.** Note where tests live (next to the code, a `tests/` tree, a separate project) and how files and test
  functions are named.
- **The command.** Learn how to run one test, one file, and the whole suite. You will run all three.
- **Shared helpers.** Look for existing fixtures, factories, builders, and fakes before writing new ones.

## Choose the Level

Write the cheapest test that can catch the bug you care about. Most tests should be fast unit tests, fewer should be integration
tests, and only critical user journeys need end-to-end tests.

| Level | Covers | Speed | Use it for |
| :---- | :----- | :---- | :--------- |
| Unit | One function, class, or module, with its collaborators real or faked | Milliseconds | Logic, calculations, parsing, validation, state machines, edge cases |
| Integration | Several real components together: code plus database, filesystem, queue, or HTTP layer | Seconds | Queries, serialization, wiring, configuration, contracts between components |
| End-to-end | The whole system through its real interface | Slow | A few critical paths, such as sign-up, checkout, or a CLI's main command |

A bug found by an end-to-end test that a unit test could have caught is a sign of a missing unit test. A unit test that mocks so
much it no longer touches real behavior is a sign that the test belongs one level up.

## Structure Each Test

**Arrange, act, assert.** Set up the inputs and collaborators, do one thing, then check the outcome. Keep the three parts visually
distinct; a blank line between them is enough.

```text
arrange:  cart = Cart(items = [Item(price = 10), Item(price = 5)])
act:      total = cart.total(discount_percent = 10)
assert:   total == 13.50
```

**One behavior per test.** Several assertions are fine when they describe one outcome. When a test checks two unrelated behaviors,
the first failure hides the second and the name cannot describe both.

**Name the behavior, not the method.** A failing test's name should tell the reader what broke without opening the file. Follow the
project's convention; if there is none, use the idiom of the language:

| Style | Example |
| :---- | :------ |
| `test_<unit>_<condition>_<expected>` (Python, Rust) | `test_checkout_empty_cart_raises_error` |
| Sentence (JavaScript, TypeScript, Kotlin) | `it("rejects an empty cart at checkout")` |
| `Method_Condition_Expected` (C#, Java) | `Checkout_EmptyCart_Throws` |
| `TestUnit_Condition` with subtests (Go) | `TestCheckout/empty_cart_returns_error` |

**Assert on observable results.** Check return values, persisted state, emitted events, output, and errors. Avoid asserting on
private fields, call order between internal helpers, or log text that nobody depends on. Those break on every refactor and do not
catch real bugs.

**Make failures readable.** Prefer the framework's specific assertions (equality with a diff, collection contains, raises with a
message match) over a bare boolean check, so a failure says what was expected and what arrived.

## Decide What to Test

| Test | Skip |
| :--- | :--- |
| Business rules and calculations | The framework, the standard library, and third-party libraries |
| Edge cases and boundaries | Trivial getters, setters, and pass-through code |
| Error handling and failure paths | Generated code |
| Public interfaces and contracts | Private implementation details |
| Every bug that was fixed, as a regression test | External services directly (test your adapter against a fake or a contract) |

Cover the happy path first, then the error paths, then the edges. For edges, walk this list for every input:

- Empty, missing, or null
- One item, and many
- The boundaries: zero, negative, maximum, just inside and just outside each limit
- Malformed or wrong-type input
- Duplicates, ordering, and Unicode where text is involved
- Concurrency or repeated calls where the code has state

When several cases share a shape, use the framework's table-driven or parameterized form (`pytest.mark.parametrize`, `test.each`,
`[Theory]` with `[InlineData]`, `@ParameterizedTest`, Go table tests, `rstest`) so each case is one line and reports on its own.

## Keep Tests Independent and Deterministic

Each test must pass alone, in any order, in parallel, and on any machine. Flaky tests teach everyone to ignore red builds.

- Build fresh state in each test or fixture. Do not share mutable objects, globals, or singletons across tests.
- Clean up what you create: temp directories, database rows, environment variables, files. Prefer the framework's temp-directory and
  teardown support, which cleans up even when the test fails.
- Control time, randomness, and the environment. Inject a clock, seed the random generator, and set environment variables inside the
  test with automatic restore.
- Never depend on the network, the current date, the local timezone, or files outside the repository unless the test exists to check
  exactly that.
- For anything asynchronous, wait for the condition, not a fixed delay. See the condition-based-waiting skill.

## Use Test Doubles Carefully

Mocks, stubs, fakes, and spies isolate the code under test from things that are slow, nondeterministic, or outside your control.
They are a means to isolate, never the thing being tested.

| Replace with a double | Keep real |
| :-------------------- | :-------- |
| External HTTP APIs, payment, email, SMS | The code under test |
| Time, randomness, UUIDs | Pure functions and simple value objects |
| Slow or costly resources in unit tests | Anything cheap and deterministic to construct |
| Failure modes that are hard to trigger for real | The standard library and in-memory collections |

Before mocking anything, answer three questions:

1. What side effects does the real dependency have?
2. Does this test depend on any of them?
3. Can I use the real thing, an in-memory fake, or a test container instead?

If you are unsure, run the test with the real implementation first and mock only the part that is slow or unreachable. Mock at the
boundary you own (your `PaymentGateway` interface), not deep inside a library you do not.

The common failures, each covered with examples in [references/anti-patterns.md](references/anti-patterns.md):

| Anti-pattern | What to do instead |
| :----------- | :----------------- |
| Asserting that a mock exists or was rendered | Assert on the real component's behavior, or remove the mock |
| Adding methods to production code that only tests call | Put the helper in test utilities |
| Mocking a dependency whose side effect the test relies on | Mock one level lower, at the slow part only |
| A partial mock that omits fields downstream code reads | Mirror the real shape completely, ideally from a recorded or typed sample |
| Mock setup longer than the test itself | Move the test up a level or use a fake |
| Asserting on every call made to a mock | Assert on outcomes; verify only the interactions that are the behavior |

Framework syntax for doubles in Python, JavaScript and TypeScript, Rust, Go, C#, and Java is in
[references/test-doubles.md](references/test-doubles.md).

## Build Test Data Deliberately

- **Fixtures** set up shared context (a database session, a temp directory, a configured client). Scope them as narrowly as the cost
  allows, and make them return fresh objects.
- **Factories or builders** create domain objects with sensible defaults and let each test override only what it cares about:
  `make_user(role = "admin")`. Each test then shows the one detail that matters to it.
- Generate unique values (emails, IDs) per test so tests never collide in a shared database.
- Keep large literal payloads in data files next to the tests, not inline.

## Coverage

Coverage measures which lines ran, not whether anything was checked. Aim for meaningful coverage of the logic that matters, not a
percentage. Use a coverage report to find untested branches and error paths, then decide whether each one deserves a test. A
project's own coverage gate, if it has one, still applies.

## Prove the Test Can Fail

A test that has never failed has not shown that it tests anything. After writing a test against existing code:

1. Break the behavior on purpose: invert a condition, return a constant, delete the line under test.
2. Run the test and confirm it fails with a message that points at the break.
3. Restore the code and confirm the test passes.

If the test still passes with the code broken, it is asserting on the wrong thing. When writing new code, the test-driven
development skill gets this for free by writing the test first.

## Before You Finish

- The new tests pass alone, and the whole suite passes with them, run fresh.
- Each new test was seen to fail for the right reason, either first (TDD) or by a deliberate break.
- Names describe behavior, and no test depends on another or on run order.
- No sleeps, network calls, or real clocks slipped in.
- No production code gained a method or flag that only tests use.
- The test output is clean: no new warnings, stray prints, or unhandled-error noise.
