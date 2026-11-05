---
name: condition-based-waiting
description: >
  Fix flaky and slow tests by replacing fixed sleeps and guessed timeouts with waits for the actual condition: an awaited result or
  signal, a polled condition with a timeout and a clear error, or a fake clock for timing logic. Use this skill whenever a test is
  flaky, intermittent, passes locally but fails in CI or under load, fails when run in parallel or in a different order, times
  out, or contains sleep, setTimeout, Thread.sleep, Task.Delay, time.Sleep, or a hard-coded wait before an assertion; and whenever
  you write a test for asynchronous code, background jobs or queue workers (Celery, Sidekiq, BullMQ), events, file watchers,
  servers starting up, or UI that updates after a delay. Also use it to test time-dependent logic such as debounce, throttle,
  timeouts, retries, or schedules without real waiting, by controlling a fake clock. Works in any language or test framework. Not
  for performance or load testing.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/software-testing/skills/condition-based-waiting
  version: 1.0.0
---

# Condition-Based Waiting

A fixed sleep in a test is a guess about how long something takes. On a fast machine the guess is too long and the suite crawls. On
a loaded CI runner it is too short and the test fails at random. Either way, the test is waiting for the wrong thing.

Wait for the condition you actually care about, not for an amount of time.

## Choose the Right Kind of Wait

Prefer the options higher in this list. Each is more deterministic than the one below it.

| Option | Use it when | Example |
| :----- | :---------- | :------ |
| Await the operation itself | The code returns a promise, future, task, or handle | `await job.run()`, `future.get()`, `task.Wait()`, `thread.join()` |
| Wait on a signal | The code emits an event, callback, or message you can hook | A channel, latch, event, or `once("done")` |
| Fake the clock | The code's behavior depends on time: timeouts, debounce, retries, schedules | Advance a fake clock by the exact interval |
| Poll the condition with a timeout | None of the above is reachable from the test | `wait_for(lambda: job.status == "done", "job to finish")` |
| A fixed delay | Only to let known-periodic behavior happen, after waiting for its trigger | See [When a Fixed Delay Is Right](#when-a-fixed-delay-is-right) |

If the code under test gives the test no way to know it has finished, that is often a design smell worth fixing: return a handle,
emit an event, or accept a callback.

## The Polling Pattern

Most test frameworks already have a waiting helper, and you should use it: see
[references/wait-helpers.md](references/wait-helpers.md) for the built-ins in common frameworks and a small helper in several
languages. A good helper does four things:

```text
wait_for(condition, description, timeout = 5s, interval = 10-50ms):
    deadline = now() + timeout
    loop:
        result = condition()               # re-read fresh state on every check
        if result is truthy: return result
        if now() > deadline:
            fail "timed out after <timeout> waiting for <description>; last value: <result>"
        sleep(interval)
```

- **Re-evaluate every time.** Read the state inside the condition, not into a variable before the loop, or you will poll a stale
  copy forever.
- **Always have a timeout,** generous enough for a slow CI machine (seconds, not milliseconds). The timeout is a safety net, not a
  guess at the expected time; a passing test returns as soon as the condition holds.
- **Fail with a useful message** that says what was awaited and the last value seen.
- **Poll at a sensible interval.** Every 10 to 50 milliseconds is plenty; polling every millisecond wastes CPU and can starve the
  code you are waiting for.

## Common Conditions

| Waiting for | Condition |
| :---------- | :-------- |
| An event | `events.find(e => e.type == "DONE")` |
| A state | `machine.state == "ready"` |
| A count | `queue.length >= 5` |
| A file | `exists(path)`, and for a file still being written, also its expected size or final line |
| A server | A health endpoint returning 200, or the port accepting connections |
| UI text or an element | The framework's find or wait query, which retries until it appears |

## When a Fixed Delay Is Right

Sometimes the behavior under test is itself periodic, and the test needs it to happen a known number of times. A fixed delay is
acceptable when all three hold:

1. The test first waits for the triggering condition (the process started, the subscription is active).
2. The delay is derived from a known interval in the code, not guessed.
3. A comment explains the arithmetic.

```text
wait_for(manager has emitted TOOL_STARTED)
sleep(200ms)  # the tool reports progress every 100 ms; two ticks are needed to see partial output
```

Even then, a fake clock is usually better: advance it by exactly two intervals and the test runs instantly.

## Fixing an Existing Flaky Test

1. **Reproduce the flake.** Run the test many times in a loop, in parallel, and under load (for example, with CPU-heavy work in the
   background). Some runners can repeat a test (`go test -count=100`, `pytest --count=100` with `pytest-repeat`); otherwise run the
   runner in a shell loop. Note the failure rate.
2. **Find what the test is really waiting for.** Read the code around each sleep or timeout and name the condition it stands in for.
3. **Replace the guess** with the strongest option from the table above.
4. **Prove it.** Run the same loop again, under the same load, and confirm zero failures. Report the run counts before and after.

If the flake persists with no timing guesses left, it is probably shared state or test order, not timing. Find the test that leaks
state by bisection: run the failing test alone, then together with each half of the tests that run before it, and keep the half that
makes it fail until one test remains. Fix the leak in that test (restore what it changes), not in the victim.
