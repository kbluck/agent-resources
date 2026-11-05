# Test Doubles by Language

Syntax for stubs, mocks, spies, and fakes in common frameworks. Use whatever the project already uses; these are starting points,
not recommendations to add a dependency. Read the "Use Test Doubles Carefully" section of the skill first: most tests need fewer
doubles than they have.

## Contents

- [Kinds of Double](#kinds-of-double)
- [Python](#python)
- [JavaScript and TypeScript](#javascript-and-typescript)
- [Rust](#rust)
- [Go](#go)
- [C# and .NET](#c-and-net)
- [Java and Kotlin](#java-and-kotlin)

## Kinds of Double

| Kind | What it does | Prefer it when |
| :--- | :----------- | :------------- |
| Fake | A working lightweight implementation (in-memory repository, fake clock) | You need realistic behavior across several calls |
| Stub | Returns canned answers | The test needs a dependency to return something specific |
| Spy | Records calls to a real or stub object | The call itself is the behavior, such as "sends one email" |
| Mock | Pre-programmed with expectations that fail the test if unmet | Rarely; outcomes are usually the better assertion |

A hand-written fake behind an interface you own is often clearer and less brittle than any mocking library.

## Python

`unittest.mock` ships with the standard library. Patch where the name is looked up, not where it is defined.

```python
from unittest.mock import AsyncMock, Mock, call, patch

# Stub a return value, or a sequence, or an exception
client = Mock()
client.fetch.return_value = {"data": "test"}
client.fetch.side_effect = [1, 2, 3]
client.fetch.side_effect = TimeoutError("upstream")

# Patch for one test; patch "app.signup.send_email", where signup imports it
@patch("app.signup.send_email")
def test_signup_sends_welcome_email(send_email):
    signup("test@example.com")
    send_email.assert_called_once_with("test@example.com", subject="Welcome")

# Async
@patch("app.checkout.charge", new_callable=AsyncMock)
async def test_checkout_records_payment_id(charge):
    charge.return_value = {"id": "ch_123"}
    result = await checkout(cart)
    assert result.payment_id == "ch_123"

# Keep mocks honest: autospec rejects calls the real signature would reject
@patch("app.signup.send_email", autospec=True)
def test_signup_with_autospec(send_email): ...
```

With pytest, `monkeypatch.setattr`, `monkeypatch.setenv`, and the `tmp_path` fixture cover many cases without a mock object, and
undo themselves after the test.

## JavaScript and TypeScript

Vitest and Jest share nearly the same API (`vi` in Vitest, `jest` in Jest).

```typescript
import { beforeEach, expect, test, vi } from "vitest";

// Mock a module; hoisted above imports
vi.mock("./email", () => ({ sendEmail: vi.fn().mockResolvedValue(true) }));
import { sendEmail } from "./email";

test("signup sends a welcome email", async () => {
  await signup("test@example.com");
  expect(sendEmail).toHaveBeenCalledWith("test@example.com", expect.any(String));
});

// Stub values per call, async results, and failures
const fetchUser = vi.fn()
  .mockReturnValueOnce({ id: 1 })
  .mockResolvedValueOnce({ id: 2 })
  .mockRejectedValueOnce(new Error("fail"));

// Spy on a real method, then restore it
const spy = vi.spyOn(user, "getName");
user.getName();
expect(spy).toHaveBeenCalled();

// Fake timers for code that uses setTimeout, setInterval, or Date
vi.useFakeTimers();
vi.advanceTimersByTime(1000);
vi.useRealTimers();

beforeEach(() => {
  vi.restoreAllMocks(); // restore spies; clearAllMocks only resets call history
});
```

For HTTP, intercepting at the network layer (for example with MSW) keeps the real client code under test.

## Rust

Rust favors traits as seams. A hand-written fake is often enough; `mockall` generates mocks when it is not.

```rust
#[cfg_attr(test, mockall::automock)]
trait UserStore {
    fn get_user(&self, id: u32) -> Option<User>;
}

#[test]
fn profile_uses_stored_name() {
    let mut store = MockUserStore::new();
    store.expect_get_user()
        .with(mockall::predicate::eq(1))
        .times(1)
        .returning(|_| Some(User { id: 1, name: "Test".into() }));

    let profile = get_user_profile(&store, 1);
    assert_eq!(profile.name, "Test");
}
```

Pass dependencies as generics or `&dyn Trait` so tests can substitute them. Use `tempfile` for filesystem tests.

## Go

Go tests usually use small interfaces and hand-written fakes rather than a mocking library.

```go
type Mailer interface {
    Send(to, subject string) error
}

type fakeMailer struct {
    sent []string
    err  error
}

func (f *fakeMailer) Send(to, subject string) error {
    f.sent = append(f.sent, to)
    return f.err
}

func TestSignupSendsWelcomeEmail(t *testing.T) {
    mailer := &fakeMailer{}
    if err := Signup(mailer, "test@example.com"); err != nil {
        t.Fatal(err)
    }
    if len(mailer.sent) != 1 || mailer.sent[0] != "test@example.com" {
        t.Fatalf("sent = %v, want one email to test@example.com", mailer.sent)
    }
}
```

`httptest.NewServer` stands up a real local HTTP server for client tests. `t.TempDir()` and `t.Setenv()` clean up automatically. If
the project uses `gomock` or `testify/mock`, follow its existing patterns.

## C# and .NET

Moq and NSubstitute are the common libraries; both mock interfaces and virtual members only.

```csharp
// Moq
var mailer = new Mock<IMailer>();
mailer.Setup(m => m.SendAsync("test@example.com", It.IsAny<string>())).ReturnsAsync(true);

await new SignupService(mailer.Object).SignupAsync("test@example.com");

mailer.Verify(m => m.SendAsync("test@example.com", It.IsAny<string>()), Times.Once);

// NSubstitute
var mailer = Substitute.For<IMailer>();
mailer.SendAsync(default!, default!).ReturnsForAnyArgs(true);
await new SignupService(mailer).SignupAsync("test@example.com");
await mailer.Received(1).SendAsync("test@example.com", Arg.Any<string>());
```

Inject `TimeProvider` (.NET 8 and later) and use `FakeTimeProvider` from `Microsoft.Extensions.TimeProvider.Testing` to control
time. For ASP.NET Core, `WebApplicationFactory` runs the real pipeline in memory.

## Java and Kotlin

Mockito is the common library in Java; MockK is idiomatic in Kotlin.

```java
// Mockito with JUnit 5
@ExtendWith(MockitoExtension.class)
class SignupServiceTest {
    @Mock Mailer mailer;

    @Test
    void signupSendsWelcomeEmail() {
        when(mailer.send(eq("test@example.com"), anyString())).thenReturn(true);

        new SignupService(mailer).signup("test@example.com");

        verify(mailer, times(1)).send(eq("test@example.com"), anyString());
    }
}
```

```kotlin
// MockK
val mailer = mockk<Mailer>()
every { mailer.send("test@example.com", any()) } returns true
SignupService(mailer).signup("test@example.com")
verify(exactly = 1) { mailer.send("test@example.com", any()) }
```

Inject a `java.time.Clock` to control time. Testcontainers runs real databases and brokers for integration tests.
