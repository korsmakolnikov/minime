---
name: c-scaffold
description: Creates a new C project with the scaffold tool - CMake behind a Make wrapper, Unity tests, GitHub Actions CI, git init with an empty "start." commit. kent loads it on a greenfield C project; the user can also run it on their own.
---

# c-scaffold

The project's environment, not its architecture.

## Before

* The current directory is the project directory, created by the user, and
  holds nothing the templates write (`scaffold c … --dry-run` lists them).
* Ask the user, in one question each, with the default first:
  1. **Project name**: the directory's basename. Used for the executable,
     the header and the README title; the tool derives a C identifier.
  2. **C standard**: `23`, then `17`, `11` (CMake's `C_STANDARD`).
  3. **Target architecture**: `uname -m` on this machine, then `i686`,
     `aarch64`. Anything but the host (except `i686` on `x86_64`, built with
     `-m32`) needs a cross compiler the user passes through `CMAKE_FLAGS`.
  4. **GitHub repository** (`owner/name`) for the CI badge.

## Run

```sh
scaffold c PROJECT_NAME=<name> C_STANDARD=<std> TARGET_ARCH=<arch> GITHUB_REPO=<owner/name>
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

## Verify

`scaffold verify` runs the Makefile's targets; the tests fetch Unity from
GitHub at configure time (network: ask the user first). Missing gcc, make or
cmake: the user runs `make deps` (it uses `sudo`; never run it yourself).

## After

The scaffolded files stay uncommitted until the user says otherwise. There is
no C driver for `toolchain` yet and no `c-handbook`: until then, the tests
run through the Makefile, with the user's approval.
