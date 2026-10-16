---
name: elixir-handbook
description: How to work on an Elixir project in this workflow - toolchain.yaml and the toolchain command (build, the tests to run, the static checks), the testing libraries (ExUnit, StreamData, Mox and Hammox for contract tests), the test layout, and the user's personal style rules. Load it whenever you build, test, check, write or review Elixir code in a project listed in `projects`.
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

What an agent needs to know about an Elixir codebase, in one place. The
agents say **what** to run and **when** (a cycle, a closing point, a review);
the `toolchain` command does it, and this skill says how to read the results
and write the code.

## When it applies

* **Projects**: only a project whose folder name (the basename of the
  repository root) is listed in `projects`. Anywhere else, say that no
  handbook covers the project and ask how to build and test it.
* **Tools**: only those in `tools`, and only those the project uses. A
  project built with another toolchain (rebar3, erlang.mk, Nix) is reported,
  never forced into `mix`. A check the project does not configure (no
  `credo` or `dialyxir` dependency) is skipped by `toolchain check`, never
  added: no new dependency, no new `.credo.exs`, no new alias.

## toolchain.yaml and the toolchain command

`toolchain.yaml`, at the project root and never committed, tells `toolchain`
how this project runs its commands: the container wrapper (`exec`, for
example `[edgar, exec, crash]`), extra environment, and any command the
project replaces. `toolchain show` prints what will run. When the file is
missing, `toolchain` uses plain `mix` on the host; kent writes the file from
the shopping list, never another agent.

| Need | Command |
|---|---|
| compile, warnings as errors | `toolchain build` |
| one test | `toolchain test test/foo/bar_test.exs:42` |
| a list of test files | `toolchain test <file> <file>` |
| the tests that include the files of a commit | `toolchain test --commit` (HEAD) |
| the tests that include some files | `toolchain test --related <file>…` |
| the tests related to the branch, architecture tests included | `toolchain test --branch` |
| the static checks on the branch's files | `toolchain check` (`--fix` formats first) |

Pass `--agent <your name>` so the output reaches the activity log. A test
file includes a module when it is its mirrored test (`lib/a/b.ex` →
`test/a/b_test.exs`; in an umbrella, `apps/<app>/lib/…` →
`apps/<app>/test/…`) or names the module. There is no command for the full
suite: the CI runs it.

* **Never interrupt** a run: an interrupted BEAM can hang on its BREAK menu
  inside the container and block everything. Long runs (`toolchain test
  --branch`, `toolchain check` with dialyzer) go in the background; wait for
  them.
* Never fetch dependencies or install anything (`mix deps.get`, a PLT
  download) without the user's approval.

## Reading the static checks

`toolchain check` runs, on the `.ex` and `.exs` files the branch changed:
`mix format --check-formatted`, `mix credo --strict`, then `mix dialyzer` on
the whole program (minutes the first time, while it builds the PLT). Keep
only dialyzer's warnings on lines the branch changed (`git-read diff -U0
{base}...HEAD -- <file>`); leave the others. A finding fixed without
changing behaviour (formatting, a Credo rule, a typespec) is a fix of the
closing point, committed as the agent's own instructions say; a fix that
would change behaviour is a new TDD cycle, starting with a red.

## Testing

* **ExUnit**: `async: true` unless the test touches shared state (the
  database without a sandbox, a named process, the application env).
  Helpers shared by several test modules live in `test/support/` (compiled
  in the test env through `elixirc_paths`), never in a test file.
* **Property-based tests**: StreamData, `use ExUnitProperties`, `property
  "…" do check all x <- generator do … end end`. Generators shared by several
  tests live in one generator module under `test/support/`, as the project's
  single DSL for building domain values; the scenario's parameters stay
  explicit at the call site. Adding `stream_data` to `mix.exs` is the user's
  decision.
* **Doubles**: only of a component whose boundary is an interface, which in
  Elixir is a behaviour. Prefer **Hammox** to Mox when the project has it:
  it checks every call and return value against the callback's typespecs,
  which is the contract test between the double and the real
  implementation. With plain Mox, write the contract test yourself: an
  `ExUnit.CaseTemplate` (or a shared `describe` macro) holding the
  behaviour's tests, run once against the real module and once against the
  double's expectations. Inject the implementation through the application
  env or a function argument, never by redefining modules.
* **Architecture tests** (ford's fitness functions) live in
  `test/architecture/`; `toolchain test --branch` always includes them.

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
