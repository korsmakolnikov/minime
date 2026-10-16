---
name: elixir-static-checks
description: The static checks of an Elixir project (formatter, linter, type checker), found from the project's own toolchain and run on the files a branch changed. Load it only when the project folder is in `projects` and only at a closing point - unclebob at the close of a unit, after the last change of a correction session, or when the user closes an interactive session; martin in review. Never inside a TDD cycle.
projects:
  - crash
tools:
  - mix format
  - mix credo
  - mix dialyzer
---

# elixir-static-checks

The static checks of an Elixir codebase, the same for every project in
`projects`. The skill names what to run; the project decides how it runs
(a container, a Make target, a mix alias).

## When it applies

* **Projects**: only a project whose folder name (the basename of the
  repository root, `git rev-parse --show-toplevel`) is listed in `projects`.
  Anywhere else, do not load it: report that no static-checks skill covers
  the project and run nothing.
* **Tools**: only the tools in `tools`. A check the project does not
  configure is skipped and logged, never added: no new dependency, no new
  `.credo.exs`, no new alias. A toolchain the skill does not support (a
  tool the project uses that is not in `tools`) is reported, not guessed.
* **Moments**: once per closing point, never inside a red, green or
  refactor. A cycle runs only its tests.

## Finding the toolchain

Read, in this order, and use the first that answers:

1. `AGENTS.md` (or `CLAUDE.md`, `CONTRIBUTING.md`): the documented commands
   or wrappers.
2. `Makefile`, `justfile`, scripts under `bin/` or `scripts/`: targets named
   after format, lint, credo, dialyzer, check.
3. `mix.exs` aliases (`check`, `lint`, `format`), and the deps that tell what
   is configured: `credo`, `dialyxir`. An umbrella (`apps_path`) runs the
   checks from the root.
4. Config files: `.formatter.exs`, `.credo.exs`, the `dialyzer:` key in
   `mix.exs`.

When the project runs in a container, use the project's own wrapper (the
Make target, `docker compose exec <service> …`) and run it directly, never
through `bash -c` or `sh -c`: the hooks and the user must be able to read the
command.

## The changed files

The files of the branch: `git diff --name-only $(linus base)...HEAD` plus the
working tree (`git status --porcelain`), only `.ex` and `.exs`, only files
that still exist. The checks judge these files; warnings elsewhere are left
alone.

## The checks, in order

1. **Formatter**: `mix format --check-formatted <changed files>`. On a
   failure, `mix format <changed files>` and show the resulting `git diff`.
2. **Linter**: `mix credo --strict <changed files>`, unless the project's
   own command passes other flags.
3. **Type checker**: `mix dialyzer`, on the whole program. It can take
   minutes (more the first time, while it builds the PLT): run it in the
   background, wait for it, never interrupt it. Keep only the warnings on
   lines the branch changed (`git diff -U0 $(linus base)...HEAD -- <file>`).

## The result

For each check: the command, whether it passed, and each finding kept as
`tool file:line message`. A finding fixed without changing behaviour
(formatting, a lint rule, a spec) is a fix of the closing point: the agent
commits it as its own instructions say (a fixup of the unit, or a refactor
in an interactive session). A fix that would change behaviour is a new TDD
cycle, starting with a red; run the check again after it.
