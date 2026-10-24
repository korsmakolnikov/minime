---
name: adl-fitness
description: Generates architectural fitness functions (ExUnit or pytest tests) from the ASSERT and FOREACH statements of ADL files, using the AdlFitness helpers shipped with this skill. Use after an ADL file is approved, before scaffolding the code it describes.
---

# Fitness functions from ADL assertions

Load `adl-spec` first. Every `ASSERT` becomes at least one test, and every
artifact an assertion references also gets an existence check, so that no
assertion passes on an empty tree.

## Install the helper (once per project)

The helpers are in `templates/`, next to this file.

* **Elixir**: copy `templates/adl_fitness.ex` to
  `test/support/adl_fitness.ex`, and make sure `mix.exs` compiles
  `test/support` in the test env (`elixirc_paths: elixirc_paths(Mix.env())`
  with `defp elixirc_paths(:test), do: ["lib", "test/support"]` and
  `defp elixirc_paths(_), do: ["lib"]`), unless it already does.
* **Python**: copy `templates/adl_fitness.py` next to the project's tests (for
  example `tests/support/adl_fitness.py`), following their layout and import
  style. It uses only the standard library: add no dependencies.

The helpers' docstrings state their limits (dynamic references are not
seen). When an assertion needs more than static imports, propose a dedicated
tool (`boundary` for Elixir, `import-linter` for Python) and record it in
`REQUIRES`.

## One test file per ADL file

* Elixir: `test/architecture/<adl file name>_test.exs`, module
  `<App>.Architecture.<Name>Test`; Python:
  `tests/architecture/test_<adl file name>.py`.
* The **full ADL text goes in the module doc / docstring**: `.sources/` is not
  committed, so the tests are the only versioned trace of the architecture.
* One test per assertion, named after it.

## Mapping

Namespaces follow the physical-name mapping in `adl-spec`. Elixir functions
take the OTP app (`:sysops`) first; Python functions take the source root and
the root package first.

| ADL | Helper |
|---|---|
| every `DEFINE` referenced below | `assert_defined(…, [namespaces])` |
| `CLASSES are only CONTAINED within X` | `assert_only_within(…, [namespaces of X], allow: [root module])` |
| `CLASSES are only CONTAINED within SUBDOMAINS within DOMAINS` | expand to the namespaces of the defined subdomains |
| `a has NO DEPENDENCY on {b, c}` | `assert_no_dependency(…, a, [b, c])` |
| `a has NO DEPENDENCY on other COMPONENTS` | `assert_no_dependency(…, a, [siblings of a])` |
| every sibling independent of the others | `assert_mutually_independent(…, [siblings])` |
| `FOREACH $X IN COMPONENTS DO ASSERT(...) END` | one generated test per `$X` (a `for` comprehension around `test` in ExUnit, `pytest.mark.parametrize` in pytest) |
| `a CONTAINS library` | custom test: the library is declared in `mix.exs`/`pyproject.toml` and referenced from `a` |
| assertions on runtime behaviour, time, metrics, `SERVICES` deployment | not static. Report it; do not write a test that fakes it |

`CONST` values become module attributes or module-level constants.

## Verify

1. Run the architecture tests alone: before scaffolding they must fail on
   `assert_defined`, as expected.
2. After scaffolding they must pass; then run the full suite.
3. Prove at least one dependency assertion can fail: add a forbidden call,
   watch the test fail, revert it. Never commit the probe.
