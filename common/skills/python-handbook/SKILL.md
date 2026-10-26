---
name: python-handbook
description: How to work on a Python project in this workflow - toolchain.yaml and the toolchain command (build, the tests to run, the static checks), the testing libraries (pytest, Hypothesis, Protocols and autospec doubles, contract tests), the test layout. Load it whenever you build, test, check, write or review Python code in a project listed in `projects`.
projects:
  - minime
  - kent-loop-sandbox
tools:
  - uv
  - pytest
  - ruff
  - mypy
---

# python-handbook

What an agent needs to know about a Python codebase, in one place. The
agents say **what** to run and **when**; the `toolchain` command does it, and
this skill says how to read the results and write the code.

## When it applies

* **Projects**: only a project whose folder name (the basename of the
  repository root) is listed in `projects` or printed by
  `minime-config projects python` (the optional `projects.toml` of the
  minime configuration). Anywhere else, say that no
  handbook covers the project and ask how to build and test it.
* **Tools**: only those in `tools`, and only those the project uses. A
  project on another runner (Poetry, tox, nox, Bazel) is reported, never
  forced into uv. A check the project does not configure (no `[tool.ruff]`,
  no mypy configuration) is skipped by `toolchain check`, never added.

## toolchain.yaml and the toolchain command

`toolchain.yaml`, at the project root (versioned on Claude Code, never on
Copilot: see `workflow-files`), tells `toolchain`
how this project runs its commands (a container wrapper, extra environment,
replaced commands); `toolchain show` prints what will run. Without the file,
`toolchain` detects Python from `pyproject.toml` and runs through `uv run`
when the project uses uv (`uv.lock` or `[tool.uv]`), plainly otherwise. The
`python-scaffold` skill writes it for a new project; kent, for an existing
one.

| Need | Command |
|---|---|
| byte-compile `src` and `tests` | `toolchain build` |
| one test | `toolchain test tests/test_cart.py::test_total_of_an_empty_cart` |
| a list of test files | `toolchain test <file> <file>` |
| the tests that include the files of a commit | `toolchain test --commit` (HEAD) |
| the tests that include some files | `toolchain test --related <file>…` |
| the tests related to the branch, architecture tests included | `toolchain test --branch` |
| the static checks on the branch's files | `toolchain check` (`--fix` formats first) |

Pass `--agent <your name>` so the output reaches the activity log. A test
file includes a module when it is its mirrored test (`src/shop/cart/pricing.py`
→ `tests/cart/test_pricing.py` or `tests/test_pricing.py`) or imports it
(`import shop.cart.pricing`, `from shop.cart.pricing import …`,
`from shop.cart import pricing`). There is no command for the full suite: the
CI runs it. Installing dependencies (`uv sync`, `uv add`) needs the user's
approval.

## Reading the static checks

`toolchain check` runs, on the `.py` files the branch changed: `ruff format
--check`, `ruff check`, `mypy`. A finding fixed without changing behaviour
(formatting, a lint rule, a type annotation) is a fix of the closing point,
committed as the agent's own instructions say; a fix that would change
behaviour is a new TDD cycle, starting with a red. Never silence a finding
with `# noqa` or `# type: ignore` unless the user agrees.

## Testing

* **pytest**: plain functions and `assert`; fixtures for shared setup.
  Fixtures shared by several test modules live in `conftest.py`, never
  copied between files; helpers in a `tests/support/` package.
* **Property-based tests**: Hypothesis, `@given(...)`. Strategies shared by
  several tests live in one generator module (`tests/support/strategies.py`),
  the project's single DSL for building domain values; the scenario's
  parameters stay explicit at the call site (a strategy that hardcodes a
  domain value hides the scenario). Beware assertions that pass for the
  wrong reason: when a helper such as `sorted()` silently accepts a scalar,
  assert directly. Adding `hypothesis` is the user's decision.
* **Doubles**: only of a component whose boundary is an interface, which in
  Python is a `typing.Protocol` or an abstract base class. Build them with
  `create_autospec(Class, instance=True)` rather than a bare `Mock`: it fails
  on missing attributes and wrong signatures, so the red you get is the red
  you wanted. Do not mock what you own unless it buys isolation you cannot
  get otherwise.
* **Contract tests**: nothing checks a double against the real class for
  you. Write the interface's tests once, in a base test class or a fixture
  parametrised over the implementations (`@pytest.fixture(params=[Real,
  Fake])`), and run them against both the real implementation and any fake
  that tests use in its place.
* **Architecture tests** (ford's fitness functions) live in
  `tests/architecture/`; `toolchain test --branch` always includes them.

## Durations and benchmarks (martin)

* `toolchain test --durations <paths>` adds `--durations=0
  --durations-min=0`: pytest prints every test's setup, call and teardown
  times, slowest first. A slow setup is usually a fixture with the wrong
  scope (a container started per test instead of per session).
* A benchmark is a plain script under `benchmarks/` in the project, run with
  `toolchain bench <file>` (`python <file>` in the project's environment).
  It imports the new version from the package and the old one from a copy
  of the file as it was at `HEAD`, saved beside the script
  (`benchmarks/<module>_old.py`), and times both with `timeit` on inputs of
  growing size (for example 10, 100, 1000, 10000), printing one line per
  size and version. Growing ratios between sizes show the complexity; equal
  ratios with a constant gap show a constant factor. It is committed as
  `benchmark(<scope>): …` and dropped by `linus squash`.

## Style

The project's ruff and mypy configuration rule; the scaffolded default is
`ruff` with `E, F, W, I, B, UP, SIM, RUF` and `mypy --strict`. Type every
public function; prefer dataclasses (frozen for value objects) and
`Protocol` over inheritance; comprehensions over `map`/`filter` with
lambdas.
