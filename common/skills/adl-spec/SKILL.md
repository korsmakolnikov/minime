---
name: adl-spec
description: Reference for the Architecture Definition Language (ADL) by Mark Richards and Neal Ford as used in this workflow, including the .sources/ folder layout and how ADL physical names map to Elixir and Python namespaces. Load it before reading, writing or validating any .adl file.
---

# ADL reference and project conventions

ADL is pseudo-code that describes and governs a system's structure, meant to
be turned by an LLM into code and fitness functions
(https://www.developertoarchitect.com/downloads/adl-ref.pdf). Use **pure
ADL**, with no invented keywords. Component interfaces are not ADL: they are
written directly in code (see the `adl-scaffold` skill).

## Metadata (stripped when the ADL is used as a code-generation prompt)

| Keyword | Meaning |
|---|---|
| `DESCRIPTION text` | What this definition is about. |
| `REQUIRES text` | Tooling or code decorations the fitness functions need (e.g. `AdlFitness ExUnit helper`, `import-linter`). |
| `PROMPT text` | The prompt used to generate code from this definition. |

## Artifacts

Each is written `DEFINE <KIND> logical_name AS physical_name`. The logical name
is human-readable; the physical name is a namespace segment or directory.

| Kind | Physical name |
|---|---|
| `SYSTEM` | Root namespace or directory of the system. |
| `DOMAIN` | High-level namespace inside the system. |
| `SUBDOMAIN` | Mid-level namespace inside a domain. |
| `COMPONENT` | Leaf-level namespace. Classes/modules live here. |
| `LIBRARY` | Name of a shared or third-party library artifact. |
| `SERVICE` | Namespace delimiting a separately deployed unit. |
| `CONST` | `DEFINE CONST NAME AS value`, used inside assertions. |

Nesting is expressed by indentation under the enclosing `DEFINE`.

## Actions

* `ASSERT(condition)`: a constraint written in plain text with the keywords below.
* `FOREACH $X IN <collection> DO <actions> END`: apply assertions per artifact.

Collections: `CLASSES`, `DOMAINS`, `SUBDOMAINS`, `COMPONENTS`, `SERVICES`.
Verbs: `CONTAINED WITHIN`, `CONTAINS`, `DEPEND ON` / `DEPENDS ON` /
`DEPENDENCY ON` (usually as `has NO DEPENDENCY on`). Qualifiers seen in the
reference: `only`, `exclusively`, `other`, sets in braces `{a, b}`.

## Example

```
ADL:TICKETING DOMAIN

DESCRIPTION Define Ticketing Domain
REQUIRES AdlFitness ExUnit helper
DEFINE SYSTEM Sysops Squad AS sysops
  DEFINE DOMAIN Ticketing AS ticketing
    DEFINE COMPONENT Ticket Creation AS creation
    DEFINE COMPONENT Ticket Completion AS completion
    DEFINE SUBDOMAIN Assignment AS assignment
ASSERT(CLASSES are only CONTAINED within COMPONENTS and SUBDOMAINS)
ASSERT(creation has NO DEPENDENCY on completion)
```

## The `.sources/` folder

The input of the workflow, the ADL files written by ford, the domain spec
written by hughes and kent's shopping lists, lives in `.sources/` at the project root. simon
documents them in `.documentation/<branch>/`. Whether they are versioned
depends on the CLI (the `workflow-files` skill): never on Copilot, where
nobody stages them; on Claude Code kent commits them between units.

```
.sources/
  spec.yaml               domain spec written by hughes (see `domain-spec`)
  system.adl              SYSTEM and its DOMAINS / SERVICES
  <domain>.adl            one file per domain
  <domain>.<subdomain>.adl
  as-is/                  reverse-engineered ADL of existing code (brownfield)
  shopping_lists/<branch>.md   kent's findings for each branch
```

* Each file opens with a title line `ADL:<TITLE IN CAPITALS>`, a blank line,
  `DESCRIPTION`, optional `REQUIRES` / `PROMPT`, the `DEFINE` tree and the
  assertions, and restates the enclosing `DEFINE SYSTEM` (and `DOMAIN`, when
  relevant) so it can be read on its own.
* Files under `as-is/` describe the code as it is, with only assertions that
  hold today; target files describe what it must become.

## Physical name mapping

The path from `SYSTEM` down to an artifact gives its namespace.

| Stack | `sysops` / `ticketing` / `creation` becomes | Directory |
|---|---|---|
| Elixir | `Sysops.Ticketing.Creation` (each segment `Macro.camelize`d) | `lib/sysops/ticketing/creation/` plus facade `lib/sysops/ticketing/creation.ex` |
| Python | `sysops.ticketing.creation` | `<source root>/sysops/ticketing/creation/` (a package with `__init__.py`) |

* The Elixir `SYSTEM` physical name is the OTP application name (`:sysops`).
* The Python source root is the project's own (`src/` or the repository
  root; see `pyproject.toml`).
* `SERVICE` maps to a separately deployable unit: an umbrella app or a
  separate Mix project in Elixir, a separate distribution in Python.
