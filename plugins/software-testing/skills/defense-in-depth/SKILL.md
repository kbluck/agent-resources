---
name: defense-in-depth
description: >
  After finding the root cause of a bug caused by invalid data, make that class of bug structurally impossible by validating at
  each layer the data passes through: entry-point checks, business-logic checks, environment guards for dangerous operations, and
  debug context for forensics, each with its own test. Use this skill whenever a bad value (empty path, null ID, wrong unit,
  out-of-range number) travelled through several layers before failing; a fix guards only one code path; a test or a mock could
  bypass a single check; or an operation can do real damage if given bad input, such as deleting files, running git or shell
  commands, writing outside a temp directory in tests, moving money, or touching production. Also use it when asked to make a
  destructive operation refuse targets outside an allowed root or scope (empty paths, `..`, symlinks, the wrong environment), even
  with no incident behind the request. Not for finding where bad data comes from, or for general form or request validation and
  error handling.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/software-testing/skills/defense-in-depth
  version: 1.0.0
---

# Defense in Depth

When a bug is caused by invalid data, one check at the place you found feels like enough. It rarely is. Another caller, a refactor,
a new code path, or a mock in a test can route around a single check, and the same bug comes back.

Fixing the origin says "this bug is fixed". Checking at each layer the data passes through says "this kind of bug cannot get far".
Different layers catch different mistakes: the entry check catches most callers, the business check catches internal callers that
skip the entry, and the environment guard stops the damage even when both are bypassed.

## Keep It Proportionate

Defense in depth is for data that does real harm when it is wrong. Use all the layers for operations that destroy, publish, or
spend: deleting or writing files, running commands, migrations, payments, emails, anything that touches production. For a display
glitch, fixing the origin and adding a regression test is enough. Match the project's existing error-handling style, and do not wrap
every function in checks.

## The Four Layers

### 1. Entry Point: Reject Invalid Input at the Boundary

Validate where data enters the system or a module's public API: request handlers, CLI argument parsing, public constructors, and
library entry points. Reject with a clear error that names the bad value.

```text
create_project(name, working_directory):
    if working_directory is empty:            fail "working_directory must not be empty"
    if not exists(working_directory):         fail "working_directory does not exist: <value>"
    if not writable(working_directory):       fail "working_directory is not writable: <value>"
```

### 2. Business Logic: Check What This Operation Needs

Inside the system, check that the data makes sense for this specific operation. This layer catches internal callers that never went
through the entry point.

```text
initialize_workspace(project_dir, session_id):
    if project_dir is empty:                  fail "project_dir required to initialize a workspace"
```

### 3. Environment Guards: Refuse Dangerous Operations in the Wrong Context

Right before a dangerous operation, refuse to run it where it should never run. Tests are the classic case: a test should never
initialize a repository, delete a directory, or write a file outside its temp directory.

```text
git_init(directory):
    if running under tests and resolve(directory) is not inside the system temp directory:
        fail "refusing git init outside the temp directory during tests: <directory>"
```

Use the language's real path resolution and comparison (resolve symlinks, normalize case on case-insensitive filesystems) rather
than a string prefix check, so `/tmp-evil` does not pass as inside `/tmp`. Detect the test context the way the project does: an
environment variable the test runner sets, a configuration flag, or an injected setting.

### 4. Debug Context: Capture What You Will Need Next Time

Log the context just before the dangerous operation, at debug level: the arguments, the working directory, relevant environment, and
the stack. If a future bug gets past every check, this log shows how.

```text
git_init(directory):
    log.debug("git init", directory, cwd, stack)
```

## Applying the Pattern

1. **Trace the data flow.** Find where the bad value originates and every place it is used.
2. **List the checkpoints.** Write down each layer the value passes through on its way to the failure.
3. **Fix the origin first**, with a failing test.
4. **Add a check at each layer that matters**, using the four layers above as the menu.
5. **Test each layer on its own.** Call the inner layer directly, bypassing the entry point, and confirm it still rejects the bad
   value. A guard that no test has seen fire is a guess.

## Testing Guards Without Risk

A test that proves a guard refuses a dangerous path will, before the guard exists or if it ever breaks, perform the very operation
it is meant to prevent. Written test-first, the red run of "refuses to delete the current directory" deletes the current directory.

- **Replace the destructive call in refusal tests.** Patch `rmtree`, the delete, the command runner, or the payment client with a
  recorder, and assert that it was never called and that the guard raised. A missing guard then fails the test instead of doing
  damage.
- **Point real operations only at disposable targets.** Tests that let the operation run for real (the normal, allowed path) use the
  framework's temp directory, a throwaway database, or a sandbox account.
- **Never aim a real call at the current directory, the home directory, the filesystem root, or a real checkout**, even in a test
  you expect to be refused. Use paths inside a temp directory that stand in for them (a temp "checkout" that the test makes the
  current directory), or patch the destructive call as above.

## Example

**Bug:** an empty project directory made `git init` run in the source tree during tests.

**Data flow:** test setup produced `""`, then `Project.create(name, "")`, then `WorkspaceManager.create_workspace("")`, then
`git init` ran in the current directory.

| Layer | Check added | What it caught in testing |
| :---- | :---------- | :------------------------ |
| Entry | `Project.create` rejects an empty, missing, or unwritable directory | Most callers |
| Business | `WorkspaceManager` rejects an empty project directory | A second code path that skipped `Project.create` |
| Environment | `git init` refuses to run outside the temp directory under tests | A mocked `Project` that bypassed both checks |
| Debug | Stack and cwd logged before `git init` | A platform-specific path that resolved differently |

Each layer caught a case the others missed. After all four, the bug could not be reproduced.
