# minime

My Claude Code and GitHub Copilot CLI subagents and skills.

- [Architecture](#architecture) — how the pieces fit together.
- [unclebob](#unclebob) — TDD agents: unclebob-pair, interactive on its own; unclebob, autonomous in the workflow.
- [Claude Code workflow](#claude-code-workflow) — the architecture-first workflow on Claude Code: agents, tools, hooks, `toolchain.yaml`.
- [Copilot workflow](#copilot-workflow) — the same workflow on the GitHub Copilot CLI.
- [Installation](#installation-1)

# Architecture

Keep these diagrams in step with the repository: update them in the same
change that adds, removes or moves an agent, a skill, a tool, a hook or an
install target, together with `INSTALLED` in the Makefile (`make
clean-check` verifies it).

What the repository holds and where `make` installs it:

```
 repository                                       make target        installed in
 ──────────                                       ───────────        ────────────
 common/   shared by both CLIs                    common-install
   bin/      linus, spec-check, signal-check, toolchain, git-read,
             shopping-list, session-state, flow-log, audit-log,
             events-query, minime-migrate, adl-graph, scaffold,
             unit-audit, minime-config ──────────────────────────► ~/.local/bin/
   lib/      minime/ (the tools' library, drivers, templates) ───► ~/.local/share/minime/lib/
   signals/  *.schema.json ──────────────────────────────────────► ~/.local/share/minime/signals/
   skills/   adl-*, domain-spec, domain-model, elixir-handbook,   install ──────► ~/.claude/skills/
             python-handbook, python-scaffold, c-scaffold,        copilot-install ► ~/.copilot/skills/
             container-scaffold, workflow-files
 claude/   Claude Code                            install
   agents/   kent, hughes, ford, unclebob, martin, simon, joshua,
             argyris, marvin, linus, unclebob-pair ──────────────► ~/.claude/agents/
   skills/   save-session ───────────────────────────────────────► ~/.claude/skills/
   hooks/    guard.py, signal_stop.py, flow_hook.py ─────────────► ~/.claude/minime/hooks/
   bin/      unclebob (starts unclebob-pair) ────────────────────► ~/.local/bin/
 copilot/  GitHub Copilot CLI                     copilot-install
   agents/   *.agent.md, the same agents as claude/agents/ ──────► ~/.copilot/agents/
   skills/   minime-sync, datadog-… ─────────────────────────────► ~/.copilot/skills/
   hooks/    auto_approve.py, notify.py ─────────────────────────► ~/.copilot/hooks/
   settings.json, copilot-instructions.md ───────────────────────► ~/.copilot/
   bin/      kent, argyris ──────────────────────────────────────► ~/.local/bin/
 tests/    the tools and the hooks                make test
 logs      (not in the repository) ~/.local/state/minime/<repository>/: kent-events.jsonl,
           kent-errors.jsonl, kent-flow.log, kent's progress; kept 30 days, 100 MB in all
 .claude/  skills/kent-loop: drives a headless kent session on a test project
           (developing minime; not installed)
                                                  clean: removes all of it (INSTALLED)
```

How the agents work together on a project (the same on both CLIs; "Copilot
workflow" lists what differs):

```
                                         user
                          questions, approvals │ ▲ ASK_USER, relayed verbatim
                                               ▼ │
 ┌──────────────────────── kent: orchestrator, main thread (claude --agent kent) ──────────────────────┐
 │ frames the work, writes the shopping list (and an existing project's toolchain.yaml), launches     │
 │ every agent with what it needs, relays its questions; never writes code                           │
 └──┬──────────────┬───────────────┬───────────────┬──────────────┬────────────┬────────────┬─────────┘
    │ 2            │ 1b, 3         │ 4, 5          │ 6, per unit  │ 7          │ background │ background
    ▼              ▼               ▼               ▼              ▼            ▼            ▼
 hughes          ford            unclebob        martin         marvin       simon        joshua
 the domain:     new project's   TDD per         unit-audit     AGENTS.md,   C4 and       audits every
 entities,       scaffold and    component       order, TDD     CLAUDE.md    Mermaid      sub-agent turn
 events, ops,    containers,     from the        violations;                 class and    from transcripts
 properties      as-is and       inside out,     measures,                   sequence     and hook logs
 (reads no       target ADL,     then the        refactor of                 diagrams         │
 code)           interfaces,     whole flow:     the tests,                      │            ▼
    │              │             test: and       then of the                     ▼      audit-log
    ▼              ▼             feat: only      code, then                .documentation/   │
 .sources/       .sources/*.adl,   │             squashes                  <branch>/        ▼
 spec.yaml       components.yaml   │             the unit ──► you review               argyris, own
    ▲              │               ▼                          its commit,           session: fixes
    │              │          commits via linus               on your own           the agent files
    └──────────────┴── DOMAIN_CHANGE_REQUEST / INTERFACE_CHANGE_REQUEST, through kent    in minime

 Numbers: kent's steps (1a shopping list, 1b shopping list and as-is ADL, 2 domain,
 3 scaffold and architecture, 4 components, 5 flow, 6 refactor and squash, then your review,
 7 agent instructions).
 Every agent: its shell runs only its tools (guard.py); every call is logged (flow_hook.py);
 every sub-agent turn ends with a JSON signal block checked before kent sees it (signal_stop.py);
 build, tests and checks through `toolchain`, as the language's handbook explains; git writes only
 through linus; nobody pushes.
```

# unclebob

Two agents for [Claude Code](https://code.claude.com) that drive Test-Driven Development according to Robert C. Martin's Three Laws of TDD: **unclebob-pair**, interactive, when you run it on your own (below: you design every test and approve every step), and **unclebob**, which kent launches on a component in the workflow (cycles of a `test:` and a `feat:` commit, no refactor: martin refactors the whole unit afterwards; see [Claude Code workflow](#claude-code-workflow)).

## The Three Laws of TDD

1. You are not allowed to write any production code unless it is to make a failing unit test pass.
2. You are not allowed to write any more of a unit test than is sufficient to fail. Compilation failures count as failures.
3. You are not allowed to write any more production code than is sufficient to pass the one failing unit test.

## Roles (unclebob-pair)

- **The user designs the tests.** The agent never proposes which behavior to test.
- **The agent** writes the test dictated by the user, implements the minimum code that makes it pass (fake it: hardcoded values until a later test forces generalization), shows on screen every line it adds or changes, and proposes refactors only in the Blue phase.

## The cycle

Each cycle covers a single behavior and requires the user's explicit authorization. The agent never chains two cycles on its own.

| Step | Phase | What it does | Commit |
|------|-------|--------------|--------|
| 0 | Setup | Checks with `toolchain show` how the project builds and tests, runs one test to prove the tests run, asks for the commit scope | — |
| 1 | Authorization | Asks the user which behavior to test | — |
| 2 | Red | Writes a single test, runs it alone, verifies that it fails; one that passes at once is a characterisation, said plainly | `test:` |
| 3 | Green | Writes the minimum code that makes that test pass, then runs the tests that include the changed files | `feat:` |
| 4 | Blue | Measures the cycle's modules (time and space complexity, SOLID, idiom, readability, lines of code, tests and harness, the tests' durations), refactors the tests with the code unchanged, then the code with the tests unchanged, and measures again | `refactor(test):`, `refactor(<scope>):` |
| 5 | Close | Only on request: the tests related to the branch and the static checks of the language's handbook | `refactor:` |

Cross-cutting rules:

- Each step allows a single correction attempt beyond the first; typos, syntax errors and changes requested by the user do not count. Tests that fail after a green or a refactor commit stop the procedure immediately. The agent never changes what a test verifies.
- The procedure is to be interpreted literally: when in doubt, the most restrictive reading applies, every proposal waits for approval before being applied, and every confirmation request ends the turn.
- During the cycle only the current test runs, and after each commit the tests that include the files it changed. The full suite never runs: the CI runs it. Tests and static checks run through `toolchain`; the language's handbook skill (`elixir-handbook`, `python-handbook`) explains them.
- Every commit goes through the `linus` command, with the scope. Commit messages follow Conventional Commits and never reference the state of the tests. `test:` describes the feature, `feat:` how it was implemented, `refactor:` the choices and the reasons. Each commit includes only the files touched in that step.

## Installation

See [Installation](#installation-1) at the bottom.

## Usage

Start it as the session's main agent:

```sh
unclebob          # the same as claude --agent unclebob-pair
```

Do not delegate to it from a regular session: the procedure stops to ask for confirmation many times per cycle, and a delegated subagent cannot talk to you directly. Its hooks are active: its shell runs only its tools (`toolchain`, `linus`, `git-read`, …).

# Claude Code workflow

The architecture-first workflow, run by kent as the main thread:

```sh
claude --agent kent       # the workflow, in the project's directory
unclebob                  # unclebob-pair, interactive (claude --agent unclebob-pair)
claude --agent argyris    # fixes the agent files from joshua's log, in ~/code/minime
claude --agent linus      # commits for you, outside the workflow
tail -f ~/.local/state/minime/<repository>/kent-flow.log   # follow every agent's calls
```

kent frames the work and writes the shopping list; on an existing project it
has ford draft the as-is ADL. hughes writes the domain from the shopping
list (it reads no code); ford lays down a new project (`python-scaffold`,
`c-scaffold`, `container-scaffold`), then writes the architecture, the interfaces and the components
map; unclebob each component test-first, from the inside out, then the whole
flow, in cycles of a `test:` and a `feat:` commit; martin checks the order of
each unit's commits, measures it, refactors its tests and then its code,
runs the tests of the branch, squashes it into one commit and reports; you review that commit on your
own, with your own fixups, and tell kent to go on; marvin writes
the project's `AGENTS.md` (and `CLAUDE.md`) at the end. joshua audits every
turn and simon documents, in background. The agents' files are in
`claude/agents/`; the plan and what is left are in `claude/NEXT_ITERATION.md`.

## Tools instead of a shell

No agent improvises shell commands: each runs only its own tools, the
commands in `common/bin`, and `claude/hooks/guard.py` refuses anything else
(and command substitution, unquoted heredocs, writes outside the agent's
files). Reading goes through the Read tool, searching through `rg` (this
Claude Code has no Grep or Glob tools).

| Tool | What it does | Used by |
|---|---|---|
| `toolchain` | build, the tests to run (one, a commit's files, the branch's: never the full suite; `--durations` for their times), the static checks, a benchmark script (`bench`) | unclebob, ford, martin |
| `linus` | every git write: commits with a valid message (on Claude Code it does not check their order), fixups, squash (dropping `benchmark:` commits), partial staging (`hunks`, `stage-hunks`), the session's feature branch (`branch`) | kent, unclebob, ford, martin, marvin, argyris, linus |
| `unit-audit` | the order of a unit's commits (`test:`/`feat:` cycles, then `refactor(test)`, `refactor(<scope>)`, benchmarks), and the lines of production code, tests and harness | martin (`lines`: unclebob-pair) |
| `git-read` | read-only git (`{base}` stands for the branch's base) | everyone but hughes |
| `spec-check` | the spec (`domain`), ford's components map (`realization`), the spec ids the tests cite (`coverage`) | hughes, ford, unclebob, martin, joshua |
| `shopping-list` | the branch's shopping list (kent writes, the others read) | kent, all |
| `scaffold` | a new project from the language's templates, `git init`, `toolchain.yaml` (and the root's `project:` for a project in a folder), `verify`, `commit` | ford (kent: `init` in an empty directory) |
| `adl-graph` | the dependency graph for the as-is ADL, in the container if any | ford |
| `minime-migrate` | brings a project's workflow files to the current layout | kent, `make update` |
| `session-state` | kent's progress, to resume a session | kent |
| `events-query` | the sub-agent turns (with each turn's model usage and what replays it), their transcripts, the errors; `--repo <name>` reads another repository's logs | joshua, argyris |
| `audit-log` | the agents' violations, in the errors log: append, pending, handled, archive; `repos` lists the repositories with violations pending, `--repo <name>` picks one | joshua, martin, argyris |
| `flow-log` | a line in the activity log | everyone |
| `minime-config` | the optional configuration files (below): large systems, the handbooks' projects, command aliases | everyone |

## Hooks

Declared in each agent's frontmatter, active only while that agent runs:

* `guard.py <agent>` (PreToolUse): the agent's tools and files.
* `flow_hook.py <agent>` (PostToolUse): one line per call in
  `kent-flow.log`.
* `signal_stop.py --expect …` (Stop, SubagentStop for a sub-agent): the
  turn's final signal block is checked with `signal-check`; an invalid one
  goes back to the agent, which ends its turn again. Every turn is logged
  in `kent-events.jsonl` for joshua, with the model's usage in the turn
  (requests, input, cache and output tokens) and what replays it (branch,
  HEAD, session, the launch prompt, the transcript); a failed signal also
  in `kent-errors.jsonl`, beside the guard's refusals and the agents'
  violations.

The logs live in `~/.local/state/minime/<repository>/`
(`$MINIME_STATE_DIR` moves them; Copilot still uses `/tmp`). Folders
untouched for 30 days, and the oldest beyond 100 MB in all, are removed when
a session starts. Before you interrupt kent, `/save-session` writes its
progress there; `claude --agent kent` resumes from it.

## toolchain.yaml

How the project builds, tests and checks, at the project's root.
`scaffold` writes it for a new project, kent for an existing one. A
project in a folder of a repository is named by a `toolchain.yaml` at the
repository's root holding only `project: <folder>`, which `scaffold`
writes; the tools then work on the folder from the root.
`toolchain show` prints what will run. Like the other workflow files it is
versioned on Claude Code and never on Copilot (below).

```yaml
toolchain: 1
language: elixir                  # elixir | python: the driver
exec: [docker, exec, app]         # prefix of every command (a container wrapper)
exec_stdin: [docker, exec, -i, app]     # the same with stdin open (adl-graph)
env: {MIX_ENV: test}              # extra environment
commands:                         # replace a driver command; {paths} expands to the paths
  test: [make, test, "ARGS={paths}"]
architecture_tests: [test/architecture]
```

Without it, the language is detected (`mix.exs`, `pyproject.toml`) and the
driver's defaults run on the host. The languages' knowledge (test layout,
property-based testing, doubles and contract tests, style rules) is in the
handbooks: `elixir-handbook`, `python-handbook`.

## The workflow's files

`.sources/` (shopping lists, `spec.yaml`, the ADL, `components.yaml`),
`.documentation/<branch>/` (simon), `toolchain.yaml` and the logs
are the workflow's control centre; the `workflow-files` skill says who
writes and reads each.

* **Claude Code** (personal and open-source projects): versioned. The
  agents write them and kent commits them with `linus`, only between units
  (`docs(workflow): …`), so none falls inside a unit martin squashes.
* **Copilot** (code shared with colleagues): never committed. `make update`
  adds them to that machine's global git ignore (`minime-migrate
  --ignore-workflow-files`) and `linus` refuses them there.

# Copilot workflow

The same workflow as on Claude Code, for the [GitHub Copilot CLI](https://docs.github.com/copilot/how-tos/use-copilot-agents/use-copilot-cli), in `copilot/`: the same agents (`kent`, `hughes`, `ford`, `unclebob`, `martin`, `marvin`, `simon`, `joshua`, `argyris`, `linus`, and `unclebob-pair` on its own), the same steps, the same tools in `common/bin`, the same skills and signals. Each agent file in `copilot/agents/` is its Claude Code twin adapted to what the Copilot CLI offers. What differs:

| | Claude Code | Copilot |
|---|---|---|
| The workflow's files (`.sources/`, `.documentation/`, `toolchain.yaml`) | versioned: `kent` commits them between units, `marvin` may point to them | never versioned: in the global git ignore (`make update`), refused by `linus`, never named in `AGENTS.md` |
| Agent instructions | `marvin` writes `AGENTS.md` and `CLAUDE.md` | `marvin` writes `AGENTS.md` only |
| Launching and relaying | Agent tool, `SendMessage`, AskUserQuestion | `task` in background, `write_agent`/`read_agent`, `ask_user` |
| Signals | checked by the `signal_stop.py` hook at the end of every turn | checked by the agent itself with `signal-check`; `kent` answers `SIGNAL_INVALID`, `joshua` checks them again |
| Tools per agent | enforced by `guard.py` | stated in each agent file; the permission hook (`auto_approve.py`) approves or asks, and `joshua` audits |
| joshua | audits on `AUDIT`, from `kent-events.jsonl` and the transcripts | audits each agent's block on `REPORTED`, from the session's `events.jsonl`; `kent` sends `LAUNCHED`, `ANSWERED`, `REPORTED` |
| Logs and state | `~/.local/state/minime/<repository>/` | `/tmp` (`kent-flow.log`, `kent-errors.jsonl`, `kent-partial-session-progress.md`) |
| Activity log | written by the `flow_hook.py` hook | each agent logs its steps with `flow-log` |
| Resuming | `/save-session`, then `claude --agent kent` | `kent` saves on request; after `/restart`, any message resumes |
| Autonomy | the permission prompts | `~/.bash_copilot`: `AUTONOMY_LINUS`, `AUTONOMY_UNCLEBOB`, `AUTONOMY_MARTIN`, `AUTONOMY_ARGYRIS` |

The `minime-sync` skill mirrors `~/.copilot` into `copilot/` and commits it through `linus`; `datadog-experiment-downloader` downloads a Datadog LLM Observability experiment with `pup`. Both stay in `copilot/skills/`.

Start with `kent` (the launcher in `copilot/bin/`: `copilot --agent kent` plus `--add-dir` for the root of the repository it starts in, `~/.copilot` and `~/code/minime`, since reaching them otherwise asks for path access, which the permission hook cannot answer; other options pass through), or `copilot --agent unclebob-pair` for a plain TDD session. Follow the whole flow with `tail -f /tmp/kent-flow.log`. Run `argyris` (same launcher shape) whenever you want to fix the agent files: before `kent`, on the violations left by earlier sessions, or beside it in another terminal.

The names:

| Agent | After | Why |
|-------|-------|-----|
| `kent` | Kent Beck | TDD and Extreme Programming: drives the work cycle |
| `ford` | Neal Ford | co-author of the ADL with Mark Richards, fitness functions |
| `hughes` | John Hughes | QuickCheck: property-based testing of the spec |
| `unclebob` | Robert C. Martin | the three laws of TDD |
| `martin` | Martin Fowler | *Refactoring*: the refactor of each unit |
| `linus` | Linus Torvalds | created git: writes the history |
| `argyris` | Chris Argyris | double-loop learning: fix the rules, not only the action |
| `marvin` | Marvin Minsky | *The Society of Mind* and its K-lines: the state an agent starts from |
| `simon` | Simon Brown | the C4 model |
| `joshua` | the WOPR of *WarGames* | Joshua is its creator's password: it watches the whole game |

`copilot/copilot-instructions.md` holds the rules every agent follows; above all, no agent ever pushes, and no agent runs a bare `cd`, which would move the session's directory into a subfolder.

# Installation

Requires `make` and the `claude` CLI in your `PATH`. Works on any distribution (tested on Arch and Ubuntu): the Makefile copies agents into `~/.claude/agents/` and skills into `~/.claude/skills/`.

```sh
make install     # common-install, then the agents, skills and hooks of claude/ and the shared skills
make uninstall   # removes them
make reinstall   # uninstall + install
make clean       # removes everything any target installed, for both CLIs, old names included;
                 # missing paths are skipped (make clean && make install-copilot starts afresh)
make clean-check # fails if the repository installs something clean does not know about
make test        # the tests of the tools and the hooks (tests/)
make structurizr-install  # structurizr-cli for simon (Java from the distribution)
make claude-cli  # installs Claude Code, if missing (Arch Linux, Ubuntu)
make copilot-cli # installs the Copilot CLI, if missing (Node.js from the distribution)
make list        # lists the installed agents and skills
make check       # checks that the claude CLI is available
```

For the Copilot workflow:

```sh
make common-install    # installs the tools (common/bin/) in ~/.local/bin/, their library and
                       # the signal schemas in ~/.local/share/minime/, shared by both workflows
make copilot-install   # (or install-copilot) common-install, then agents, skills and hooks in ~/.copilot/,
                       # settings and copilot-instructions.md in ~/.copilot/
                       # and the kent and argyris launchers in ~/.local/bin/
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
  `docker compose exec`, and the `exec` of their aliases in `aliases.toml`,
  see "Configuration") are judged like host commands, and only in the
  containers listed in `COPILOT_CONTAINERS` (below). Reads
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
* `AUTONOMY_MARTIN`: martin's refactor of the code and the tests, told apart
  the same way.
* `AUTONOMY_ARGYRIS`: argyris applies its fixes without proposing them, edits
  agent and skill files and commits the minime mirror without prompting.

It also lists, in `COPILOT_CONTAINERS` (separated by spaces), the containers
and compose services where agents may run commands without asking.

`COPILOT_HOME` and `COPILOT_BIN_DIR` can be overridden on the `make` command line.

## Configuration

What differs from one machine to another stays out of the repository, in
optional TOML files in `~/.config/minime/` (`$XDG_CONFIG_HOME/minime`, or
`$MINIME_CONFIG_DIR`). No file is required and none is installed: a missing
file configures nothing, so a machine that needs none of this has no folder
at all. `minime-config` reads them for the agents and the hooks
(`minime-config path` prints the folder).

Each file may merge others from the same folder, with the same structure; a
missing one is skipped, so a file can name an extension that exists on one
machine only:

```toml
[extension]
files = ["work.toml"]
```

`large-systems.toml`: the systems too large for the full suite and too
coupled to test one app at a time. On them unclebob, ford and kent run only
the tests related to the branch (Copilot workflow);
`minime-config large-system` prints the name of the system the current
folder belongs to.

```toml
[systems]
shop = "~/code/shop"
```

`projects.toml`: the projects a language handbook covers besides those in
its frontmatter, as folder names (`minime-config projects <language>`).

```toml
[projects]
elixir = ["shop"]
```

`aliases.toml`: commands that stand for `docker` or `docker compose`, such
as a wrapper that runs containers in a development environment. The Copilot
hook judges `<cmd> exec <container> …` like `docker exec` (the container
must still be in `COPILOT_CONTAINERS`) and approves only the `read_only`
subcommands otherwise; the agents use `<cmd>` in place of `docker`, with
`context` as the container (`minime-config aliases`).

```toml
[alias.docker]
cmd = "devbox"
context = "app"
read_only = ["ps", "logs", "status"]

[alias."docker compose"]
cmd = "devbox"
context = "app"
```
