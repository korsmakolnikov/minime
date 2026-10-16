---
name: python-scaffold
description: Creates a new Python project with the scaffold tool - src layout, uv, pytest with Hypothesis, ruff, mypy --strict, a Makefile task runner, GitHub Actions CI, git init with an empty "start." commit and toolchain.yaml. kent loads it on a greenfield Python project, before hughes and ford; the user can also run it on their own.
---

# python-scaffold

The project's environment, not its architecture: ford lays the architecture
inside a project that already builds and runs its tests.

## Before

* The current directory is the project directory, created by the user, and
  holds nothing the templates write (`scaffold python PROJECT_NAME=x
  --dry-run` lists them).
* Ask the user, in one question each, with the default first:
  1. **Project name**: the directory's basename. The distribution name.
  2. **Package**: the name as a lowercase identifier (`agent-bench` →
     `agent_bench`). The import name, under `src/`.
  3. **Python version**: `3.12`. The minimum version, `requires-python`.
  4. **GitHub repository** (`owner/name`) for the CI badge, or none.

## Run

```sh
scaffold python PROJECT_NAME=<name> PACKAGE=<package> PYTHON=<version> GITHUB_REPO=<owner/name>
```

It creates:

```
pyproject.toml            hatchling, dev group: pytest, hypothesis, ruff, mypy
.python-version           the Python version uv uses
Makefile                  deps (Arch, Ubuntu), install, build, test, lint,
                          format, typecheck, check, clean
src/<package>/            __init__.py, py.typed
tests/test_import.py      one test, so the runner has something to run
.github/workflows/ci.yml  uv, make install, make check, make test
.gitignore, README.md
toolchain.yaml            language: python (see workflow-files for versioning)
```

then `git init` and an empty `start.` commit, unless the directory is inside
a repository already. It refuses to overwrite a file.

## Verify

`scaffold verify` runs `make install` (it downloads the dependencies: ask the
user first), `make build`, `make check` and `make test`, and reports each.
A missing `uv` or Python: the user runs `make deps` (it uses `sudo`; never
run it yourself). Report failures with their output.

## After

* The scaffolded files stay uncommitted: committing them is the user's
  decision (a `chore: scaffold the project` commit through `linus commit
  --phase other`, when they say so).
* The tests and the checks run through `toolchain` from now on (see the
  `python-handbook` skill).
