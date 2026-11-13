# beck

Status: **design**, no code yet. These notes record what was discussed and
approved, so that the next session resumes from here.

beck is an application that replaces the `kent` agent and redesigns the
architecture-first workflow around it. The workflow as agents costs too many
tokens (`claude/NEXT_ITERATION.md`, "Metriche dei token": unclebob 70.8 %,
joshua 10.7 %, kent 6.4 %), is slow, and needs the user at every unit.
The old `kent` agent stays until beck is stable, then fades out.

## Principles

* **Deterministic first, agent as fallback.** Every decision goes through a
  chain of responsibility: a deterministic handler answers when it can; when
  it cannot, the event passes to an agent (often a small one, on Haiku).
  beck is an agentic application made of several state machines, not a
  script, and not a single LLM orchestrator.
* **Event storming before design.** The domain of the workflow is modelled
  from its events first; the actors and their boundaries come after, and the
  old agents' boundaries are not sacred.
* **Agents never commit.** beck commits, after checking each TDD phase
  deterministically.
* **Agents never search the code twice.** The index maps every DSL id to the
  code and the tests; beck hands each agent only the slice it needs.
* **The user is the architect at the start and the reviewer at the end**,
  not a reviewer of every unit: the workflow can run overnight.
* **Event sourcing.** Everything that happens is an event; state, resume,
  policies, audits, metrics and replays all read the events.
* **KISS.** No layer, abstraction or option without a concrete need today.

## Configuration

* `~/.config/kent/config.yml`: global defaults. Anything tied to a work
  environment lives only here, never in this repository.
* `.kent/config.yml` in the project: extends and overrides the global one.
* Settings so far:
  * whether `.kent/` is versioned (replaces the old rule "versioned on
    Claude Code, never on Copilot", which no longer holds once Claude Code
    runs on company code);
  * the branch name format (when it contains a task code, the user gives it);
  * the model of each actor;
  * the token budget, per agent session and per iteration (infinite allowed:
    first we measure);
  * the CLI driver (Claude Code, Copilot).
* To decide: how this relates to the existing `~/.config/minime/*.toml`
  (`minime-config`).

## Project layout: `.kent/`

Everything beck needs lives in `.kent/`; the old `.sources/`,
`.documentation/`, `.adl/` and `.shopping_lists/` are ignored
(`minime-migrate` is dropped).

* `config.yml`
* shopping lists, one per branch
* the DSLs: the domain spec and the architecture (YAML); no components map
* `toolchain.yml` (to decide whether it moves here from the project root)
* `index.db`: the DSL-to-code index (derived, never versioned)
* the event stores (never versioned)

When versioned, beck commits `.kent/` itself (`docs(workflow): …`), only
between units; no agent is needed for it.

## Actors (draft)

| Actor | What | Notes |
|---|---|---|
| beck | the state machines, the policies, the commits, the deterministic checks, the TUI | no LLM |
| kent (scout, inside beck) | studies the existing code, delimits the area the iteration touches, anchors the spec ids to the code in brownfield, brings the environment up from the project's docs (`AGENTS.md`, README, Makefile) | name kept from Kent Beck; never runs together with the old `kent` agent |
| DSL author | the domain and the architecture: hughes and ford merged | two phases with fresh contexts; whether the domain phase still reads no code is open |
| unclebob | TDD, one group of spec ids per session, context cut by the index | may run in parallel on independent components |
| martin | refactors the unit on green tests and closes it on its own | no new tests (temporary benchmarks only); outside the unit only code covered by tests; missing tests send the work back to unclebob |
| joshua | audits only what the deterministic auditor cannot decide: interruptions, tooling violations, scope of the tests run | fed by events, at least per cycle |
| argyris | improves the agents, triggered by events; runs replays and A/B tests of models | |
| test reader | on Haiku: summarises a failure for unclebob | only when the deterministic parser is not enough |
| environment checker | is the environment up? deterministic from the container status, Haiku as fallback on long logs | |

Removed: **simon** (its output was never used; may return on demand),
**marvin** (`AGENTS.md` updates proved harmful; later, `AGENTS.md` will
import the DSLs), **the old kent** (after fade-out).

## DSLs

* **ADL dropped**, replaced by a YAML architecture DSL in the style of the
  domain spec, keeping ADL's features (the kinds of `DEFINE`, `ASSERT`,
  `FOREACH`), with an id on every element and every assertion.
* **No components map**: which component realizes each spec id is written
  in the architecture YAML (a design decision, so it lives in a versioned
  source); the index derives the rest down to the code.
* The fitness functions are generated deterministically from the
  assertions; an agent writes only those the generator cannot translate.
* Future stages, not in the first iteration: Alloy and TLA+ where they make
  sense.

## Index (SQLite, embedded)

* Maps spec id → component → symbols (functions, modules) → tests.
  Symbols from tree-sitter (Elixir, Python, C grammars).
* Few heavy writes (when the DSLs are created), then small updates; mostly
  reads, graph walks with `WITH RECURSIVE`.
* Each file is tracked by content hash; a commit event marks the index of
  its files dirty, and a policy has kent verify them.
* **At the start of every iteration** the whole map is checked against the
  diff from the last indexed commit, including other people's commits (a new
  PR merged into the base). This covers most cases.
* An agent that finds the code different from what the index says reports
  it, and the area is reindexed.

## Event store (SQLite, embedded)

* **One event store per iteration** (the iteration's name is the branch's
  name), so that old iterations can be deleted. A catalog table holds:
  event store, session id, iteration name, start date, end date.
* Every event records the repository's commit sha and, for an agent turn,
  its tokens: a replay rebuilds the starting point.
* **Policies** react to events and send signals to the agents (a dirty
  index → kent verifies; a turn ended → the auditor).
* Resume = replay the events up to the last one; Ctrl-C is safe.
  `session-state` is no longer needed.
* **Replays for improvements and A/B tests of models**: an event's input is
  run again N times, and the outcomes are judged by the deterministic checks.
  The verdict is statistical (errors, complexity, tokens, compared across the
  runs).
* The flow log stays, only as a human-readable log.

## Commits

* beck commits every TDD phase after verifying it: the new test fails (red),
  then passes with no test changed (green).
* **Commit order with parallel unclebobs**: beck must guarantee the right
  order. Approved: the planned commits are events, not memory. Proposal to
  confirm: each parallel unclebob works in its own git worktree and beck
  commits there at once (the code is never left uncommitted); at the end of
  the component beck replays the commits onto the feature branch in the
  right order. martin then squashes the unit.
* **After the iteration ends** a flag turns on: beck makes no new commits,
  only fixups of the iteration's commits, which the user squashes. This holds
  for the user's corrections and, later, for the PR comments read with `gh`.
  Pushing stays manual.
* The user's final corrections: a new iteration, or by hand — the user's
  choice.

## Tests in the projects

* An interface over the machine-readable test report, so that a failure is
  extracted deterministically (test, assertion, line).
* Python: pytest's built-in `--junitxml=<path>`; `pytest-json-report` if
  JSON is needed.
* Elixir: the `junit_formatter` hex package (an ExUnit formatter, test-only
  dependency, configured in `test/test_helper.exs`; latest 3.3.0, little
  maintenance lately).
* C/C++: CTest `--output-junit <file>`; GoogleTest `--gtest_output=xml:<file>`.
  Unity (used by `c-scaffold`) has no native JUnit output: to verify (its
  repository ships a conversion script).
* Go: `go test -json` natively; `gotestsum --junitfile <file>` for JUnit.
* Rust: cargo-nextest, `[profile.<name>.junit] path = "junit.xml"` in
  `.config/nextest.toml` (written under `target/nextest/<profile>/`).
* **Resilience**: when no machine-readable report exists (the runner has
  none, the file is missing or unreadable), beck falls back to the agent
  transparently and logs a warning in the log file.
* unclebob runs only the tests of its cycle's ids (from the index); the
  whole suite runs once, after the integration unit. The auditor checks
  which tests each cycle ran.
* Whether a project's tests can run is checked once, at the start, by
  kent and the environment checker.

## Interview and framing

* A deterministic tool tells greenfield from brownfield: at least one code
  file means brownfield; a directory with only documents means asking.
* `scaffold init` stays, deterministic, only in a completely empty
  directory.
* The interview is mostly standard questions, kept in the event store; the
  branch is created (`linus branch`) only after it, its name proposed by an
  actor in the configured format.
* `toolchain.yml` is built deterministically from the stack, with the user's
  help, once per project.

## TUI

Textual, with tmux-like areas:

* a status bar: global tokens, the state machine's state, the active
  agents;
* a panel with the agents' current activity (a summary of the event
  stream);
* a panel with a horizontal histogram of the average tokens per cycle of
  each agent;
* the main panel: the prompt, the reports, the questions;
* at the end of each component, an ASCII graph of the components in the main
  panel: existing ones in the default colour, done in green, to do in red
  (`grandalf` for the layout, to try).

Driving beck from stdin stays possible, at little cost.

## Metrics

Tokens per agent turn, saved with the events; the average cost of a turn of
each agent, to know where to save; shown in the TUI.

## Drivers

An abstraction over the CLI running the agents: Claude Code and Copilot for
now.

## How beck itself is developed

Not in TDD: it is a tool, not production code. Tests written after the code
only on the deterministic core (event store, state transitions, the TDD
checker, the index), since they judge the agents; the TUI is tried by hand.
The tokens of the development sessions are measured to check that this
costs less than TDD. The replays act as integration tests.

## Event storming (big picture, draft)

Actors: (U) user, (B) beck deterministic, (A) agent.

1. **Framing:** ProjectClassified (B) → InterviewCompleted (U) →
   BranchNamed (A, configured format) → BranchCreated (B)
2. **Survey:** ToolchainDetected (B) → ToolchainConfirmed (U) →
   EnvironmentUp (B, A fallback) → SuiteVerified (B) → CodeAreaDelimited
   (A kent) → ShoppingListApproved (U)
3. **Model:** DomainWritten (A) → DomainValidated (B) →
   ArchitectureWritten (A) → InterfacesWritten (A) → FitnessFunctionsGenerated
   (B, A for the rest) → IndexBuilt (B, A anchors) → ModelApproved (U)
4. **Implementation, per group of spec ids:** CycleOpened (B, context cut
   from the index) → RedDeclared (A) → RedVerified (B) → CommitPlanned (B) →
   GreenDeclared (A) → GreenVerified (B) → CommitPlanned (B) → TestFailed →
   FailureSummarised (Haiku) → ScopeViolated (B or joshua) →
   InterfaceChangeRequested (A) → CommitsApplied (B, in order)
5. **Unit refactor:** RefactorDone (A martin) → RefactorInvariantsVerified
   (B) → UnitSquashed (B) → UnitClosed (B)
6. **Closing:** IntegrationFlowGreen (A + B) → FullSuiteGreen (B, once) →
   FixupModeOn (B) → IterationReviewed (U) → CorrectionsRequested (U) /
   IterationClosed (U)
7. **Cross-cutting:** AgentTurnEnded (B, tokens and sha) → SignalRejected
   (B) → IndexMarkedDirty (B) → InterruptionDetected (joshua) →
   ViolationLogged (B or joshua) → ImprovementProposed (argyris)

Next: correct the timeline, then add commands, policies and read models,
and only then the boundaries of the actors.

## Open points

* **TODO: a tool in the TUI to delete old event stores.**
* **Index staleness**: how to detect a time jump (the code changed under the
  index without any event). Reindexing at the start of each iteration covers
  about 90 %; the rest is handled as it comes.
* **A cycle that does not converge** (no green after N attempts, a red test
  that cannot be written because the spec is not testable as written): to
  decide. Proposal: a configurable limit per cycle, then a CycleBlocked event;
  beck parks the cycle, goes on with the independent work and reports it at
  the end.
* The parallel commit order: confirm the worktree proposal.
* The DSL author: does the domain phase still read no code?
* The configuration vs the existing `~/.config/minime/*.toml`.
* Later: PR comments with `gh`, Alloy and TLA+ stages, simon on demand.
