# Shopping list: deterministic-workflow

## Goal

Reproduce kent's architecture-first workflow as a deterministic, code-driven
workflow in Python. It lives in a new top-level folder of minime,
`deterministic-kent/`, beside `claude/`, `copilot/` and `common/`, as a project
of its own: its own `pyproject.toml`, managed with uv. This iteration delivers
the requirements and the choice of the framework; the domain and the
architecture follow.

## Context (verified)

- The idea is already planned: `claude/NEXT_ITERATION.md` ("LangGraph version,
  with common metrics for the comparison") and `copilot/NEXT_ITERATION.md`
  (kent is the weakest link, a procedure of about 400 lines followed by a
  model; a state machine would make the order of the phases and the
  validation of the signals deterministic).
- CLAUDE.md: the code-driven version decides at runtime, through a flag,
  whether the workflow files are versioned (the Claude rule) or never
  versioned (the Copilot rule).
- Reusable assets: the tools in `common/bin` on `common/lib/minime`, the 14
  signal schemas in `common/signals`, the agent files in `claude/agents` and
  `copilot/agents`, the guard rules in `claude/hooks/guard.py`.

## Requirements (agreed)

1. The code owns the order of the phases: steps 0 to 7, the loop over the
   components, the review loop of each unit with its iterations, the routing
   of DOMAIN_CHANGE_REQUEST and INTERFACE_CHANGE_REQUEST. An agent can be
   resumed with its whole context.
2. Signals are typed output, validated against the schemas in
   `common/signals`, with retries on invalid output.
3. Each node sees only its own tools: the guard becomes the node's allowlist.
4. The commits of the workflow files between units, and durable checkpoints
   that replace `session-state`.
5. One agent-runner interface with implementations chosen at runtime by a
   flag: driving the existing CLIs (`claude -p`, `copilot -p`) as
   subprocesses, and an in-process agent loop, provider-agnostic.
6. Providers from day one: Anthropic, GitHub Copilot (through its CLI only),
   local models (Ollama or OpenAI-compatible servers). OpenAI is not
   required.
7. The user interacts through a terminal CLI: ASK_USER questions relayed
   verbatim; the run can be interrupted and resumed.
8. Minimal metrics per agent turn (tokens, cost, duration, outcome of the
   signal validation, questions asked) as JSONL, compatible with
   `/tmp/kent-events.jsonl`.
9. The workflow keeps its own copy of the agent files of `claude/agents` and
   `copilot/agents`, with its own version of the prompts (how they differ
   from the originals is for the domain to settle).
10. Out of the first version: joshua and simon in background.
11. The unit loop of 23 October 2026 (`claude/NEXT_ITERATION.md`, "Il nuovo
    flusso delle unità"): unclebob writes `test:`/`feat:` cycles with no
    refactor; martin checks the order (`unit-audit`), measures the unit at
    time zero, refactors the tests then the code and asks before keeping a
    worse measure; the run then waits for the user's review of the unit
    (an interrupt), and martin squashes after the approval; at the end the
    user reviews the whole flow.
12. Bounded contexts: the code launches an agent with only what its step
    needs, built deterministically from the repository (the components map,
    the interfaces, the unit's commit range) and the run's state, never from
    another model's memory. One unclebob per test, or per operation, is to
    be measured against one per component; the orchestrator costs no tokens.
13. The run's state lives in the checkpoint (the components and their
    state, the unit under review, the user's answers), not in an agent's
    context.
14. The cost per agent turn (requests, input, cache and output tokens,
    model) is logged as in `kent-events.jsonl`, so that the deterministic
    and the agentic workflow can be compared on the same project. The
    experiment's aim: small problems that cheaper or local models can solve;
    unclebob stays on Opus until the workflow is stable.

## Decisions (21 October 2026)

- Framework: LangGraph for the orchestration (the phases, interrupts for
  ASK_USER, the checkpointer), pydantic-ai as the in-process runner (typed
  output with retries, toolsets per agent, the Anthropic and Ollama or
  OpenAI-compatible providers). The user chose it over the research's
  recommendation (plain Python state machine plus pydantic-ai).
- Constraint that follows: on resume LangGraph runs the interrupted node
  again from the start, so every agent launch and every commit sits in a
  node that is idempotent or separate from the interrupt.
- In-process resume: each agent's pydantic-ai conversation is serialised
  beside the run's state, the equivalent of the CLIs' `--resume`.
- Copilot only through its CLI: pydantic-ai's `github-copilot:` provider is
  excluded (it imitates the VS Code client; unclear terms; company code).
- `claude -p` runs with `--bare`: no project hooks, CLAUDE.md or MCP; the
  node grants its tools with `--tools` and `--allowedTools`.
- The LangGraph checkpoint (SQLite) lives under `/tmp`, one file per
  session, like the logs; never versioned.
- Provider and model are configurable per agent role, in a configuration
  file; no automatic fallback.
- The Copilot spike is postponed: Copilot's company tokens cannot be used on
  this machine (`claude/NEXT_ITERATION.md`, "Ricerche"). The Copilot runner
  is designed on the interface, its parser validated later.
- The sub-project: `toolchain` reads a `toolchain.yaml` at the repository
  root whose `project: deterministic-kent` makes its driver work in that
  sub-folder (done in `common/lib`, with tests in `tests/`), and `minime` is
  listed in `projects` of `python-handbook` (done).
- Who: the flow of a new project in a folder. hughes writes the domain
  first; then ford asks the technology questions and scaffolds with
  `scaffold python --dir deterministic-kent`, which also writes the root
  `toolchain.yaml` (`project: deterministic-kent`) and the sub-project's CI
  in the root `.github/workflows/`, then `scaffold verify` and `scaffold
  commit`, before the ADL and the interfaces.

## Stack and harness

- Python, uv, a `pyproject.toml` in `deterministic-kent/`. Python package:
  `deterministic_kent`. Scaffolded by ford with `scaffold python --dir
  deterministic-kent` from the repository root.
- Property-based testing: Hypothesis, if and when it is needed.
- The existing tools run on the system `python3` and the standard library;
  `make test` runs `python3 -m unittest discover -s tests`. The new project
  must not add dependencies to them.
- Verified: `toolchain` and its Python driver work on the repository root
  (`pyproject.toml`, `src/`, `tests/` and the commands' working directory);
  `toolchain show` finds no project there until the scaffold writes the
  root `toolchain.yaml`. `python-handbook` applies only to the repositories
  listed in its `projects` field, `minime` among them.

## Framework research (21 October 2026, web research, summarised)

- Claude Code CLI: `-p --agent X --output-format json --json-schema` validates
  the output and retries; the result carries `structured_output`,
  `session_id`, `usage`, `total_cost_usd`; `--resume <id>`; `--tools`,
  `--allowedTools`. Always check that `structured_output` is present.
- Copilot CLI: `-p`, `--output-format=json` (JSONL events), `--agent`,
  `--resume`, `--allow-tool`, `--deny-tool`, `--no-ask-user`; no
  `--json-schema`, and the JSONL fields are undocumented: the signal must be
  parsed and validated by us.
- LangGraph 1.2.16 (MIT): graphs, `interrupt()` with `Command(resume=…)`,
  SQLite and Postgres checkpointers; a broad `try/except` swallows an
  interrupt; subgraphs have their own checkpoint namespace.
- pydantic-ai 2.59 (MIT, V2 stable since June 2026, fast release pace: pin
  the version): native typed output with retries, toolsets per agent,
  providers `anthropic:`, `ollama:`, OpenAI-compatible; conversations
  serialisable for resuming; `result.usage()` for the tokens.
- Discarded: Claude Agent SDK (Claude only), OpenAI Agents SDK (OpenAI
  centred, LiteLLM compromised on PyPI on 24 March 2026), Burr (no model
  layer, small community).

## Open questions

None for now.

## Agent instructions (for marvin)

- CLAUDE.md should state that `deterministic-kent/` is a third side, a uv
  project of its own, and how to run its tests.
