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

Requires `make` and the `claude` CLI in your `PATH`. Works on any distribution (tested on Arch and Ubuntu): the Makefile copies the files into `~/.claude/agents/`.

```sh
make install     # installs all agents in agents/
make uninstall   # removes them
make reinstall   # uninstall + install
make list        # lists the installed agents
make check       # checks that the claude CLI is available
```

## Usage

Start the agent as the session's primary agent:

```sh
claude --agent unclebob
```

Do not use it as a delegated subagent (`@unclebob` from a regular session): the procedure stops to ask for confirmation many times per cycle, and a delegated subagent runs in an isolated context that cannot talk directly to the user.
