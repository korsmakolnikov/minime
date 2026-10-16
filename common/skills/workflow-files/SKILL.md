---
name: workflow-files
description: The control files of the agentic workflow - .sources/ (ADL, spec, components map, shopping lists), .documentation/, toolchain.yaml and the logs under /tmp - who writes each, who reads it, and why none of them is versioned. Load it before reading or writing any of them, or when a project's layout looks out of date.
---

# workflow-files

The workflow keeps its state in a few files beside the project's code. They
are its control centre: every agent reads its input there and writes its
output there, and nothing else.

## Never versioned

None of these files is committed, staged or mentioned in the project's
`AGENTS.md` or `CLAUDE.md`. The workflow is the user's personal experiment,
run on code that colleagues share and do not know about it; the files would
make sense in git only if others adopted the tool. The global git ignore
file lists `.sources/`, `.documentation/` and `toolchain.yaml`
(`minime-migrate` adds them); never add them to a project's `.gitignore`.

## In the project

| File | Written by | Read by | Holds |
|---|---|---|---|
| `toolchain.yaml` | kent (from the shopping list), the scaffold tool | the `toolchain` and `adl-graph` commands | language, container wrapper, replaced commands |
| `.sources/shopping_lists/<branch>.md` | kent, through `shopping-list` | every agent kent launches, as context | the iteration's goal, unknowns and answers |
| `.sources/spec.yaml` | hughes | ford, unclebob, martin, simon | the domain: entities, value objects, events, relations, constraints, operations, properties (`domain-model` skill) |
| `.sources/*.adl`, `.sources/as-is/*.adl` | ford | unclebob, martin, simon | the target and the as-is architecture (`adl-spec` skill) |
| `.sources/components.yaml` | ford | kent, unclebob, martin, simon | which component realizes each spec id, its module and its boundary |
| `.documentation/<branch>/` | simon | the user | the C4 workspace and the Mermaid diagrams |

## Under /tmp (one machine, one session at a time)

| File | Written by | Read by |
|---|---|---|
| `kent-flow.log` | every agent, through `flow-log`, and the hooks | the user (`tail -f`) |
| `kent-events.jsonl` | the stop hook, one line per sub-agent report | joshua (`events-query`) |
| `kent-guard.jsonl` | the guard hook, one line per refusal | joshua (`events-query --guard`) |
| `kent-partial-session-progress.md` | kent, through `session-state` | kent, to resume |
| `joshua.log` | joshua, through `audit-log append` | argyris (`audit-log pending`, `show`, `handled`, `archive`) |

## Old layouts

`minime-migrate` brings a project from an older layout to this one (`.adl/`
and `.shopping_lists/` into `.sources/`) and reports any file it cannot move
without overwriting. Every future change of layout is added there, never done
by hand.
