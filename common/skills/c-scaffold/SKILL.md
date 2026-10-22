---
name: c-scaffold
description: Creates a new C project with the scaffold tool - CMake behind a Make wrapper, Unity tests, GitHub Actions CI, git init with an empty "start." commit. ford loads it on a greenfield C project, before the architecture; the user can also run it on their own.
---

# c-scaffold

The project's environment, not its architecture.

## Before

* The project directory is the current directory, or a new folder that
  `--dir <folder>` creates (a project inside an existing repository); it
  holds nothing the templates write (`scaffold c … --dry-run` lists them).
* Ask the user (in the workflow, through kent's relay), in one question
  each, with the default first, only what kent's prompt and the shopping
  list do not already give. A user's delegation of the technology choices
  to your recommendations covers these questions too: take the defaults and
  report the values you used.
  1. **Project name**: the directory's basename. Used for the executable,
     the header and the README title; the tool derives a C identifier.
  2. **C standard**: `23`, then `17`, `11` (CMake's `C_STANDARD`).
  3. **Target architecture**: `uname -m` on this machine, then `i686`,
     `aarch64`. Anything but the host (except `i686` on `x86_64`, built with
     `-m32`) needs a cross compiler the user passes through `CMAKE_FLAGS`.
  4. **GitHub repository** (`owner/name`) for the CI badge.

## Run

```sh
scaffold c PROJECT_NAME=<name> C_STANDARD=<std> TARGET_ARCH=<arch> GITHUB_REPO=<owner/name> [--dir <folder>]
```

It creates:

```
src/                      main.c + <name>.c (library sources)
include/<name>.h          public header
tests/test_<ident>.c      Unity test executable
Makefile                  wrapper around CMake: make, make test, make run, make deps, make clean
CMakeLists.txt            executable + static library + Unity via FetchContent (tag v2.6.1)
README.md                 with the CI badge
.github/workflows/ci.yml  make deps, make, make test in an ubuntu:latest container
.gitignore                build/
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

`scaffold verify [--dir <folder>]` runs the Makefile's targets; the tests fetch Unity from
GitHub at configure time (network: ask the user first). Missing gcc, make or
cmake: the user runs `make deps` (it uses `sudo`; never run it yourself).

## After

Once verify passes, on the feature branch (`linus` refuses `master` and
`main`), commit the scaffold with `scaffold commit [--dir <folder>] --model
<id>` (`chore: scaffold the project`, the workflow's files left out); never
hand this commit to the user. There is no C driver for `toolchain` yet and no `c-handbook`: until then, the tests
run through the Makefile, with the user's approval.
