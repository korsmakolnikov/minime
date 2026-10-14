---
name: scaffold
description: Scaffold a new project in the current directory for a given language (currently C) - directory layout, build system, unit tests, README with CI badge, GitHub Actions CI, git init with an empty "start." commit. Invoke explicitly as /scaffold <language>.
argument-hint: <language>
disable-model-invocation: true
---

# scaffold — project bootstrap procedure

Scaffold the boring, easy-to-forget initial setup of a project. The user has already created the project directory and runs this skill from inside it. The skill knows nothing about the project's domain: it lays down structure, tooling and CI, nothing else.

Skill directory: `~/.claude/skills/scaffold` (if not found there, locate it with `find ~/.claude -type d -name scaffold`). It contains:

- `scripts/scaffold.sh` — renders `<language>/templates/` into the current directory and initialises git.
- `<language>/templates/` — the files to create, with `{{PLACEHOLDER}}` markers in paths and contents.

Execute the steps in order. Do not skip the question step, even if the answers seem obvious.

## Step 1 — Language

`$ARGUMENTS` is the language, case-insensitive. Supported languages: **C** (`c`).

If `$ARGUMENTS` is empty or not supported, reply with `Usage: /scaffold <language>` followed by the list of supported languages, and stop.

## Step 2 — Preconditions

1. The current directory is the project directory. Never `cd` elsewhere and never create the project directory yourself.
2. Run `ls -A`. If the directory already contains `src/`, `include/`, `tests/`, `Makefile`, `CMakeLists.txt`, `README.md`, `.github/` or `.gitignore`, stop and report which files conflict: the script refuses to overwrite and so do you.
3. Gather the defaults for the questions:
   - project name: the basename of the current directory;
   - target architecture: `uname -m`;
   - GitHub repository: `<owner>/<basename>`, where `<owner>` is `gh api user -q .login` if `gh` is available and logged in, else `git config --get github.user`, else unknown.

## Step 3 — Questions

Ask all of the following in a single `AskUserQuestion` call. Always ask, even if a default exists; the default goes first, marked `(Recommended)`.

Common:

1. **Project name** — option: the directory basename. Used for the executable, the header and the README title. Any string works; the script derives a C identifier from it.

Language-specific: see the language section below.

## Step 4 — Render

Run, from the project directory:

```sh
~/.claude/skills/scaffold/scripts/scaffold.sh <language> PROJECT_NAME=<name> KEY=VALUE ...
```

with the `KEY=VALUE` pairs listed in the language section. The script:

- creates every file, replacing the placeholders;
- refuses to run if a destination exists or a placeholder is left unresolved;
- runs `git init` and `git commit -m "start." --allow-empty` — unless the directory is already inside a git repository (monorepo), in which case it skips both and says so.

If the script fails, report its output verbatim and stop.

## Step 5 — Verify

1. Check the toolchain: `command -v gcc make cmake git`. If anything is missing, tell the user to run `make deps` (it uses `sudo`; do not run it yourself unless asked).
2. If the toolchain is present, run `make && make test`. The test target fetches Unity from GitHub at configure time, so it needs network access. Report the outcome truthfully: a failing build or test is reported with its output, not hidden.

## Step 6 — Report

Reply with:

- the list of created files;
- the git state: empty `start.` commit created (or skipped, with the reason); **the scaffolded files are not committed** — the user or the primary agent decides when and how;
- the verification result;
- next steps in one line: create the remote (e.g. `gh repo create <owner>/<name> --source=. --push`) so that the CI badge in the README resolves.

## Permanent rules

- Everything you write — files, messages, commit — is in English.
- Never commit the scaffolded files. The only commit is the empty `start.` one made by the script.
- Never edit the templates in the skill directory and never add files beyond what the templates produce, unless the user asks explicitly. Adjust only what the user requests, after the render.
- Never run `make deps` or anything requiring `sudo` without being asked.
- Never `git init` a nested repository inside an existing one.

---

## Language: C

Directory layout produced:

```
src/                      main.c + <name>.c (library sources)
include/<name>.h          public header
tests/test_<ident>.c      Unity test executable
Makefile                  wrapper around CMake: make (build), make test, make run, make deps, make clean
CMakeLists.txt            executable + static library + Unity tests via FetchContent
README.md                 with the GitHub Actions CI badge
.github/workflows/ci.yml  runs make deps / make / make test in an ubuntu:latest container
.gitignore                build/
```

Toolchain: gcc, make, cmake >= 3.21, git. `make deps` installs them on Ubuntu/Debian (apt) and Arch (pacman). Unity is fetched by CMake at configure time (tag `v2.6.1`).

Questions to add to Step 3 (in this order, after the project name):

2. **C standard** — options: `23 (Recommended)` (the latest standard), `17`, `11`. Any value accepted by CMake's `C_STANDARD` works.
3. **Target architecture** — options: the output of `uname -m` `(Recommended)`, then `i686`, `aarch64`. Anything other than the host (except `i686` on `x86_64`, handled with `-m32`) requires a cross compiler that the user provides via `CMAKE_FLAGS`; mention it in the report if chosen.
4. **GitHub repository** (`owner/name`, for the CI badge) — option: the detected `<owner>/<basename>`. If the owner is unknown, ask for the value.

Script invocation:

```sh
~/.claude/skills/scaffold/scripts/scaffold.sh c \
  PROJECT_NAME=<name> C_STANDARD=<std> TARGET_ARCH=<arch> GITHUB_REPO=<owner/name>
```
