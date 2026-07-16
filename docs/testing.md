---
icon: lucide/flask-conical
---

# Testing packages

Karsk projects can ship [pytest](https://pytest.org)-based tests that exercise
the *built* packages, run with [karsk test](commands/test.md).

## The `karsk_tests/` convention

Tests live in a directory referenced by the config's `tests` field —
conventionally `karsk_tests/` next to `config.yaml` (this is what
[karsk init](commands/init.md) scaffolds):

```yaml
tests: ./karsk_tests/
```

`karsk test config.yaml` verifies that every package has been built (and tells
you to run `karsk build` if any are missing), then invokes pytest on that
directory. Anything after the config file is passed straight through to
pytest:

```sh
karsk test config.yaml -k version -x -v
```

## The `karsk` fixture

`karsk test` registers the `karsk.testing` pytest plugin, which provides a
single fixture named **`karsk`**. It returns the fully initialised
[`Context`](api/context.md) for your configuration — the same object the CLI
itself works with. With it you can look up packages (`karsk["hello"]`), find
their output paths, and run programs inside the build container with the
environment mounted at its destination paths via `Context.run()`.

## A worked example

The `hello_world` example ships this test
(`examples/hello_world/karsk_tests/test_versions.py`):

```python
--8<-- "examples/hello_world/karsk_tests/test_versions.py"
```

Step by step:

1. The `karsk` fixture provides the `Context`.
2. `karsk["hello"].config.version` reads the version straight from the
   configuration, so the test never hardcodes it.
3. `karsk.run(...)` executes the built binary inside the build container,
   with the package mounted read-only at its destination path — the same way
   it will run after deployment.
4. The test asserts the program exits cleanly and reports the configured
   version.

Tests may be `async` (as above); `karsk test` runs pytest with
[pytest-asyncio](https://pytest-asyncio.readthedocs.io/) in auto mode when
developing in the Karsk repository.

Note that the fixture only works under `karsk test` — running `pytest
karsk_tests/` directly fails with "Karsk context not initialised".

## See also

[karsk test](commands/test.md), [`karsk.testing` API](api/testing.md),
[`karsk.context` API](api/context.md)
