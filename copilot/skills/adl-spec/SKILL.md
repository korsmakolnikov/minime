---
name: adl-spec
description: Reference for the Architecture Definition Language (ADL) by Mark Richards and Neal Ford as used in this workflow, including the .adl/ folder layout and how ADL physical names map to Elixir and Python namespaces. Load it before reading, writing or validating any .adl file.
---

# ADL reference and project conventions

ADL is pseudo-code for describing and governing the structure of a system. It
is designed to be read by an LLM and turned into code and fitness functions.
Source: https://www.developertoarchitect.com/downloads/adl-ref.pdf

Use **pure ADL**. Do not invent keywords. Component interfaces are not part of
ADL: they are defined directly in code (see the `adl-scaffold` skill).

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

## The `.adl/` folder

ADL files live in `.adl/` at the project root. The folder is **never
committed** (the user ignores it globally). Never stage it.

```
.adl/
  shopping-list.md        preliminary findings gathered by mortimer
  system.adl              SYSTEM and its DOMAINS / SERVICES
  <domain>.adl            one file per domain
  <domain>.<subdomain>.adl
  as-is/                  reverse-engineered ADL of existing code (brownfield)
```

* Each file opens with a title line `ADL:<TITLE IN CAPITALS>`, then a blank
  line, then `DESCRIPTION`, optional `REQUIRES` / `PROMPT`, the `DEFINE` tree,
  and the assertions.
* Every file restates the enclosing `DEFINE SYSTEM` (and `DOMAIN`, when
  relevant) so it can be read on its own.
* Files under `as-is/` describe what the code is today and contain only
  assertions that hold today. Target files describe what it must become.

## Physical name mapping

The path from `SYSTEM` down to an artifact gives its namespace.

| Stack | `sysops` / `ticketing` / `creation` becomes | Directory |
|---|---|---|
| Elixir | `Sysops.Ticketing.Creation` (each segment `Macro.camelize`d) | `lib/sysops/ticketing/creation/` plus facade `lib/sysops/ticketing/creation.ex` |
| Python | `sysops.ticketing.creation` | `<source root>/sysops/ticketing/creation/` (a package with `__init__.py`) |

* The Elixir `SYSTEM` physical name is the OTP application name (`:sysops`).
* The Python source root is whatever the project uses (`src/` or the
  repository root). Read `pyproject.toml` to find it.
* `SERVICE` maps to a separately deployable unit: an umbrella app or a
  separate Mix project in Elixir, a separate distribution in Python.
