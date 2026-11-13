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
* **Structured output.** Every agent answers in a structured format with a
  schema, so that beck can check as much as possible deterministically
  (a repeated failure pattern, a declared scope, a signal); an output that
  does not match its schema is rejected (`SignalRejected`).
* **Event storming before design.** The domain of the workflow is modelled
  from its events first; the actors and their boundaries come after, and the
  old agents' boundaries are not sacred.
* **Agents never commit.** beck commits, after checking each TDD phase
  deterministically.
* **Agents never search the code twice.** The index maps every DSL id to the
  code and the tests; beck hands each agent only the slice it needs.
* **The user is the architect at the start and the reviewer at the end**,
  not a reviewer of every unit: the workflow can run overnight, and on
  holidays. What it cannot solve alone it parks, with a proposal, and goes on
  with the rest.
* **Event sourcing.** Everything that happens is an event; state, resume,
  policies, audits, metrics and replays all read the events.
* **KISS.** No layer, abstraction or option without a concrete need today.

## Configuration

* `~/.config/beck/config.yml`: global defaults. Anything tied to a work
  environment lives only here, never in this repository.
* `.beck/config.yml` in the project: extends and overrides the global one.
* The old `~/.config/minime/*.toml` (`minime-config`) stays with the old
  workflow; beck does not read it.
* Settings so far:
  * whether `.beck/` is versioned (replaces the old rule "versioned on
    Claude Code, never on Copilot", which no longer holds once Claude Code
    runs on company code);
  * the branch name format (when it contains a task code, the user gives it);
  * the model of each actor;
  * the token budget, per agent session and per iteration (infinite allowed:
    first we measure);
  * the limits of a cycle (see "Blocked cycles"): 3 repetitions of a
    pattern, 30 attempts;
  * the CLI driver (Claude Code, Copilot).

## Project layout: `.beck/`

Everything beck needs lives in `.beck/`; the old `.sources/`,
`.documentation/`, `.adl/` and `.shopping_lists/` are ignored
(`minime-migrate` is dropped).

* `config.yml`
* shopping lists, one per branch
* the DSLs: the domain spec and the architecture (YAML); no components map
* `toolchain.yml` (to decide whether it moves here from the project root)
* `index.db`: the DSL-to-code index (derived, never versioned)
* the event stores (never versioned)

When versioned, beck commits `.beck/` itself (`docs(workflow): …`), only
between units; no agent is needed for it.

## Actors (draft)

| Actor | What | Notes |
|---|---|---|
| beck | the state machines, the policies, the commits, the deterministic checks, the TUI | no LLM |
| kent (inside beck) | studies the existing code and delimits the area the iteration touches; brings the environment up from the project's docs (`AGENTS.md`, README, Makefile); writes the shopping list; is the DSL author: the domain, then the architecture and the interfaces (hughes and ford merged); anchors the spec ids to the code; keeps the DSLs in sync with the code; proposes the resolution of a blocked cycle or of an interface change | name kept from Kent Beck; never runs together with the old `kent` agent; the domain and the architecture are two states of the machine, each with a fresh context and its own approval; in brownfield it reads the code, only the slice of the delimited area the index hands it |
| unclebob | TDD, one group of spec ids per session, context cut by the index | N in parallel, one unit each, in its own worktree; may request an interface change |
| martin | refactors the unit on green tests and closes it on its own; resolves the conflicts when its unit lands | runs in parallel with the unclebobs; no new tests (temporary benchmarks only); outside the unit only code covered by tests; missing tests send the work back to unclebob; may request an interface change, never makes one |
| joshua | audits only what the deterministic auditor cannot decide: interruptions, tooling violations, scope of the tests run; watches every `SignalRejected` and how the parallelism stalls | fed by events, at least per cycle |
| argyris | improves the agents, triggered by events; runs replays and A/B tests of models; with joshua, tunes the parallelism | |
| test reader | on Haiku: summarises a failure for unclebob | only when the deterministic parser is not enough |
| environment checker | is the environment up? deterministic from the container status, Haiku as fallback on long logs | |

Removed: **hughes** and **ford** (merged into kent), **simon** (its output
was never used; may return on demand), **marvin** (`AGENTS.md` updates
proved harmful; later, `AGENTS.md` will import the DSLs), **the old kent**
(after fade-out).

## DSLs

* **ADL dropped**, replaced by a YAML architecture DSL in the style of the
  domain spec, keeping ADL's features (the kinds of `DEFINE`, `ASSERT`,
  `FOREACH`), with an id on every element and every assertion.
* **No components map**: which component realizes each spec id is written
  in the architecture YAML (a design decision, so it lives in a versioned
  source); the index derives the rest down to the code.
* The domain and the architecture are two parallel branches of the model,
  each with its own approval; in practice they run in sequence (the
  architecture is derived from the domain, and the user, who reads and
  discusses both, is the bottleneck).
* The fitness functions are generated deterministically from the
  assertions; an agent writes only those the generator cannot translate.
* Future stages, not in the first iteration: Alloy and TLA+ where they make
  sense.

## Index (SQLite, embedded)

* Maps spec id → component → symbols (functions, modules) → tests.
  Symbols from tree-sitter (Elixir, Python, C grammars).
* Few heavy writes (when the DSLs are created), then small updates; mostly
  reads, graph walks with `WITH RECURSIVE`.
* The index is derived: beck rebuilds it deterministically, kent anchors the
  ids to the symbols where needed. The DSLs are design decisions: kent
  proposes their changes, the user approves them.
* Each file is tracked by content hash; a commit event marks the index of
  its files dirty, and a policy has kent verify them.
* **At the start of every iteration** the whole map is checked against the
  diff from the last indexed commit, including other people's commits (a new
  PR merged into the base). This covers most cases. When the diff changes
  the behaviour of code that realizes spec ids, the DSLs have drifted: kent
  proposes how to bring them back in sync, the user approves, beck rebuilds
  the index.
* An agent that finds the code different from what the index says reports
  it, and the area is reindexed.

## Event store (SQLite, embedded)

* **One event store per iteration.** It is created as soon as a session
  starts, with a random id; when the branch is created, the catalog records
  the iteration's name (the branch's name). Old iterations can be deleted.
  The catalog table holds: event store, session id, iteration name, start
  date, end date.
* `beck sessions` lists the event stores of the project (id, branch, start,
  end, last event); `beck attach <id>` resumes one, replaying its events up
  to the last. Ctrl-C is safe; `session-state` is no longer needed.
* Every event records the repository's commit sha and, for an agent turn,
  its tokens: a replay rebuilds the starting point.
* **Policies** react to events and send signals to the agents (a dirty
  index → kent verifies; a turn ended → the auditor).
* **Replays for improvements and A/B tests of models**: an event's input is
  run again N times, and the outcomes are judged by the deterministic checks.
  The verdict is statistical (errors, complexity, tokens, compared across the
  runs). The replays also tune what can only be tuned on real data, such as
  the normalisation of the failure signatures.
* The flow log stays, only as a human-readable log.

## Parallelism and commits

* **As parallel as possible.** Every unit (a component, the integration
  flow) gets its own git worktree, branched from the feature branch once the
  interfaces are committed. N unclebobs work on different units at once, and
  martin refactors the finished units beside them.
* An unclebob does not wait for the components its unit depends on: it
  trusts the declared interfaces, which is what they are for. The
  integration unit at the end exists to find where the components diverge
  from the interfaces.
* beck commits every TDD phase in the unit's worktree as soon as it has
  verified it: the new test fails (red), then passes with no test changed
  (green). The code is never left uncommitted.
* martin squashes the unit in its worktree; beck then lands the squashed
  commit on the feature branch, in the dependency order of the architecture.
  Since every unit lands as one commit, no single commit needs reordering.
  A landing that conflicts (shared files: dependencies, the supervision
  tree) goes back to martin, then through the checks again.
* It is not expected to work well at first: joshua measures, from the
  events, how long each unit waits, the conflicts at landing and the
  divergences found by the integration, and argyris and the user tune it.
* **After the iteration ends** a flag turns on: beck makes no new commits,
  only fixups of the iteration's commits, which the user squashes. This holds
  for the user's corrections and, later, for the PR comments read with `gh`.
  Pushing stays manual.
* The user's final corrections: a new iteration, or by hand — the user's
  choice.

## Blocked cycles

* Every attempt of a cycle ends with a **failure signature**, computed
  deterministically from the structured test report and the agent's
  structured output: the normalised set of (test, kind of failure, assertion
  message), without line numbers, addresses and times.
* beck looks at the tail of the sequence of signatures: a block of length p
  repeated 3 times in a row blocks the cycle. p = 1 is the same result three
  times; p ≥ 2 is a repeated pattern (A B A B A B).
* With no repetition, the cycle blocks after 30 attempts.
* The rule is not only for TDD: it applies to every loop between an agent
  and a deterministic check (`DomainInvalid ⟲ WriteDomain`,
  `InterfacesBroken ⟲ WriteInterfaces`, …). A loop triggered by the user
  (`Revise…`) has no limit.
* Both limits are in the configuration. The normalisation is the delicate
  part (too coarse blocks too early, too fine never sees a repetition): it
  starts as above and is tuned with the replays.
* A blocked cycle does not stop the machine: beck parks it and the cycles
  that depend on it, goes on with the independent work, and has kent propose
  a resolution, which waits for the user. When nothing else can proceed, the
  machine stops, and that is correct.
* An **interface change** follows the same path. It can be requested during
  the iteration by unclebob (a signature lacks a datum the operation needs,
  an error case is not in the return type, a property of the spec cannot be
  observed through the public interface), by martin (an interface too wide
  or leaking its implementation: changing a contract changes the tests, so
  martin requests it, never makes it), or by the integration unit (a
  divergence between components). The work in flight on the components that
  use that interface is parked too.

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
* `.beck/` does not count: a directory holding only `.beck/` is empty.
* `scaffold init` stays, deterministic, only in an empty directory. It runs
  `git init`, so in greenfield the branch is created after it.
* The interview is mostly standard questions, kept in the event store; kent
  may add follow-up questions. The branch is created (`linus branch`) only
  after it: an actor proposes its name in the configured format, the user
  confirms it.
* **The first iteration of beck on a brownfield project** has no DSLs: kent
  writes them for the delimited area only, the as-is first, then the
  iteration's changes on top.
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
each agent, to know where to save; shown in the TUI. The parallelism
measures (waits, conflicts at landing, divergences at integration) come from
the events too.

## Drivers

An abstraction over the CLI running the agents: Claude Code and Copilot for
now.

## How beck itself is developed

Not in TDD: it is a tool, not production code. Tests written after the code
only on the deterministic core (event store, state transitions, the TDD
checker, the index), since they judge the agents; the TUI is tried by hand.
The tokens of the development sessions are measured to check that this
costs less than TDD. The replays act as integration tests.

## Read models

No projection is persisted, and they are not an architectural concept:
they are functions that fold the events into a state, called by the
policies and by the TUI. They are named only where a policy needs one:

* the state of the machine (where `beck attach` resumes);
* the sequence of the failure signatures of a loop (the repetition rule);
* which units are ready to land and which are parked;
* the TUI and the metrics (tokens per agent, the histogram, the graph of the
  components, the parallelism measures for joshua);
* the catalog (`beck sessions`).

## Event storming (big picture)

Actors: (U) user, (B) beck deterministic, (A) agent. Each phase has a main
line, read left to right; the branches (`↳`) leave from the event they
hang under and either return to an earlier event (`⟲`) or stop the line.
Every branch becomes a transition of the state machine.

The approved phases also list their commands and policies:
`Command (who) → Event`, and `P: Event → Command` for a policy, which
carries the signal from one actor to the next. `[…]` is a condition read
from a read model; `⟲` returns to an earlier command.

### 1. Session and framing (approved)

```
StartSession (U: beck)                     → SessionStarted (B: event store with a random id, catalog row)
P: SessionStarted → LoadConfig (B)         → ConfigLoaded | ConfigInvalid (stop)
P: ConfigLoaded → ClassifyProject (B)      → ProjectClassified {greenfield | brownfield | undetermined}
P: [undetermined] → AskClassification (B→U)
   ClassifyProject (U)                     → ProjectClassified
P: ProjectClassified → AskQuestion (B: the standard questions; A kent: the follow-ups)
   AnswerQuestion (U)                      → QuestionAnswered
P: [no question pending]                   → InterviewCompleted (B)
P: InterviewCompleted [greenfield] → ScaffoldProject (B) → ProjectScaffolded (git init, toolchain.yml)
P: InterviewCompleted [brownfield] | ProjectScaffolded
   → ProposeBranchName (A)                 → BranchNameProposed
   ConfirmBranchName (U)                   → BranchNamed
P: BranchNamed → CreateBranch (B)          → BranchCreated (iteration name in the catalog)
AttachSession (U: beck attach <id>)        → SessionAttached (replay, resume from the pending command)
```

### 2. Survey (approved)

```
P: BranchCreated [toolchain.yml present] → LoadToolchain (B)   → ToolchainLoaded
P: BranchCreated [toolchain.yml absent]  → DetectToolchain (B) → ToolchainDetected
   ConfirmToolchain (U)                                        → ToolchainConfirmed
P: ToolchainLoaded | ToolchainConfirmed
   → BringEnvironmentUp (B, A kent fallback from the docs)     → EnvironmentUp | EnvironmentDown (stop)
P: EnvironmentUp → VerifySuite (B)       → SuiteVerified {machine-readable report: yes | no} | SuiteFailed (stop)
P: SuiteVerified [brownfield, index present] → ReconcileIndex (B) → IndexReconciled | DslDriftDetected
P: DslDriftDetected → ProposeDslSync (A kent)  → DslSyncProposed
   ApproveDslSync (U)                          → DslSyncApproved
P: DslSyncApproved → RebuildIndex (B)          → IndexRebuilt
P: IndexReconciled | IndexRebuilt | SuiteVerified [brownfield, no index]
   → DelimitCodeArea (A kent)                  → CodeAreaDelimited
P: CodeAreaDelimited | SuiteVerified [greenfield]
   → WriteShoppingList (A kent)                → ShoppingListWritten
   ApproveShoppingList (U)                     → ShoppingListApproved
   ReviseShoppingList (U)                      → ShoppingListRevised ⟲ WriteShoppingList
```

### 3. Model (approved)

Two branches, each a state of kent with a fresh context and its own
approval; in practice the domain comes first. While writing, kent asks the
user (`QuestionAsked` (A) ⟷ `QuestionAnswered` (U)). Every `⟲` triggered by
a check follows the repetition rule of "Blocked cycles".

```
P: ShoppingListApproved → WriteDomain (A kent, fresh context) → DomainWritten
P: DomainWritten → ValidateDomain (B, spec-check)  → DomainValidated | DomainInvalid ⟲ WriteDomain {the errors}
   ApproveDomain (U)                               → DomainApproved
   ReviseDomain (U)                                → DomainRevised ⟲ WriteDomain
P: DomainApproved → WriteArchitecture (A kent, fresh context) → ArchitectureWritten
P: ArchitectureWritten → ValidateArchitecture (B: the schema, every spec id realized by exactly one component)
                                                   → ArchitectureValidated | ArchitectureInvalid ⟲ WriteArchitecture
P: ArchitectureValidated → WriteInterfaces (A kent) → InterfacesWritten
P: InterfacesWritten → CompileInterfaces (B)       → InterfacesCompiled | InterfacesBroken ⟲ WriteInterfaces
P: InterfacesCompiled → GenerateFitnessFunctions (B) → FitnessFunctionsGenerated {the untranslated assertions}
P: [untranslated ≠ ∅] → WriteFitnessFunctions (A kent) → FitnessFunctionsWritten
P: FitnessFunctionsGenerated [untranslated = ∅] | FitnessFunctionsWritten
   → RunFitnessFunctions (B)                       → FitnessFunctionsPassed | FitnessFunctionsFailed ⟲ WriteInterfaces
   ApproveArchitecture (U)                         → ArchitectureApproved (requires DomainApproved)
   ReviseArchitecture (U)                          → ArchitectureRevised ⟲ WriteArchitecture
P: ArchitectureApproved → BuildIndex (B)           → IndexBuilt {the unanchored ids}
P: [unanchored ≠ ∅] → AnchorIds (A kent)           → IdsAnchored
P: IndexBuilt [unanchored = ∅] | IdsAnchored → PlanUnits (B)
                                                   → UnitsPlanned (units, groups of spec ids, dependency and landing order)
P: UnitsPlanned → CommitModel (B)                  → ModelCommitted (interfaces and fitness functions on the
                                                     feature branch; .beck/ too when versioned)
```

Cross-cutting, from phase 1: `P: AgentTurnEnded | SignalRejected → AuditTurn (joshua)`.

### 4. Implementation (per unit, in its own worktree, units in parallel)

```
UnitStarted (B: worktree from the feature branch)
→ for each group of spec ids:
    CycleOpened (B, context cut from the index)
    → RedDeclared (A unclebob) → RedVerified (B) → RedCommitted (B)
    → GreenDeclared (A unclebob) → GreenVerified (B) → GreenCommitted (B)
    → CycleClosed (B)
→ UnitImplemented (B)
```

* ↳ `RedRejected` (B: the test passes, or does not compile for another
  reason) ⟲ `RedDeclared`.
* ↳ `GreenRejected` (B: a test still fails, or a test was changed)
  → `FailureSummarised` (B parser, Haiku fallback) ⟲ `GreenDeclared`.
* ↳ `ScopeViolated` (B, or joshua) ⟲ the declared phase.
* ↳ `CycleBlocked` (B: a repeated pattern, or 30 attempts)
  → `DependentsParked` (B) → `ResolutionProposed` (A kent)
  → `ResolutionApproved` (U) → `CycleReopened` (B) ⟲ `CycleOpened`;
  or `ResolutionRejected` (U) → the user decides.
* ↳ `InterfaceChangeRequested` (A unclebob) → `DependentsParked` (B)
  → `ResolutionProposed` (A kent) → `ResolutionApproved` (U)
  → `InterfacesChanged` (B commits them) → the parked cycles reopen.

### 5. Unit refactor (martin, in the unit's worktree, beside the other units)

```
UnitMeasured (B, A for what cannot be measured) → RefactorDone (A martin)
→ RefactorInvariantsVerified (B) → UnitSquashed (B)
→ UnitLanded (B, on the feature branch, in dependency order) → UnitClosed (B)
```

* ↳ `RefactorRejected` (B: a test failed or changed, a measure got worse)
  ⟲ `RefactorDone`.
* ↳ `MissingTestsFound` (A martin) → back to unclebob ⟲ `CycleOpened`.
* ↳ `InterfaceChangeRequested` (A martin) → the path of phase 4.
* ↳ `LandingConflicted` (B) → `ConflictResolved` (A martin)
  → `RefactorInvariantsVerified` ⟲ `UnitLanded`.

### 6. Integration and closing

The integration flow is the last unit: it goes through phases 4 and 5 like
the others and ends with `UnitClosed`.

```
FullSuiteGreen (B, once) → StaticChecksPassed (B) → FixupModeOn (B)
→ IterationReviewed (U) → IterationClosed (U)
```

* ↳ a divergence between components in the integration unit
  → `InterfaceChangeRequested` (phase 4).
* ↳ `FullSuiteFailed` (B) → the index maps the failing tests to the units
  → `CycleOpened` on them.
* ↳ `StaticChecksFailed` (B) → `StaticFixesProposed` (A martin)
  → fixups of the units' commits (B).
* ↳ `CorrectionsRequested` (U) → fixups (B), or a new iteration, or by
  hand: the user's choice.

### 7. Cross-cutting

* `AgentTurnEnded` (B, tokens and sha) → the auditor's policy.
* `SignalRejected` (B: an output that does not match its schema) → joshua.
* `IndexMarkedDirty` (B) → `IndexVerified` (A kent).
* `IndexDiscrepancyReported` (A) → `IndexRebuilt` (B).
* `TokenBudgetExceeded` (B).
* `SessionInterrupted` (B, Ctrl-C) / `SessionAttached` (B).
* `EnvironmentDown` (B), at any time.
* `InterruptionDetected` (joshua), `ViolationLogged` (B or joshua).
* `ImprovementProposed` (argyris).

Next: the commands and policies of phases 4 and 5 (implementation and
refactor), then phase 6 (integration and closing), each approved in turn;
then the boundaries of the actors and the state machines, then the code.

## Open points

* **TODO: a tool in the TUI to delete old event stores.**
* **Index staleness**: how to detect a time jump (the code changed under the
  index without any event). Reindexing at the start of each iteration covers
  about 90 %; the rest is handled as it comes.
* Whether `toolchain.yml` moves into `.beck/`.
* The normalisation of the failure signatures: tuned with the replays.
* Unity's JUnit output; `grandalf` for the TUI's graph.
* Later: PR comments with `gh`, Alloy and TLA+ stages, simon on demand.
