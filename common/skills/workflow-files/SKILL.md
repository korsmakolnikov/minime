---
name: workflow-files
description: The control files of the agentic workflow - .sources/ (ADL, spec, components map, shopping lists), .documentation/, toolchain.yaml and the logs under /tmp - who writes each, who reads it, and why they are versioned on Claude Code and never on Copilot. Load it before reading or writing any of them, or when a project's layout looks out of date.
---

# workflow-files

The workflow keeps its state in a few files beside the project's code. They
are its control centre: every agent reads its input there and writes its
output there, and nothing else.

## Versioned on Claude Code, never on Copilot

* **Claude Code** (the user's personal and open-source projects): the files
  are versioned. The agents write them and kent commits them with `linus`,
  only between units (`docs(workflow): …`), so they never fall inside a unit
  martin squashes; `linus squash` ignores their uncommitted changes. marvin
  may point to them in `AGENTS.md`.
* **Copilot** (code shared with colleagues who do not know about the
  experiment): never committed, staged or mentioned in `AGENTS.md`. The
  global git ignore file of that machine lists `.sources/`,
  `.documentation/` and `toolchain.yaml` (`minime-migrate
  --ignore-workflow-files`, run by `make update`), and `linus` refuses them
  there. Never add them to a project's `.gitignore`.

## In the project

| File | Written by | Read by | Holds |
|---|---|---|---|
| `toolchain.yaml` | the scaffold tool (a new project, run by ford), kent (an existing one) | the `toolchain` and `adl-graph` commands | language, container wrapper, replaced commands |
| `toolchain.yaml` at the root, for a project in a folder | the scaffold tool | the same commands | only `project: <folder>`: where the project is |
| `.sources/shopping_lists/<branch>.md` | kent, through `shopping-list` | every agent kent launches, as context | the iteration's goal, unknowns and answers |
| `.sources/spec.yaml` | hughes | ford, unclebob, martin, simon | the domain: entities, value objects, events, relations, constraints, operations, properties (`domain-model` skill) |
| `.sources/*.adl`, `.sources/as-is/*.adl` | ford | unclebob, martin, simon | the target and the as-is architecture (`adl-spec` skill) |
| `.sources/components.yaml` | ford | kent, unclebob, martin, simon | which component realizes each spec id, its module and its boundary |
| `.documentation/<branch>/` | simon | the user | the C4 workspace and the Mermaid diagrams |

## The logs (one folder per repository, outside it)

On Claude Code in `~/.local/state/minime/<repository>/` (`$MINIME_STATE_DIR`
moves it; kent-loop uses its own); on Copilot still under `/tmp`. Folders
untouched for 30 days, and the oldest beyond 100 MB in all, are removed at
the start of a session: the events point to Claude Code's transcripts, which
it keeps 30 days too. argyris runs in `~/code/minime`, so it names the
repository it reads: `audit-log repos`, then `--repo <name>` on every
`audit-log` and `events-query` call.

| File | Written by | Read by |
|---|---|---|
| `kent-flow.log` | every agent, through `flow-log`, and the hooks | the user (`tail -f`) |
| `kent-events.jsonl` | the stop hook, one line per sub-agent turn: the signal, the model's usage (requests and tokens) and what replays the turn (branch, HEAD, session, launch prompt, transcript) | joshua (`events-query`), the user and argyris, to replay an iteration |
| `kent-errors.jsonl` | the guard (refusals), the stop hook (failed signals), joshua and martin through `audit-log append` (violations), argyris (`handled`) | joshua (`events-query --errors`, `--guard`), argyris (`audit-log pending`, `show`, `handled`, `archive`) |
| `kent-partial-session-progress.md` | kent, through `session-state` (and `/save-session`) | kent, to resume |

## Old layouts

`minime-migrate` brings a project from an older layout to this one (`.adl/`
and `.shopping_lists/` into `.sources/`) and reports any file it cannot move
without overwriting. Every future change of layout is added there, never done
by hand.
