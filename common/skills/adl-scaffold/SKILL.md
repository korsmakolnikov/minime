---
name: adl-scaffold
description: Scaffolds the directories, namespace modules and component interfaces (signatures, types and docs, no logic) described by approved ADL files, for Elixir and Python projects. Use after the fitness functions for an ADL file exist.
---

# Scaffolding from ADL

Load `adl-spec` first. The scaffold makes the fitness functions pass and
defines the contracts unclebob will implement. **It contains no business
logic.**

## Precondition

Run the project's test runner before touching anything. If it does not run,
stop and report (for greenfield, propose `mix new` or `uv init` and wait for
approval).

## Structure

For each artifact, following the physical-name mapping:

* **Elixir**: directory `lib/<path>/` and a namespace module at
  `lib/<path>.ex`
  (`defmodule Sysops.Ticketing do @moduledoc "<logical name>: …" end`); a
  component's facade is `lib/<path>.ex`, and unclebob's internals go under
  `lib/<path>/`.
* **Python**: package `<source root>/<path>/` whose `__init__.py` docstring
  names the logical artifact and which exports the component's public
  interface.

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
* Stubs raise explicitly, so that unclebob's first test of each operation is
  a genuine red.
* Names and types exactly as approved in the interview.

## Verify

1. The project compiles (`mix compile --warnings-as-errors` / an import of
   every new package).
2. The architecture tests pass and the full suite runs.
