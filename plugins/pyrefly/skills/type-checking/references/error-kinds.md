# Error Kinds and How to Fix Them

The error kinds an agent meets most often when type-checking existing code, with what each usually means and where the fix belongs.
Checked against Pyrefly 1.4 and the [error kinds docs](https://pyrefly.org/en/docs/error-kinds/), which list every kind. Each error
ends with its kind in brackets, for example `[bad-return]`; that slug is also the code for a suppression comment.

- [Environment and imports](#environment-and-imports)
- [Calls](#calls)
- [Returns and assignments](#returns-and-assignments)
- [Attributes and names](#attributes-and-names)
- [Classes and overrides](#classes-and-overrides)
- [Annotations](#annotations)
- [Async](#async)
- [Warnings worth fixing](#warnings-worth-fixing)
- [Kinds that belong to type-coverage](#kinds-that-belong-to-type-coverage)

## Environment and Imports

Fix these first. Each one turns a module into `Any`, which hides errors in the code that uses it.

| Kind | Default | Usual cause | Fix |
| :--- | :------ | :---------- | :-- |
| `missing-import` | error | The package is not installed in the interpreter Pyrefly found, or a first-party module is outside the search path. The full-text message lists every path searched. | Run `pyrefly dump-config <file>` and check the interpreter and site-packages paths. Activate or point at the project's venv, or install the dependency through the project's tooling. For first-party code, fix `search-path` only with the user's agreement. |
| `missing-source-for-stubs` | error | Pyrefly bundles stubs for the package, but the package itself is not installed. Typical when no project venv is found. | Same as `missing-import`: the environment is wrong or the dependency is missing. |
| `missing-source` | ignore | A stubs package (`types-requests`) is installed without the package (`requests`). | Install the package, or remove the unused stubs. |
| `untyped-import` | warn | A third-party package is used without its separate stubs package. With a Pyrefly config present, bundled stubs are not used. | Suggest adding the stubs package (often `types-<name>`) to the dev dependencies. Ask before adding it. |
| `missing-module-attribute` | error | `from pkg import name` where `name` does not exist: a typo, a removed API, or a version mismatch between the code and the installed package. | Fix the import, or check that the installed version is the one the project pins. |
| `implicit-import` | warn | `pkg.sub.thing` used after only `import pkg`. It works only if something else imported `pkg.sub` first. | Add `import pkg.sub`. |

`ignore-missing-imports`, `replace-imports-with-any`, and `replace-untyped-imports-with-any` make import errors disappear by turning
the module into `Any`. They are right for a truly optional dependency or a module that only exists at runtime, and that is a project
decision. Propose the setting with the reason; do not add it to make the check pass.

## Calls

The error is reported at the call. Decide whether the caller is passing the wrong thing or the callee's signature is wrong.

| Kind | Example message | Fix |
| :--- | :-------------- | :-- |
| `bad-argument-type` | ``Argument `Literal['s']` is not assignable to parameter `x` with type `int` in function `f` `` | Usually the caller: convert, parse, or pass the right value. If the callee genuinely accepts more (it works on any `Iterable`, any `str \| Path`), widen the parameter to what the body supports and check its other callers. |
| `missing-argument` | ``Missing argument `b` in function `two` `` | Pass the argument. If it was recently added to the callee, consider whether it should have had a default. |
| `bad-argument-count` | ``Expected 2 positional arguments, got 3 in function `two` `` | Usually a stale call after a signature change. Fix the call. |
| `unexpected-keyword` | ``Unexpected keyword argument `c` in function `two` `` | A renamed or removed parameter. Find the current name in the callee. |
| `no-matching-overload` | ``No matching overload found for function `f` called with arguments: (float)`` | The message names the argument types. Find the one the caller meant and make the argument fit it. If no overload covers a legitimate call, the overloads are incomplete. |
| `not-callable` | ``Expected a callable, got `None` `` | Usually an `X \| None` that is called without a check. Handle the `None` case. |
| `not-iterable` | ``Type `Literal[1]` is not iterable`` | Wrong value, or an `X \| None` iterated without a check. |
| `bad-index` | `Index 2 out of range for tuple with 2 elements` | A tuple declared shorter than it is, or an indexing bug. |
| `bad-typed-dict-key` | Unknown key on a `TypedDict` | A typo, or a key missing from the `TypedDict` definition. |

## Returns and Assignments

| Kind | Example message | Fix |
| :--- | :-------------- | :-- |
| `bad-return` | ``Returned type `int` is not assignable to declared return type `str` `` | Either the function returns the wrong thing on some path, or the return annotation is wrong. Read the callers: if they rely on the annotated type, fix the body; if they already handle what is really returned, fix the annotation. |
| `bad-assignment` | ``` `Literal[1]` is not assignable to `str` ``` | A variable annotated too narrowly for what it holds, or a wrong value. Also raised for reassigning a `Final`. |
| `unbound-name` | ``` `y` may be uninitialized ``` | A name assigned only on some paths. Initialize it before the branch, or make every path assign or exit. This is often a real crash waiting for the untested branch. |
| `unsupported-operation` | ``+` is not supported between `int` and `str` `` | A real bug or an unhandled `None`. Convert explicitly. |
| `read-only` | Assignment to a property without a setter, or a frozen dataclass field | Use the setter, `dataclasses.replace`, or construct a new object. |

## Attributes and Names

| Kind | Example message | Fix |
| :--- | :-------------- | :-- |
| `missing-attribute` | ``Object of class `NoneType` has no attribute `name` `` | The value may be `None`. Handle it: return early, raise a clear error, or give a default. Do not add `assert x is not None` just to quiet the checker. |
| `missing-attribute` | ``Object of class `list` has no attribute `apend` `` | A typo or a wrong type. Fix the name or the value. |
| `missing-attribute` | ``No attribute `joinn` in module `os.path` `` | A typo, or an API from a different version of the library. |
| `missing-attribute` on `self.x` | Attribute set dynamically (`setattr`, a plugin, a metaclass) | If Pyrefly cannot see the assignment, declare the attribute at class level (`x: int`). If it is truly dynamic, suppress with a reason. |
| `unknown-name` | ``Could not find name `Callable` `` | A missing import, often inside an annotation. Add it. |

Objects of type `Any` never raise `missing-attribute`. If you expected an error and see none, the value is probably `Any`.

## Classes and Overrides

| Kind | Usual cause | Fix |
| :--- | :---------- | :-- |
| `bad-override` | A subclass method takes narrower parameters or returns a wider type than the base, breaking substitution. | Make the override accept at least what the base accepts and return at most what the base returns. If the base is wrong, fix the base and check its other subclasses. |
| `bad-override-param-name` | An override renames a parameter that callers can pass by keyword. | Use the base class's parameter name, or make the parameter positional-only in both (`/`). |
| `bad-instantiation` | Instantiating an abstract class or a `Protocol`. | Instantiate a concrete subclass. |
| `bad-class-definition` | Invalid class body, for example duplicate fields or bad `__slots__`. | Follow the message. |
| `invalid-inheritance` | Subclassing something that cannot be subclassed (`Final` class, a non-class). | Follow the message. |

## Annotations

A broken annotation becomes `Any` and causes errors wherever the value is used, so fix these before the errors around them.

| Kind | Usual cause | Fix |
| :--- | :---------- | :-- |
| `invalid-annotation` | Misused special form: `Final` without a value, `ClassVar` outside a class, `ParamSpec` in the wrong place. | Follow the message. |
| `not-a-type` | A value used where a type is expected, often a variable alias without `TypeAlias`. | Use the class, or declare the alias. |
| `invalid-type-var` | A `TypeVar` used in a way the scoping rules do not allow. | Follow the message. |
| `bad-specialization` | Wrong number or kind of type arguments, for example `dict[int]`. | Give the right arguments. |

## Async

| Kind | Example message | Fix |
| :--- | :-------------- | :-- |
| `unused-coroutine` | ``Result of async function call is unused. Did you forget to `await`? `` | Add `await`. This is a real bug: the call never runs. |
| `not-async` | `async with` or `async for` on a non-async object | Use the sync form, or the async version of the API. |

## Warnings Worth Fixing

These print but do not fail the run by default. Fix them in code you touched; list the rest.

| Kind | What it means |
| :--- | :------------ |
| `deprecated` | A use of something marked `@deprecated`. The message often names the replacement. |
| `redundant-cast` | `cast(T, x)` where `x` is already `T`. Remove the cast. |
| `redundant-condition` | A condition that is always true or false, such as an uncalled function in an `if`. Usually a bug. |
| `implicit-import` | See [Environment and imports](#environment-and-imports). |
| `untyped-import` | See [Environment and imports](#environment-and-imports). |

## Kinds That Belong to `type-coverage`

These are off by default and appear only when the config turns them on (the `strict` preset enables `implicit-any`). Each one is
fixed by adding an annotation, which is coverage work:

`unannotated-return`, `implicit-any`, `implicit-any-parameter`, `implicit-any-attribute`, `implicit-any-empty-container`,
`implicit-any-type-argument`, `implicit-any-lambda`.

If they appear only in the code you changed, annotating what you wrote is part of finishing the change. If they appear across
modules you did not touch, that is a coverage project: tell the user and use `type-coverage`.
