---
name: elixir-handbook
description: How to work on an Elixir project - find its toolchain, build it, run one test, the tests that include a file and the tests related to a branch, run the static checks (formatter, Credo, dialyzer), and the user's personal style rules. Load it whenever you build, test, check, write or review Elixir code in a project listed in `projects`; unclebob, martin, kent and the other agents share it.
projects:
  - crash
tools:
  - mix
  - mix test
  - mix format
  - mix credo
  - mix dialyzer
---

# elixir-handbook

What every agent needs to know about an Elixir codebase, in one place: the
agents say **what** to run and **when** (a cycle, a closing point, a
review); this skill says **how**, for Elixir. Another language has its own
`<language>-handbook`.

## When it applies

* **Projects**: only a project whose folder name (the basename of the
  repository root, `git rev-parse --show-toplevel`) is listed in `projects`.
  Anywhere else, do not load it: say that no handbook covers the project and
  ask how to build and test it.
* **Tools**: only the tools in `tools`, and only those the project actually
  uses. A project built with another toolchain (rebar3, erlang.mk, a Nix or
  Bazel build) is reported, never forced into `mix`. A check in `tools` the
  project does not configure (no `credo` or `dialyxir` dependency, for
  example) is skipped and logged, never added: no new dependency, no new
  `.credo.exs`, no new alias.

## Finding the toolchain

Read, in this order, and use the first that answers:

1. `AGENTS.md` (or `CLAUDE.md`, `CONTRIBUTING.md`): the documented commands
   or wrappers.
2. `Makefile`, `justfile`, scripts under `bin/` or `scripts/`: targets named
   after test, build, format, lint, credo, dialyzer, check.
3. `mix.exs` aliases (`test`, `check`, `lint`, `format`), and the deps that
   tell what is configured: `credo`, `dialyxir`. An umbrella (`apps_path`)
   runs the checks from the root.
4. Config files: `.formatter.exs`, `.credo.exs`, the `dialyzer:` key in
   `mix.exs`.

When the project runs in a container, use the project's own wrapper (the
Make target, `docker compose exec <service> …`) and run it directly, never
through `bash -c` or `sh -c`: the hooks and the user must be able to read the
command.

* **Never interrupt** a `mix` run (no Ctrl-C, no kill of its shell): an
  interrupted BEAM can hang on its BREAK menu inside the container and block
  everything. Run long ones in the background and wait for them.
* Never fetch dependencies or install anything (`mix deps.get`, `mix
  archive.install`, a PLT download) without the user's approval.

## Building

* The project's documented build command, or `mix compile` in the
  environment the tests use (`MIX_ENV=test`, set by `mix test` itself).
* An umbrella (`apps_path` in the root `mix.exs`) builds from the root.

## Running tests

Never run `mix test` without paths: that is the full suite, and the CI runs
it.

* **One test**: `mix test <test file>:<line>`.
* **A list of files**: `mix test <file> <file> …`, one invocation.
* **The tests that include a file**:
  * a test file: the file itself;
  * a production module `lib/<path>.ex` (in an umbrella,
    `apps/<app>/lib/<path>.ex`): its mirrored test
    `test/<path>_test.exs` (`apps/<app>/test/<path>_test.exs`), if it
    exists, and every test file that names the module, found with
    `git grep -lw '<Module.Name>' -- '*_test.exs'` (the name from its
    `defmodule`).
* **The tests related to a branch**: the same rule applied to every `.ex`
  and `.exs` file changed in `$(linus base)..HEAD` and in the working tree,
  plus the architecture tests when the project has them, in one invocation.
  Never a whole OTP app instead.
* In an umbrella, run the paths from the app that owns them
  (`(cd apps/<app> && mix test test/…)`), one invocation per app, unless the
  project documents a way from the root.

## Static checks

Only at a closing point (the close of a unit, the end of a correction
session, the close of an interactive session, a review): never inside a red,
green or refactor.

* **The changed files**: `git diff --name-only $(linus base)...HEAD` plus the
  working tree (`git status --porcelain`), only `.ex` and `.exs`, only files
  that still exist. The checks judge these files; findings elsewhere are left
  alone.
* In order:
  1. **Formatter**: `mix format --check-formatted <changed files>`. On a
     failure, `mix format <changed files>` and show the resulting `git diff`.
  2. **Linter**: `mix credo --strict <changed files>`, unless the project's
     own command passes other flags.
  3. **Type checker**: `mix dialyzer`, on the whole program. It can take
     minutes (more the first time, while it builds the PLT): run it in the
     background, wait for it, never interrupt it. Keep only the warnings on
     lines the branch changed (`git diff -U0 $(linus base)...HEAD -- <file>`).
* **The result**: for each check, the command, whether it passed, and each
  finding kept as `tool file:line message`. A finding fixed without changing
  behaviour (formatting, a lint rule, a spec) is a fix of the closing point:
  the agent commits it as its own instructions say (a fixup of the unit, or a
  refactor in an interactive session). A fix that would change behaviour is a
  new TDD cycle, starting with a red; run the check again after it.

## Style rules

The user's own rules: the team does not share them, so they live here and not
in the project's `.credo.exs`. Never add them to the project's configuration.

* **Scope**: only the code you write or change in the current cycle; the rest
  of the project keeps its style, even in a module you touch.
* A green stays the minimum the failing test needs, even when it breaks a
  rule: the rules are applied in the **refactor** phase, one refactor commit
  per rule applied, its body naming the rule (`elixir-style: <rule id>`). In
  review, a rule the unit's code breaks is a finding that cites the rule id.
* A rule never justifies a change of behaviour. If following it would change
  what the code does, leave the code as is and say so in the refactor
  commit's body.

### Rules

#### `with-max-three-clauses`: a `with` has at most three clauses

Every clause of the `with` head counts, `pattern <- expr` and `x = expr`
alike; the `else` block does not count.

```elixir
# Avoid: four clauses
with {:ok, user} <- authenticate(params),
     cart = Cart.for(user),
     {:ok, cart} <- Cart.validate(cart),
     {:ok, order} <- Orders.create(cart, params) do
  {:ok, order}
end
```

Extract the related steps into private functions whose names say what they
do, each with its own short `with`, and compose them in the outer one:

```elixir
with {:ok, user} <- authenticate(params),
     {:ok, order} <- place_order(user, params) do
  {:ok, order}
end

defp place_order(user, params) do
  with {:ok, cart} <- Cart.validate(Cart.for(user)),
       {:ok, order} <- Orders.create(cart, params) do
    {:ok, order}
  end
end
```

* **Why**: a long `with` mixes several steps at one level of abstraction and
  hides which ones belong together; named steps say it, and each can be read
  and tested on its own.
* **Keep the behaviour.** An extracted function returns every non-matching
  value unchanged, so the outer `with` and its `else` see exactly what they
  saw before. When the original `else` tells failures apart, keep their
  shapes; never wrap or rename an error while extracting.
* Group steps by meaning, not by count: extract the steps that together form
  one action a name can describe, never an arbitrary cut after the third
  clause.
* Extracted functions are private (`defp`): a refactor adds no public
  function.
