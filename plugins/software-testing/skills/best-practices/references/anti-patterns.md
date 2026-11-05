# Test Anti-Patterns

Tests must verify real behavior, not the behavior of their own mocks. Each pattern below shows the mistake, why it misleads, and the
fix. Examples use TypeScript for concreteness; the same mistakes look the same in any language.

## Contents

- [Testing Mock Behavior](#testing-mock-behavior)
- [Test-Only Methods in Production Code](#test-only-methods-in-production-code)
- [Mocking Without Understanding the Dependency](#mocking-without-understanding-the-dependency)
- [Incomplete Mocks](#incomplete-mocks)
- [Other Smells](#other-smells)

## Testing Mock Behavior

```typescript
// Mistake: the assertion proves the mock rendered, not that the page works.
vi.mock("./Sidebar", () => ({ Sidebar: () => <div data-testid="sidebar-mock" /> }));

test("renders sidebar", () => {
  render(<Page />);
  expect(screen.getByTestId("sidebar-mock")).toBeInTheDocument();
});
```

The test passes as long as the mock exists. It would keep passing if `Page` stopped rendering a working sidebar.

```typescript
// Fix: render the real component and assert on what a user would see.
test("renders sidebar navigation", () => {
  render(<Page />);
  expect(screen.getByRole("navigation")).toBeInTheDocument();
});
```

Before asserting on anything a mock produced, ask: is this checking real behavior, or only that the mock is there? If it is the
mock, delete the assertion or remove the mock.

## Test-Only Methods in Production Code

```typescript
// Mistake: destroy() exists only so tests can clean up.
class Session {
  async destroy() {
    await this.workspaceManager?.destroyWorkspace(this.id);
  }
}
```

The method looks like public API. Someone will call it in production, and it ships code paths that nothing but tests exercise.

```typescript
// Fix: keep cleanup in test utilities, using the public surface.
export async function cleanupSession(session: Session) {
  const workspace = session.getWorkspaceInfo();
  if (workspace) await workspaceManager.destroyWorkspace(workspace.id);
}
```

The same applies to `isTestMode` flags, setters that exist only for injection, and widened visibility "for testing". If a test needs
a seam, add a real one (constructor injection, an interface) that production code also benefits from.

## Mocking Without Understanding the Dependency

```typescript
// Mistake: mocking the config writer removes the write that duplicate detection depends on.
vi.mock("./configWriter");

test("detects duplicate server", async () => {
  await addServer(config);
  await expect(addServer(config)).rejects.toThrow("duplicate"); // never throws
});
```

The mocked module had a side effect the test relied on. The test now fails for a reason that has nothing to do with the code, or
worse, passes for one.

```typescript
// Fix: mock only the slow part, below the behavior under test.
vi.mock("./slowNetworkCall");

test("detects duplicate server", async () => {
  await addServer(config);                                     // config really written
  await expect(addServer(config)).rejects.toThrow("duplicate"); // duplicate really detected
});
```

Before mocking, list the real dependency's side effects and check whether the test needs any of them. When unsure, run the test
against the real implementation first.

## Incomplete Mocks

```typescript
// Mistake: the mock carries only the fields this test looked at.
const response = { status: "success", data: { userId: "123" } };
```

Downstream code reads `metadata.requestId`, so production breaks while the test passes.

```typescript
// Fix: mirror the real shape completely.
const response = {
  status: "success",
  data: { userId: "123", name: "Alice" },
  metadata: { requestId: "req-789", timestamp: 1234567890 },
};
```

Better still, build doubles from the real type (a typed factory, a recorded fixture, a contract test against the real service) so
the compiler or the contract catches drift.

## Other Smells

| Smell | What it usually means |
| :---- | :-------------------- |
| Mock setup is more than half the test | The test belongs at a higher level, or the code needs a simpler seam |
| The test fails when a mock is removed, even though the real dependency works | The test is coupled to the mock, not the behavior |
| Mocking "just to be safe" | Nobody checked whether the real thing was fast and deterministic |
| Assertions on test IDs ending in `-mock` | Testing mock behavior |
| Methods that only test files call | Test-only code in production |
| Production logic duplicated in the test to compute the expected value | The test will share the code's bug; use a literal expected value |
| A test that was written after the code and passed on the first run | Nobody has seen it fail; break the code once to prove it can |
