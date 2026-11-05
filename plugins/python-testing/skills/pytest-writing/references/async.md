# Async Tests

Patterns for async tests with pytest-asyncio 1.x and the AnyIO pytest plugin. Read the "Async Tests" section of the skill first for
the mode rules.

## Contents

- [Event Loop Scope](#event-loop-scope)
- [AnyIO and Trio](#anyio-and-trio)
- [Faking Async HTTP](#faking-async-http)
- [Cleaning up Async Resources](#cleaning-up-async-resources)
- [Asserting Concurrency](#asserting-concurrency)
- [Timeouts and Hangs](#timeouts-and-hangs)

## Event Loop Scope

Each test gets a fresh event loop by default, which is the most isolated choice and the right default. Share a loop only when an
async fixture with a wider scope (a module-scoped connection pool) must run on the same loop as the tests that use it:

```python
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def pool():
    pool = await create_pool(DSN)
    yield pool
    await pool.close()


@pytest.mark.asyncio(loop_scope="module")
async def test_query(pool):
    assert await pool.fetchval("select 1") == 1
```

Tests on a shared loop still run one at a time; sharing gives no concurrency. Keep neighboring tests in a module on the same loop
scope. The `event_loop` fixture was removed in pytest-asyncio 1.0; do not request or override it.

## AnyIO and Trio

The AnyIO plugin ships with `anyio`. Mark tests with `@pytest.mark.anyio`. By default each test runs once per backend; to run only
on asyncio, override the backend fixture in the root `conftest.py`:

```python
@pytest.fixture
def anyio_backend():
    return "asyncio"
```

A wider-scoped async fixture needs an `anyio_backend` fixture of the same or wider scope. Do not combine `anyio_mode = "auto"` with
pytest-asyncio's `asyncio_mode = "auto"`; keep pytest-asyncio in strict mode in a project that uses both.

## Faking Async HTTP

Inject the HTTP client, then give it a transport that answers in memory. With httpx, `MockTransport` needs no extra dependency and
makes a real request impossible:

```python
def make_client(handler):
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return WeatherClient(http, base_url="https://weather.test/api")


async def test_404_raises_city_not_found():
    client = make_client(lambda request: httpx.Response(404))
    with pytest.raises(CityNotFound):
        await client.current_temp("Atlantis")
```

The handler receives the `httpx.Request`, so a test can record requests and assert on the URL and query parameters it cares about.
`respx` does the same with route matching, and `aioresponses` covers aiohttp. Patching `httpx.AsyncClient.get` is a last resort.

To make sure no test reaches the network by accident, block it at the HTTP library: an autouse fixture that sets
`httpx.AsyncHTTPTransport.handle_async_request` to raise. Do not patch `socket.socket.connect`: on Windows, asyncio builds each
event loop's internal socket pair by connecting over loopback, so the guard breaks every async test there.

## Cleaning up Async Resources

Close what a test opens, or the run ends with "unclosed client session" or "Task was destroyed but it is pending" warnings, which
fail the run under `filterwarnings = ["error"]`. Yield from an async fixture and close after:

```python
@pytest_asyncio.fixture   # plain @pytest.fixture in auto mode
async def http():
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        yield client
```

## Asserting Concurrency

To prove code runs requests concurrently rather than one after another, make the fake wait until all of them have arrived. A
sequential implementation then deadlocks, so bound the wait:

```python
async def test_warmest_fetches_concurrently():
    arrived = 0
    all_in = asyncio.Event()

    async def handler(request):
        nonlocal arrived
        arrived += 1
        if arrived == 3:
            all_in.set()
        await asyncio.wait_for(all_in.wait(), timeout=1)
        return httpx.Response(200, json={"temp_c": len(request.url.params["city"])})

    client = make_client(handler)
    assert await client.warmest(["oslo", "lima", "lisbon"]) == "lisbon"
```

`httpx.MockTransport` accepts an async handler when used with `AsyncClient`. Never assert on elapsed wall-clock time; it is slow and
flaky.

## Timeouts and Hangs

An `await` that never completes hangs the whole run. Wrap waits on events or queues in `asyncio.wait_for(..., timeout=...)` (or
`anyio.fail_after`), and rely on pytest-timeout as the backstop when the project has it. For waiting on a condition, see the
`software-testing:condition-based-waiting` skill.
