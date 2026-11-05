# Hypothesis with `pytest`

Property-based tests check a statement that should hold for every input in a space, and let Hypothesis search for a counterexample.
Use them where a property is easy to state and examples are hard to choose: parsers and serializers, normalization functions,
arithmetic on money or units, and anything with an inverse.

## Choosing Properties

| Property | Example |
| :------- | :------ |
| Round trip | `loads(dumps(x)) == x` |
| Idempotence | `normalize(normalize(s)) == normalize(s)` |
| Invariant | `len(wrap(text, width))` lines, each at most `width` long unless it is one long word |
| Oracle | The fast implementation agrees with a slow, obviously correct one |
| No crash | Any input either returns a value or raises the documented exception |

A property that restates the implementation proves nothing. Keep ordinary example tests for the cases that matter to the business,
and pin regressions Hypothesis finds with `@example(...)`; the example database in `.hypothesis/` is a cache, not a record.

## Writing the Test

```python
from hypothesis import example, given, strategies as st


@given(st.text())
@example("Crème Brûlée")
def test_slugify_is_idempotent(text):
    assert slugify(slugify(text)) == slugify(text)
```

- Build inputs with strategies (`st.builds(Account, owner=st.text(min_size=1))`, `st.from_type(Settings)`) rather than filtering
  with `assume`, which wastes examples.
- Bound sizes and ranges to what the code accepts (`st.integers(1, 65535)` for a port), and test the invalid range separately.

## Fixtures

A function-scoped fixture runs once per test function, not once per generated example, so every example shares the same object.
Hypothesis raises the `function_scoped_fixture` health check for this. Fix it by building fresh state inside the test body, or by
using a fixture whose value is immutable. Suppress the health check only for fixtures such as `tmp_path` that you then use in a way
that is safe across examples (for example, a unique subdirectory per example).

## Settings and CI

Register profiles in the root `conftest.py` and pick one from the environment:

```python
import os
from hypothesis import settings

settings.register_profile("dev", max_examples=50)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
```

Hypothesis ships a `ci` profile (derandomized, no deadline, no example database) that it loads automatically when the `CI`
environment variable is set. Reproduce a failure with the `--hypothesis-seed` value or the `@reproduce_failure` blob that the
failure report prints, and see the search with `--hypothesis-show-statistics`.
