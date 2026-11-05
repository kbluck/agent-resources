# Wait Helpers by Language and Framework

Use the framework's own waiting support when it has one; it already handles retries, timeouts, and readable failures. Write a helper
only when nothing suitable exists, and put it in the project's shared test utilities so every test uses the same one.

## Contents

- [Built-in Waits](#built-in-waits)
- [Fake Clocks](#fake-clocks)
- [Polling Helpers](#polling-helpers)

## Built-in Waits

| Framework | Waiting support |
| :-------- | :-------------- |
| Testing Library (React, Vue, Svelte, DOM) | `await screen.findByText("Loaded")`, `await waitFor(() => expect(...).toBe(...))` |
| Playwright | Web-first assertions retry on their own: `await expect(page.getByText("Saved")).toBeVisible()`; `expect.poll(fn)` for non-UI values |
| Cypress | Queries and assertions retry until the timeout: `cy.contains("Saved").should("be.visible")` |
| Selenium | `WebDriverWait(driver, 10).until(EC.visibility_of_element_located(...))` and the equivalents in each binding |
| Vitest | `await vi.waitFor(() => expect(x).toBe(1))`, `vi.waitUntil(() => cond)` |
| Java | Awaitility: `await().atMost(Duration.ofSeconds(5)).until(() -> job.isDone())` |
| Kotlin coroutines | `runTest` with virtual time; `withTimeout` around a suspending wait |
| Python asyncio | `await asyncio.wait_for(event.wait(), timeout=5)` |
| Go | `testify/assert.Eventually(t, cond, 5*time.Second, 10*time.Millisecond)`; channels with `select` and `time.After` |
| .NET | `await task.WaitAsync(TimeSpan.FromSeconds(5))`; `TaskCompletionSource` as a signal |
| Rust (Tokio) | `tokio::time::timeout(Duration::from_secs(5), rx.recv()).await` |

## Fake Clocks

For code whose behavior depends on time, control the clock instead of waiting for it.

| Environment | Fake clock |
| :---------- | :--------- |
| Jest, Vitest | `jest.useFakeTimers()` / `vi.useFakeTimers()`, then `advanceTimersByTime(ms)` |
| Python | `freezegun` or `time-machine` for wall-clock time; inject a clock for `time.monotonic` |
| .NET 8 and later | Inject `TimeProvider`; use `FakeTimeProvider.Advance(...)` in tests |
| Java | Inject `java.time.Clock`; use `Clock.fixed` or a mutable test clock |
| Go | Inject a clock interface, or use `testing/synctest` (Go 1.25 and later) for virtual time in goroutines |
| Rust (Tokio) | `#[tokio::test(start_paused = true)]` and `tokio::time::advance(...)` |

## Polling Helpers

Each helper re-evaluates the condition on every attempt, has a deadline, and fails with a description and the last value seen.

### TypeScript

```typescript
export async function waitFor<T>(
  condition: () => T | undefined | null | false,
  description: string,
  timeoutMs = 5000,
  intervalMs = 20,
): Promise<T> {
  const deadline = Date.now() + timeoutMs;
  let last: unknown;
  while (true) {
    last = condition();
    if (last) return last as T;
    if (Date.now() > deadline) {
      throw new Error(`Timed out after ${timeoutMs} ms waiting for ${description}; last value: ${String(last)}`);
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
```

### Python

```python
import time

def wait_for(condition, description, timeout=5.0, interval=0.02):
    deadline = time.monotonic() + timeout
    while True:
        result = condition()
        if result:
            return result
        if time.monotonic() > deadline:
            raise TimeoutError(f"timed out after {timeout}s waiting for {description}; last value: {result!r}")
        time.sleep(interval)
```

For asyncio code, the same loop with `await asyncio.sleep(interval)`.

### Go

```go
func waitFor(t *testing.T, description string, timeout time.Duration, condition func() bool) {
    t.Helper()
    deadline := time.Now().Add(timeout)
    for !condition() {
        if time.Now().After(deadline) {
            t.Fatalf("timed out after %v waiting for %s", timeout, description)
        }
        time.Sleep(20 * time.Millisecond)
    }
}
```

### C# and .NET

```csharp
public static async Task<T> WaitForAsync<T>(
    Func<T?> condition, string description, TimeSpan? timeout = null, TimeSpan? interval = null)
{
    var limit = timeout ?? TimeSpan.FromSeconds(5);
    var stopwatch = Stopwatch.StartNew();
    while (true)
    {
        var result = condition();
        if (result is not null && !result.Equals(default(T))) return result;
        if (stopwatch.Elapsed > limit)
            throw new TimeoutException($"Timed out after {limit} waiting for {description}; last value: {result}");
        await Task.Delay(interval ?? TimeSpan.FromMilliseconds(20));
    }
}
```

### Rust

```rust
use std::time::{Duration, Instant};

pub fn wait_for<T>(description: &str, timeout: Duration, mut condition: impl FnMut() -> Option<T>) -> T {
    let deadline = Instant::now() + timeout;
    loop {
        if let Some(value) = condition() {
            return value;
        }
        assert!(Instant::now() < deadline, "timed out after {timeout:?} waiting for {description}");
        std::thread::sleep(Duration::from_millis(20));
    }
}
```
