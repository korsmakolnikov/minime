# minime

My Claude Code and GitHub Copilot CLI subagents and skills.

- [unclebob](#unclebob) — subagent that drives TDD cycles.
- [scaffold](#scaffold) — skill that bootstraps a new project (currently C).
- [Copilot workflow](#copilot-workflow) — architecture-first workflow for the GitHub Copilot CLI.

# unclebob

Subagent for [Claude Code](https://code.claude.com) that drives Test-Driven Development cycles according to Robert C. Martin's Three Laws of TDD, as a step-by-step procedure with explicit completion conditions.

## The Three Laws of TDD

1. You are not allowed to write any production code unless it is to make a failing unit test pass.
2. You are not allowed to write any more of a unit test than is sufficient to fail. Compilation failures count as failures.
3. You are not allowed to write any more production code than is sufficient to pass the one failing unit test.

## Roles

- **The user designs the tests.** The agent never proposes which behavior to test.
- **The agent** writes the test dictated by the user, blindly implements the minimum code that makes it pass (fake it: hardcoded values until a later test forces generalization), and proposes refactors only in the Blue phase.

## The cycle

Each cycle covers a single behavior and requires the user's explicit authorization. The agent never chains two cycles on its own.

| Step | Phase | What it does | Commit |
|------|-------|--------------|--------|
| 0 | Setup | Identifies the runner and the commands for a single test / the full suite, without running them (at session start) | — |
| 1 | Authorization | Asks the user which behavior to test | — |
| 2 | Red | Writes a single test, runs it alone, verifies that it fails | `test:` |
| 3 | Green | Writes the minimum code that makes that test pass | `feat:` |
| 4a | Blue | SOLID check | `refactor:` |
| 4b | Blue | Time and space complexity check | `refactor:` |
| 4c | Blue | Language idiomaticity check | `refactor:` |
| 4d | Blue | Production code refactor proposal | `refactor:` |
| 4e | Blue | Test code refactor proposal | `refactor:` |
| 4f | Blue | Runs the full suite (only once per cycle); if it fails, stops and asks | — |

Cross-cutting rules:

- Each step allows a single correction attempt beyond the first; typos, syntax errors and changes requested by the user do not count. Two cases allow no attempts and stop the procedure immediately: a test that already passes in the Red phase, and a red suite at step 4f. The agent never changes what a test verifies.
- The procedure is to be interpreted literally: when in doubt, the most restrictive reading applies, every proposal waits for approval before being applied, and every confirmation request ends the turn.
- During the cycle only the current test runs; the full suite runs only at step 4f.
- Blue-phase sub-steps with nothing to propose are skipped with an explicit notice; multiple sub-steps may be submitted for confirmation in a single interaction, but each approved correction gets its own commit.
- Commit messages follow Conventional Commits and never reference the state of the tests. `test:` describes the feature, `feat:` how it was implemented, `refactor:` the choices and the reasons. Each commit includes only the files touched in that step.

## Installation

See [Installation](#installation-1) at the bottom.

## Usage

Start the agent as the session's primary agent:

```sh
claude --agent unclebob
```

Do not use it as a delegated subagent (`@unclebob` from a regular session): the procedure stops to ask for confirmation many times per cycle, and a delegated subagent runs in an isolated context that cannot talk directly to the user.

# scaffold

Skill for [Claude Code](https://code.claude.com) that bootstraps a new project in the current directory: directory layout, build system, unit tests, README with CI badge, GitHub Actions CI, `git init` and an empty `start.` commit. It knows nothing about the project's domain; it only automates the tedious first steps. One language per invocation; new languages are added as `skills/scaffold/<language>/templates/`.

## Usage

Create the project directory, start `claude` inside it and run:

```
/scaffold C
```

The skill asks for the project name and the language-specific options, renders the templates, runs `git init` + `git commit -m "start." --allow-empty`, then verifies with `make && make test`. The scaffolded files are **not** committed: that is up to you (or the primary agent). If the directory is already inside a git repository (monorepo), `git init` and the empty commit are skipped.

Invocation is explicit only (`disable-model-invocation: true`): the primary agent never triggers it on its own.

## Languages

### C

| Question | Default |
|----------|---------|
| Project name | directory basename |
| C standard | 23 (latest) |
| Target architecture | `uname -m` of the host (`i686` on `x86_64` is handled with `-m32`; other targets need a cross compiler via `CMAKE_FLAGS`) |
| GitHub repository (`owner/name`, for the badge) | `gh api user` login + basename |

Produces:

```
src/                      main.c + <name>.c
include/<name>.h
tests/test_<ident>.c      Unity
Makefile                  make (build), make test, make run, make deps, make clean
CMakeLists.txt            executable + static library + Unity via FetchContent (v2.6.1)
README.md                 with the CI badge
.github/workflows/ci.yml  make deps / make / make test in an ubuntu:latest container
.gitignore
```

`make deps` installs gcc, make, cmake and git on Ubuntu/Debian (apt) and Arch (pacman). `C_STANDARD`, `TARGET_ARCH`, `BUILD_TYPE`, `BUILD_DIR` and `CMAKE_FLAGS` can be overridden on the `make` command line.

# Copilot workflow

Agents and skills for the [GitHub Copilot CLI](https://docs.github.com/copilot/how-tos/use-copilot-agents/use-copilot-cli), in `copilot/`. Architecture is defined with the [Architecture Definition Language](https://www.developertoarchitect.com/downloads/adl-ref.pdf) (ADL) by Mark Richards and Neal Ford; ADL files live in `.adl/` at the root of each project and are not committed.

| Agent | Role |
|-------|------|
| `joshua` | Orchestrator. Studies the code, gathers the preliminary findings, runs `ford`, then `unclebob` one component at a time, and relays their questions to the user. Never writes code or commits. |
| `ford` | Interviews the user to write the ADL, then generates fitness functions, scaffold and component interfaces. No business logic. |
| `unclebob` | Implements the internals test-first. Refuses to work when the tests cannot run. Treats `ford`'s interfaces as a contract. |
| `gutexberg` | The only actor that writes to git: Conventional Commits, fixups bounded to the branch, Copilot co-author trailer naming the model. Uses the `gutexberg` command in `copilot/bin/`. |

| Skill | Role |
|-------|------|
| `adl-spec` | ADL reference, `.adl/` layout, mapping of physical names to Elixir and Python namespaces. |
| `adl-interview` | Interview protocol and the `ASK_USER` relay format. |
| `adl-fitness` | ADL assertions to ExUnit/pytest fitness functions, with standard-library helpers. |
| `adl-scaffold` | Namespaces and interfaces, without logic. |
| `adl-reverse` | As-is ADL drafts from the dependency graph of existing code. |

Start with `copilot --agent joshua` (or `copilot --agent unclebob` for a plain TDD session).

# Installation

Requires `make` and the `claude` CLI in your `PATH`. Works on any distribution (tested on Arch and Ubuntu): the Makefile copies agents into `~/.claude/agents/` and skills into `~/.claude/skills/`.

```sh
make install     # installs all agents in agents/ and all skills in skills/
make uninstall   # removes them
make reinstall   # uninstall + install
make list        # lists the installed agents and skills
make check       # checks that the claude CLI is available
```

For the Copilot workflow:

```sh
make copilot-install   # installs or overwrites agents and skills in ~/.copilot/,
                       # settings in ~/.copilot/settings.json and gutexberg in ~/.local/bin/
```

`COPILOT_HOME` and `COPILOT_BIN_DIR` can be overridden on the `make` command line.
