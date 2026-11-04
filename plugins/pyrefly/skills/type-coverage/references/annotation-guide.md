# Annotation Guide

How to write the annotations themselves. Read the section you need.

- [Syntax by Python version](#syntax-by-python-version)
- [Imports](#imports)
- [Callables](#callables)
- [Type variables and generics](#type-variables-and-generics)
- [Decorators and ParamSpec](#decorators-and-paramspec)
- [Narrowing helpers: TypeGuard and TypeIs](#narrowing-helpers-typeguard-and-typeis)
- [Classes and attributes](#classes-and-attributes)
- [Dict shapes, literals, and sentinels](#dict-shapes-literals-and-sentinels)
- [Import cycles and forward references](#import-cycles-and-forward-references)
- [Runtime-evaluated annotations](#runtime-evaluated-annotations)

## Syntax by Python Version

Use the lowest Python version the project supports: `python-version` in the Pyrefly config, else `requires-python` in
`pyproject.toml`. A feature newer than that floor comes from `typing_extensions`, and only if the project already depends on it or
the user agrees to add it. Do not import from `typing_extensions` what `typing` already has at the floor.

| Feature | Example | In `typing` since |
| :------ | :------ | :---------------- |
| Built-in generics (PEP 585) | `list[int]`, `dict[str, Any]` | 3.9 |
| `Annotated` (PEP 593) | `Annotated[int, "px"]` | 3.9 |
| Union syntax (PEP 604) | `int \| None` | 3.10 |
| `ParamSpec`, `Concatenate` (PEP 612) | `Callable[P, R]` | 3.10 |
| `TypeAlias` (PEP 613) | `Vector: TypeAlias = list[float]` | 3.10 |
| `TypeGuard` (PEP 647) | `def is_str(x: object) -> TypeGuard[str]` | 3.10 |
| `Self` (PEP 673) | `def copy(self) -> Self` | 3.11 |
| `Required`, `NotRequired` (PEP 655) | TypedDict keys | 3.11 |
| `Never`, `assert_never`, `LiteralString` | exhaustiveness, SQL strings | 3.11 |
| `TypeVarTuple`, `Unpack` (PEP 646) | variadic generics | 3.11 |
| Type parameter syntax (PEP 695) | `def first[T](xs: list[T]) -> T`, `type Pair = tuple[int, int]` | 3.12 |
| `@override` (PEP 698) | marks an intentional override | 3.12 |
| `TypeIs` (PEP 742) | narrows both branches | 3.13 |
| `ReadOnly` TypedDict items (PEP 705) | `name: ReadOnly[str]` | 3.13 |
| Type parameter defaults (PEP 696) | `class Box[T = int]` | 3.13 |

With `from __future__ import annotations`, the 3.9 and 3.10 syntax works inside annotations on older versions, because annotations
are not evaluated. It does not help where the expression is evaluated at runtime: `isinstance` arguments, `cast()`, base classes,
type alias assignments without `TypeAlias`, and the frameworks in [Runtime-evaluated annotations](#runtime-evaluated-annotations).

## Imports

- Take abstract collection and callable types from `collections.abc`: `Callable`, `Iterable`, `Iterator`, `Sequence`, `Mapping`,
  `MutableMapping`, `Generator`, `Awaitable`. Their `typing` aliases are deprecated.
- Prefer the abstract type a parameter actually needs: `Iterable[str]` if it is only iterated, `Sequence[str]` if indexed or
  measured, `Mapping[str, int]` if only read. Return the concrete type you build (`list[str]`), since callers may rely on it.
- Match the project's existing import style (`from typing import Any` versus `import typing as t`) and let the formatter or linter
  sort them.

## Callables

- Always parameterize. A bare `Callable` is `implicit-any-type-argument`.
- Spell out the signature when it is known: `Callable[[str, int], bool]`.
- When the arguments vary, `Callable[..., R]`. For the return of a callback whose result is ignored or only passed along,
  `Callable[..., object]` is stricter than `Callable[..., Any]` and just as correct. Use `Any` only when the caller consumes a
  result whose type is genuinely dynamic.
- For keyword arguments or overloads a `Callable[...]` cannot express, write a callback `Protocol` with `__call__`.

## Type Variables and Generics

When the output type is determined by an input type (identity and passthrough helpers, "return one of these arguments", containers,
registries keyed by type), use a type variable instead of widening to `object` or `Any`. `object` in and `object` out discards
exactly the information a type variable keeps.

```python
# Python 3.12+
def first[T](items: Sequence[T]) -> T:
    return items[0]

# Before 3.12
_T = TypeVar("_T")

def first(items: Sequence[_T]) -> _T:
    return items[0]
```

- Use the PEP 695 syntax when the floor is 3.12 or later. Otherwise declare a `TypeVar`; follow the project's naming convention, and
  if there is none, give a module-private one a leading underscore matching its string name (`_T = TypeVar("_T")`).
- Bound it when the function needs some capability: `def longest[T: Sized](items: Iterable[T]) -> T` (or
  `TypeVar("_T", bound=Sized)`).
- If the function transforms the value so the output type differs from the input, a single type variable is wrong. Name the real
  output type.
- `type[_T]` for "a class, and an instance of it comes back": `def create(cls: type[_T]) -> _T`.

## Decorators and ParamSpec

A decorator that returns a wrapper with the same signature should carry that signature through with `ParamSpec`.
`Callable[..., Any]` erases it, and every caller of a decorated function loses its argument checking.

```python
from collections.abc import Callable
from functools import wraps

def logged[**P, R](fn: Callable[P, R]) -> Callable[P, R]:     # 3.12+
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(*args, **kwargs)
    return wrapper
```

Before 3.12, declare `_P = ParamSpec("_P")` and `_R = TypeVar("_R")` at module level. Use `Concatenate[X, P]` when the wrapper adds
or consumes a leading argument. Skip `ParamSpec` only when the wrapper genuinely accepts and returns arbitrary callables.

A decorator factory (`@retry(times=3)`) returns the decorator:
`def retry(times: int) -> Callable[[Callable[P, R]], Callable[P, R]]`.

## Narrowing Helpers: TypeGuard and TypeIs

A predicate (`is_*`, `has_*`) that takes a broad type and returns `bool` usually wants a narrowing return type, so callers get the
narrowed type in the `if` branch:

- `TypeIs[X]` narrows both branches and is the better default, but needs 3.13 or `typing_extensions` 4.10 or later.
- `TypeGuard[X]` narrows only the true branch; use it when the narrowed type is not a subtype of the input, or when `TypeIs` is not
  available.
- An `issubclass`-style helper taking `klass: type[_T]` returns `TypeGuard[type[_T]]`.
- Prefer an explicit `isinstance(x, type)` check over `try: issubclass(...) except TypeError`. It is clearer and Pyrefly can narrow
  on it.

## Classes and Attributes

- Declare at class level any attribute assigned in a method, especially one first assigned `None` or `()`, which otherwise becomes
  `implicit-any-attribute`:

  ```python
  class Session:
      token: str | None
      retries: int

      def __init__(self) -> None:
          self.token = None
          self.retries = 0
  ```

  In dataclasses and similar classes this creates a field. See [Runtime-evaluated annotations](#runtime-evaluated-annotations).
- `__init__` returns `-> None`.
- A method returning its own class: `Self`. For `__new__` or alternate constructors, `Self` too, so subclasses get the right type.
- Mark constants `Final` only if the project does; it is a behavior claim, not just a type.
- `@override` on overriding methods is required only if the project enables `missing-override-decorator` (the `strict` preset does).
  Otherwise leave it to the project.
- Keep the parent's parameter names when overriding. Renaming one is `bad-override-param-name`.

## Dict Shapes, Literals, and Sentinels

- A dict with a fixed set of string keys that is built and read in a few places is a `TypedDict`, not `dict[str, Any]`. Introduce
  one only when it is local to the target or the user agrees; a new shared type is a design decision.
- A parameter that takes a few fixed strings or numbers: `Literal["r", "w", "a"]`.
- A `None` default means `X | None`: `def f(timeout: float | None = None)`.
- A sentinel: a single-member `enum` gives a precise type (`X | Literal[_Missing.MISSING]`). A bare `object()` sentinel can only be
  typed as `object`, which swallows the union; suggest the enum to the user rather than widening.

## Import Cycles and Forward References

When a type is needed only for annotations and importing it would create a cycle or a costly import, import it under `TYPE_CHECKING`
and keep annotations unevaluated:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkg.graph import Graph

def transform(graph: Graph) -> Graph: ...
```

Without `from __future__ import annotations`, quote the name: `"Graph"`. Inside a class body, a reference to the class itself also
needs quoting (or `Self`) unless the future import is present. If the module already uses one approach, stay with it.

## Runtime-Evaluated Annotations

Most annotations are never evaluated, but some code reads them while the program runs. In these places an annotation is behavior, so
check before you add or change one:

| Where | What an annotation does there | Watch for |
| :---- | :---------------------------- | :-------- |
| `@dataclass`, attrs, `NamedTuple`, `TypedDict` classes | A class-level annotation declares a field | Annotating a plain class attribute adds a constructor parameter. Use `ClassVar[...]` for class-level values. |
| Pydantic models, ORM models (SQLAlchemy `Mapped[...]`, Django) | Declares and validates or maps fields | Same as above, plus a changed type changes validation or the schema. |
| FastAPI, Typer, `functools.singledispatch`, `typing.get_type_hints`, `inspect.signature` consumers | Reads parameter annotations at runtime | Names imported only under `TYPE_CHECKING` raise `NameError`; a changed type changes parsing or dispatch. |
| Tests that snapshot signatures or the public API | Compares the stringified signature | Any added annotation changes the string. Suppress on the reported line instead, as SKILL.md describes. |

Pyrefly has built-in support for Pydantic, Django, and attrs, so it checks these classes as the libraries treat them. That makes
`pyrefly check` a good first warning, but only the tests prove the runtime behavior is unchanged.
