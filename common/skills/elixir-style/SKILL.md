---
name: elixir-style
description: The user's personal style rules for Elixir code, stricter than the project's Credo configuration and not shared with the team. Load it before writing, refactoring or reviewing Elixir code; unclebob applies the rules in the refactor phase, martin checks them in its idiom review.
---

# elixir-style

These rules are the user's own: the team does not share them, so they live
here and not in the project's `.credo.exs`. Never add them to the project's
configuration, and never apply them to code outside the scope below.

## Scope

* Only the code you write or change in the current cycle, as for the static
  checks: the rest of the project keeps its style, even in a module you
  touch.
* A green stays the minimum the failing test needs, even when it breaks a
  rule: the rules are applied in the **refactor** phase, one refactor commit
  per rule applied, its body naming the rule (`elixir-style: <rule id>`).
* A rule never justifies a change of behaviour. If following it would change
  what the code does, leave the code as is and say so in the refactor
  commit's body.

## Rules

### `with-max-three-clauses`: a `with` has at most three clauses

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
