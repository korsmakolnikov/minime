---
name: adl-reverse
description: Reverse-engineers an as-is ADL draft from an existing Elixir or Python codebase by extracting the namespace dependency graph. Use during brownfield analysis, before changing an existing architecture. Read-only on the codebase.
---

# As-is ADL from existing code

Load `adl-spec` first. This skill reads code and produces **draft text**. It
never writes into the project. The draft is handed to whoever writes `.adl/`.

## 1. Extract the dependency graph

Run from the project root. Start at depth 2, then go one level deeper for the
areas being changed.

* Python: `python3 <skill dir>/deps_graph.py <source root> <root package> --depth N`
* Elixir: `mix run --no-start <skill dir>/deps_graph.exs <otp app> N`
  (compiles the project; it does not start the application).

The output lists namespace groups with their module counts and the edges
between groups with how many imports or remote calls back them.

## 2. Read before naming

The graph shows structure, not intent. For each group, read its top-level
module and a few public functions before choosing a logical name. Note:

* Groups that look like a domain, a subdomain or a component.
* Modules sitting directly under the root that belong to no group.
* Cycles, and groups that everyone depends on.
* Elixir umbrella apps or Python distributions that are really `SERVICE`s.

## 3. Draft the ADL

* One draft per file of the `adl-spec` layout, meant for `.adl/as-is/`.
* `DESCRIPTION` states that it is the as-is architecture and the commit it was
  extracted from (`git rev-parse --short HEAD`).
* **Pure ADL only**, exactly as in `adl-spec`:
  * one `DEFINE SYSTEM` per file;
  * every artifact named in an assertion is defined in the same file (use
    `DEFINE COMPONENT` / `DEFINE LIBRARY` for external modules you need to
    mention), by its physical name;
  * only the keywords of the reference (`CONTAINED WITHIN`, `CONTAINS`,
    `has NO DEPENDENCY on`, `only`, `exclusively`, `other`, `{a, b}`). No
    invented forms such as `DEPENDS ON only` or `exclusively through`. Express
    an allow-list as `has NO DEPENDENCY on other COMPONENTS` or as explicit
    `has NO DEPENDENCY on {…}` assertions.
* Include only assertions that **hold today** according to the graph.
* Notes, inferences and anything that cannot be said in ADL go outside the ADL
  block.
* List separately, outside the ADL, the rules that are violated today (with the
  offending edges) and the cycles. They feed the target design.

## 4. Hand over

Return the drafts and the violations as text. Mark anything you inferred
rather than observed.
