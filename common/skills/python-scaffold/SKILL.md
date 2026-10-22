---
name: python-scaffold
description: Creates a new Python project with the scaffold tool - src layout, uv, pytest with Hypothesis, ruff, mypy --strict, a Makefile task runner, GitHub Actions CI, git init with an empty "start." commit and toolchain.yaml. ford loads it on a greenfield Python project, before the architecture; the user can also run it on their own.
---

# python-scaffold

The project's environment, not its architecture: ford lays the architecture
inside a project that already builds and runs its tests.

## Before

* The project directory is the current directory, or a new folder that
  `--dir <folder>` creates (a project inside an existing repository); it
  holds nothing the templates write (`scaffold python PROJECT_NAME=x
  --dry-run` lists them).
* Ask the user (in the workflow, through kent's relay), in one question
  each, with the default first, only what kent's prompt and the shopping
  list do not already give. A user's delegation of the technology choices
  to your recommendations covers these questions too: take the defaults and
  report the values you used.
  1. **Project name**: the directory's basename. The distribution name.
  2. **Package**: the name as a lowercase identifier (`agent-bench` →
     `agent_bench`). The import name, under `src/`.
  3. **Python version**: `3.12`. The minimum version, `requires-python`.
  4. **GitHub repository** (`owner/name`) for the CI badge, or none.

## Run

```sh
scaffold python PROJECT_NAME=<name> PACKAGE=<package> PYTHON=<version> GITHUB_REPO=<owner/name> [--dir <folder>]
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
With `--dir` inside a repository, the CI goes to the repository's root
(`.github/workflows/<folder>.yml`, every step run in the folder, triggered
only by changes to the folder and to that workflow): GitHub
reads workflows only from there.
A `toolchain.yaml` at the root names the folder (`project: <folder>`), so
that the toolchain tools find the project from there; kent commits it with
the workflow's files.

## Verify

`scaffold verify [--dir <folder>]` runs `make install` (it downloads the dependencies: ask the
user first), `make build`, `make check` and `make test`, and reports each.
A missing `uv` or Python: the user runs `make deps` (it uses `sudo`; never
run it yourself). Report failures with their output.

## After

* Once verify passes, on the feature branch (`linus` refuses `master` and
  `main`), commit the scaffold: `scaffold commit [--dir <folder>] --model
  <id>` commits every untracked file of the project as `chore: scaffold the
  project`, the lock file included, and leaves the workflow's files out.
  Never hand this commit to the user.
* The tests and the checks run through `toolchain` from now on (see the
  `python-handbook` skill).
