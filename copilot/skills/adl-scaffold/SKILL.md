---
name: adl-scaffold
description: Scaffolds the directories, namespace modules and component interfaces (signatures, types and docs, no logic) described by approved ADL files, for Elixir and Python projects. Use after the fitness functions for an ADL file exist.
---

# Scaffolding from ADL

Load `adl-spec` first. The scaffold makes the fitness functions pass and
defines the contracts unclebob will implement. **It contains no business
logic.**

## Precondition

The project's test runner must work. Run it before touching anything. If it
does not run, stop and report (for greenfield, propose `mix new` or `uv init`
and wait for approval).

## Structure

For each artifact, following the physical-name mapping:

**Elixir**
* Directory `lib/<path>/` and a namespace module at `lib/<path>.ex`
  (`defmodule Sysops.Ticketing do @moduledoc "<logical name>: …" end`).
* Components get their facade at `lib/<path>.ex`. Internals added later by
  unclebob go under `lib/<path>/`.

**Python**
* Package `<source root>/<path>/` with an `__init__.py` whose docstring names
  the logical artifact.
* The component's public interface is exported from its `__init__.py`.

## Interfaces (designed with the user through `adl-interview`)

Write only what crosses the component boundary:

| | Elixir | Python |
|---|---|---|
| Data | `defstruct` with `@type t` | `@dataclass(frozen=True)` with type hints |
| Facade | public `def` with `@doc` and `@spec`, body `raise "not implemented: <Module>.<fun>/<arity>"` | typed function with docstring, body `raise NotImplementedError` |
| Port | behaviour with `@callback`s and `@doc` | `typing.Protocol` with typed methods and docstrings |
| Errors | documented in `@spec` as `{:error, reason}` atoms | custom exception classes with docstrings |

* No private functions, no conditionals, no defaults that encode a business
  decision.
* Stubs must raise explicitly, so that unclebob's first test of each operation
  is a genuine red.
* Keep names and types exactly as approved in the interview.

## Verify

1. The project compiles (`mix compile --warnings-as-errors` / an import of
   every new package).
2. The architecture tests pass and the full suite runs.
