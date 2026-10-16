---
name: adl-reverse
description: Reverse-engineers an as-is ADL draft from an existing Elixir or Python codebase by extracting the namespace dependency graph. Use during brownfield analysis, before changing an existing architecture. Read-only on the codebase.
---

# As-is ADL from existing code

Load `adl-spec` first. This skill reads code and produces **draft text**,
handed to whoever writes `.sources/`; it never writes into the project.

## 1. Extract the dependency graph

From the project root, at depth 2, then one level deeper for the areas being
changed, with the `adl-graph` command:

* Elixir: `adl-graph --depth N <otp app>` (compiles the project without
  starting the application);
* Python: `adl-graph --depth N <source root> <root package>`.

It reads the language and the container wrapper from `toolchain.yaml` and,
in a container, copies its script into the container's `/tmp` itself (the
skill folder is not mounted there). In the Copilot workflow, which has no
`adl-graph` yet, the scripts are in `~/.local/share/minime/lib/minime/adl/`:
`python3 …/deps_graph.py <source root> <root package> --depth N` and
`mix run --no-start …/deps_graph.exs <otp app> N` (in a container, stream
the script into its `/tmp` first and run it through the wrapper, never via
`sh -c`).

The output lists namespace groups with their module counts, and the edges
between groups with the number of imports or remote calls behind each.

## 2. Read before naming

The graph shows structure, not intent: read each group's top-level module and
a few public functions before naming it. Note:

* groups that look like a domain, a subdomain or a component;
* modules directly under the root that belong to no group;
* cycles, and groups everyone depends on;
* Elixir umbrella apps or Python distributions that are really `SERVICE`s.

## 3. Draft the ADL

* One draft per file of the `adl-spec` layout, meant for `.sources/as-is/`.
* `DESCRIPTION` says it is the as-is architecture, at the commit it was
  extracted from (`git rev-parse --short HEAD`).
* **Pure ADL only**, as in `adl-spec`:
  * one `DEFINE SYSTEM` per file;
  * every artifact named in an assertion is defined in the same file, by its
    physical name (`DEFINE COMPONENT` / `DEFINE LIBRARY` for external modules
    you mention);
  * only the reference's keywords (`CONTAINED WITHIN`, `CONTAINS`,
    `has NO DEPENDENCY on`, `only`, `exclusively`, `other`, `{a, b}`); no
    invented forms such as `DEPENDS ON only` or `exclusively through`. Write
    an allow-list as `has NO DEPENDENCY on other COMPONENTS` or as explicit
    `has NO DEPENDENCY on {…}` assertions.
* Only assertions that **hold today** according to the graph.
* Notes, inferences and whatever ADL cannot say go outside the ADL block,
  together with the rules violated today (with the offending edges) and the
  cycles: they feed the target design.

## 4. Hand over

Return the drafts and the violations as text, marking anything inferred
rather than observed.
