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

Skill for [Claude Code](https://code.claude.com) that bootstraps a new project in the current directory: directory layout, build system, unit tests, README with CI badge, GitHub Actions CI, `git init` and an empty `start.` commit. It knows nothing about the project's domain; it only automates the tedious first steps. One language per invocation; new languages are added as `claude/skills/scaffold/<language>/templates/`.

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

Agents and skills for the [GitHub Copilot CLI](https://docs.github.com/copilot/how-tos/use-copilot-agents/use-copilot-cli), in `copilot/`. Architecture is defined with the [Architecture Definition Language](https://www.developertoarchitect.com/downloads/adl-ref.pdf) (ADL) by Mark Richards and Neal Ford; the workflow's input (ADL files, domain spec, shopping lists) lives in `.sources/` at the root of each project, and its output, the architecture documentation, in `.documentation/<branch>/`; neither is committed. `kent` moves the `.adl/` and `.shopping_lists/` of earlier versions into `.sources/` at the start of a session, without overwriting anything and asking about every file that differs.

| Agent | Role |
|-------|------|
| `kent` | Orchestrator, run as the main agent. Studies the code, writes the preliminary findings (every unknown of the iteration) to `.sources/shopping_lists/<branch>.md`, runs `hughes` for the domain, `ford`, `hughes` again for the contracts, then `unclebob` one component at a time and the functional test, with `martin` reviewing and squashing each unit as soon as it is written, relays their questions to the user, keeps `joshua` informed, forwards its violations to `argyris` and every change of the sources to `simon`. Never writes code or commits. Every agent logs to `/tmp/kent-flow.log`, each line tagged with the agent's name. |
| `joshua` | Auditor. Runs in background beside `kent` for the whole session and checks every agent against its file and launch prompt. Read-only: violations never stop the workflow; `kent` prints them and forwards them to `argyris`, and `joshua` also logs them to `/tmp/joshua-violations.md`. |
| `hughes` | Interviews the user to write the domain spec, `.sources/spec.yaml`, validated by the `spec-check` command in `copilot/bin/`: entities, relations and constraints before `ford`; the contracts of the component operations and the properties for property-based tests after it. `unclebob` turns each entry into a red test. |
| `ford` | Interviews the user to write the ADL, then generates fitness functions, scaffold and component interfaces. No business logic. |
| `unclebob` | Implements the internals test-first, one red test at a time: every cycle is a red commit, a green commit and at least one refactor commit (empty when there is nothing to refactor). Refuses to work when the tests cannot run. Treats `ford`'s interfaces as a contract. Commits its cycles (`FEATURE_DRIVEN`) itself with the `linus` command, without launching an agent per commit; its static-analysis fixups at the close of a unit (`STATIC_CODE_FIX_DRIVEN`) go through the `linus` agent. |
| `linus` | The only agent that writes to git: Conventional Commits scoped by component (`feat(<domain> <component>): …`), a new commit for every change, Copilot co-author trailer naming the model. Uses the `linus` command in `copilot/bin/`, which records each commit's phase, refuses any order other than red, green, refactor, and squashes a unit only when the range is exactly that unit and its cycle is closed. Three modes, always named by the caller: `FEATURE_DRIVEN` (every agent; `unclebob` runs the command itself for its TDD cycles), `CODE_REVIEW_DRIVEN` (`martin` only: fixups of the branch commit that wrote the amended lines) and `STATIC_CODE_FIX_DRIVEN` (`unclebob` only: fixups of the unit's commits for the static-analysis (dialyzer) warnings found when the unit is done, folded into the unit by its squash). |
| `martin` | Reviewer, run after every unit `unclebob` writes: each component, then the final functional test, and each correction to a squashed unit. First audits from the commits that the unit was built test-first, sends every incoherence to `argyris` and shows the user the whole audit, commit by commit, cycle by cycle; only once the user approves it, squashes the unit into one commit with `linus squash`; then reviews that commit (SOLID, complexity, idiom, outcomes of every called function, spec coverage) and walks the user through its diff, file by file. The requested changes are applied by the unit's agent, uncommitted, and `linus` commits them as fixups of the unit's commit. The workflow ends with the review of the functional test. |
| `simon` | Architecture documenter. Runs in background beside `kent` for the whole session: whenever `ford` or `hughes` change the sources, writes for the user, in `.documentation/<branch>/`, a [Structurizr](https://structurizr.com) DSL workspace of the C4 model and `architecture.md`, with the domain model, the component interfaces, the architecture rules, the contracts and the sequence diagrams in Mermaid. Every element cites its source, and `joshua` checks that nothing diverges from what `ford` and `hughes` wrote. Flowcharts only on request. |
| `argyris` | Maintainer of the agent files. Runs in background in `kent`'s session, beside `joshua`: proposes a fix to the agent and skill files for each violation `kent` forwards, applies the approved ones, mirrors them here and tells `kent` to restart. Before its next launch of `hughes`, `ford`, `unclebob` or `martin`, `kent` saves its progress to `/tmp/kent-partial-session-progress.md` and asks for a `/restart`; it checks that file on every user message, so after the restart any message (or `kent --resume -i "continue"`) makes it resume from the file and delete it. `argyris` also watches that `kent` carries the restart out and that `joshua` never prompts the user, and alerts the user (desktop popup) when they do not. |

| Skill | Role |
|-------|------|
| `adl-spec` | ADL reference, `.sources/` layout, mapping of physical names to Elixir and Python namespaces. |
| `adl-interview` | Interview protocol for the ADL and the component interfaces. |
| `adl-fitness` | ADL assertions to ExUnit/pytest fitness functions, with standard-library helpers. |
| `adl-scaffold` | Namespaces and interfaces, without logic. |
| `adl-reverse` | As-is ADL drafts from the dependency graph of existing code. |
| `domain-spec` | The domain spec format, its validator and how each entry becomes a test (StreamData, Hypothesis). |
| `elixir-style` | The user's personal Elixir rules, stricter than the project's Credo and not shared with the team: `unclebob` applies them in the refactor phase to the code it changed, `martin` checks them in review. Today: a `with` has at most three clauses. |
| `minime-sync` | Mirrors `~/.copilot` into `copilot/` and commits it through `linus`; run it before a `/restart`. |
| `datadog-experiment-downloader` | Downloads a Datadog LLM Observability experiment with `pup`: summary, events and the agent loop of every trace, in parallel and resumable. |

Sub-agents cannot talk to the user: they end their turn with one `ASK_USER` block (`question`, optional `choices` separated by `|`, optional `default`, `why`), one question at a time, and `kent` relays it verbatim, prefixed with the agent's name.

Start with `kent` (the launcher in `copilot/bin/`: `copilot --agent kent` plus `--add-dir` for the root of the repository it starts in, `~/.copilot` and `~/code/minime`, since reaching them otherwise asks for path access, which the permission hook cannot answer; other options pass through), or `copilot --agent unclebob` for a plain TDD session. Follow the whole flow with `tail -f /tmp/kent-flow.log`.

The names:

| Agent | After | Why |
|-------|-------|-----|
| `kent` | Kent Beck | TDD and Extreme Programming: drives the work cycle |
| `ford` | Neal Ford | co-author of the ADL with Mark Richards, fitness functions |
| `hughes` | John Hughes | QuickCheck: property-based testing of the spec |
| `unclebob` | Robert C. Martin | the three laws of TDD |
| `martin` | Martin Fowler | *Refactoring*: the code review after the cycle |
| `linus` | Linus Torvalds | created git: writes the history |
| `argyris` | Chris Argyris | double-loop learning: fix the rules, not only the action |
| `simon` | Simon Brown | the C4 model |
| `joshua` | the WOPR of *WarGames* | Joshua is its creator's password: it watches the whole game |

`copilot/copilot-instructions.md` holds the rules every agent follows; above all, no agent ever pushes, and no agent runs a bare `cd`, which would move the session's directory into a subfolder.

# Installation

Requires `make` and the `claude` CLI in your `PATH`. Works on any distribution (tested on Arch and Ubuntu): the Makefile copies agents into `~/.claude/agents/` and skills into `~/.claude/skills/`.

```sh
make install     # installs all agents in claude/agents/ and all skills in claude/skills/
make uninstall   # removes them
make reinstall   # uninstall + install
make list        # lists the installed agents and skills
make check       # checks that the claude CLI is available
```

For the Copilot workflow:

```sh
make copilot-install   # installs or overwrites agents, skills and hooks in ~/.copilot/,
                       # settings and copilot-instructions.md in ~/.copilot/
                       # and linus, kent and spec-check in ~/.local/bin/
```

The hooks in `copilot/hooks/` keep the agents unattended:

* `auto_approve.py` (`permissionRequest`) approves any shell command whose
  effects fall inside a git-versioned folder (not git-ignored) or under
  `/tmp`, where agents may run anything. Edits and file creations are approved
  only under `/tmp`: code edits reach the user unless an autonomy setting
  says otherwise (below). Command
  substitutions (`$(...)`, backticks, `<(...)`) are approved when their own
  command is. Writes under the workflow folders at the root of a repository
  (`.sources/`, `.documentation/`, and the legacy `.adl/` and
  `.shopping_lists/`) are approved like those under `/tmp`; removals too,
  except in `.sources/`, which nothing could restore. Commands run in a container (`docker exec`,
  `docker compose exec`, `edgar exec`) are judged like host commands, and
  only in the containers listed in `COPILOT_CONTAINERS` (below). Reads
  (`view`, `grep`, `glob`) of `~/.copilot/agents`, `~/.copilot/skills` and
  `/tmp` are approved, so agents can read the agents they launch and the
  skills they use. Everything else asks. `git push`, network clients (`curl`,
  `wget`, `ssh`, `rsync`, `nc`, ...) and cluster commands (`kubectl`, `helm`,
  ...) are always denied, and git commands that discard uncommitted work
  (`reset --hard`, `clean`, `checkout --`, ...) always ask. Every request left
  to the user is logged with its reasons to `/tmp/copilot-hook-asks.jsonl`:
  read it to find the prompts that interrupt the flow (a prompt missing from
  it never reached the hook: a path-access prompt). Set
  `COPILOT_HOOK_DEBUG=1` to also log every payload to
  `/tmp/copilot-hook-permission.jsonl`.
* `notify.py` (`notification`, `agentStop`) shows a desktop popup
  (`notify-send`) when the user is needed and rings the terminal bell when an
  agent finishes. The popup fires only if the permission prompt or `ask_user`
  is still unanswered after `COPILOT_NOTIFY_DELAY` seconds (default 2), read
  from the session's `events.jsonl`.

`~/.bash_copilot` (installed from `copilot/bash_copilot` only when missing)
sets how much each agent may do without asking, read live by the hook and
the agents. `0` asks, `1` proceeds:

* `AUTONOMY_LINUS`: `linus commit`, `amend`, `squash` and `fixup`.
* `AUTONOMY_UNCLEBOB`: unclebob's code edits. The hook tells the agent behind
  an edit by finding the pending tool call on that file in the session's
  `events.jsonl` and following it to the task that launched the agent.
* `AUTONOMY_ARGYRIS`: argyris applies its fixes without proposing them, edits
  agent and skill files and commits the minime mirror without prompting.

It also lists, in `COPILOT_CONTAINERS` (separated by spaces), the containers
and compose services where agents may run commands without asking.

`COPILOT_HOME` and `COPILOT_BIN_DIR` can be overridden on the `make` command line.
