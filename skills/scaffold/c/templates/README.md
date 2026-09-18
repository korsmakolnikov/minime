# {{PROJECT_NAME}}

[![CI](https://github.com/{{GITHUB_REPO}}/actions/workflows/ci.yml/badge.svg)](https://github.com/{{GITHUB_REPO}}/actions/workflows/ci.yml)

## Requirements

`gcc`, `make`, `cmake` (>= 3.21) and `git`. On Ubuntu/Debian or Arch Linux:

```sh
make deps
```

## Build, test, run

```sh
make          # build the executable into build/{{PROJECT_NAME}}
make test     # build and run the unit tests (Unity, via CTest)
make run      # build and run the executable
make clean    # remove the build directory
```

Defaults: C{{C_STANDARD}}, target `{{TARGET_ARCH}}`, `Debug` build. Override on the command line:

```sh
make C_STANDARD=17 TARGET_ARCH=i686 BUILD_TYPE=Release
```

## Layout

```
src/        source files (main.c + library sources)
include/    public headers
tests/      Unity tests (one executable, test_{{PROJECT_IDENT}})
Makefile    thin wrapper around CMake
CMakeLists.txt
.github/workflows/ci.yml   runs the tests in an Ubuntu container
```
