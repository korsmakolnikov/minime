---
name: domain-spec
description: Reference for the domain spec (.adl/spec.yaml) of this workflow, the structured input next to the ADL that lists the entities, their relations, the system constraints, the contracts of the component operations and the properties to test with property-based tests (StreamData, Hypothesis). Covers the format, the spec-check validator and how each entry becomes a test. Load it before reading, writing or testing against a spec.
---

# domain-spec

The ADL says how the code is organised; the domain spec says what the code
must guarantee. hughes writes it with the user, in two passes, and unclebob
turns every entry into a red test.

## File

One file, `.adl/spec.yaml`, next to the ADL. Like the rest of `.adl/` it is
**never committed** (the user ignores the folder globally). Never stage it.

The file grows in two passes:

1. **Domain** (before ford): `entities`, `relations`, `constraints`.
2. **Contracts** (after ford): `contracts` and `properties`, tied to the
   components of the ADL.

## Format

```yaml
spec: 1
system: crash                  # the ADL SYSTEM physical name

entities:
  - name: Communication        # PascalCase, unique
    description: A message received from a client, to be tagged and archived.
    fields:
      - name: id
        type: integer          # free text, in the target language's terms
        required: true
      - name: status
        type: one of open, archived
    invariants:
      - id: archived-communication-has-a-tag
        rule: An archived communication carries at least one tag.
  - name: Tag
    description: A label a client defines to classify its communications.
    fields:
      - name: name
        type: string
        required: true

relations:
  - from: Communication
    to: Tag
    kind: many_to_many         # one_to_one | one_to_many | many_to_one | many_to_many
    description: A communication is tagged with any number of tags.
    rules:                     # optional
      - id: tag-belongs-to-the-same-client
        rule: A communication is tagged only with tags of its client.

constraints:                   # rules spanning several entities or the system
  - id: tagging-is-atomic
    rule: Either every tag of a request is applied or none is.

contracts:
  - id: tag-communication
    component: crash.mcp.communication_tagger   # ADL physical path
    operation: tag/2                            # name/arity or function name
    pre:
      - The communication exists.
    post:
      - The communication carries exactly the requested tags.
    errors:
      - when: The communication does not exist.
        returns: "{:error, :communication_not_found}"

properties:
  - id: tagging-twice-equals-tagging-once
    component: crash.mcp.communication_tagger
    kind: idempotence          # see the kinds below
    forall:
      - name: communication
        generator: an existing communication
      - name: tags
        generator: a non-empty list of valid tags of its client
    holds: Tagging twice with the same tags leaves the same state as tagging once.
```

Rules:

* `id`s are kebab-case and unique across the whole file; tests and reviews
  cite them.
* Every rule, `pre`, `post`, `holds` and `generator` is one C2-level English
  sentence that a test can check. No "should", no "for now", no TODO.
* `relations` name existing entities; `contracts` and `properties` name a
  component defined in the ADL (`DEFINE … AS <physical>`), by its physical
  path from the system down.
* A property's `forall` lists every input it quantifies over; the generator
  describes the domain of values, not a library call.

### Property kinds

| `kind` | It states | Typical test |
|---|---|---|
| `invariant` | Something always true of the result or the state. | Generate inputs, run, assert the invariant. |
| `roundtrip` | Encoding then decoding (or doing then undoing) gives the input back. | `decode(encode(x)) == x` |
| `idempotence` | Applying twice equals applying once. | `f(f(x)) == f(x)` |
| `metamorphic` | How the output changes when the input changes in a known way. | Compare `f(x)` with `f(transform(x))`. |
| `model` | The component behaves like a simpler reference model. | Run the same commands on both, compare. |
| `oracle` | The result equals that of a trusted implementation. | `f(x) == trusted(x)` |

## Validation

Run `spec-check` from the project root after every write; it must print `ok`:

```sh
spec-check --stage domain .adl/spec.yaml      # after the first pass
spec-check --stage contracts .adl/spec.yaml   # after the second pass
```

It checks the structure, the kinds, the id format and uniqueness, the entity
names relations refer to, and, at the `contracts` stage, that every
`component` is defined in the `.adl/` files and that `contracts` and
`properties` are present. It prints one line per problem and exits non-zero
on any. It cannot judge whether a sentence is testable: that is the
interview's job.

## From the spec to the tests (unclebob)

Each entry of the component being implemented is at least one red test, one
at a time, through the normal cycle:

* A **contract** gives example-based tests: one red for the main `post`, one
  per `errors` entry, one per `pre` whose violation must be handled.
* A **property** gives one property-based red: ExUnit with StreamData
  (`use ExUnitProperties`, `property … do check all … end`) in Elixir,
  Hypothesis (`@given`) in Python. Build the generators from the `forall`
  entries in the project's shared generator module.
* Entity **invariants**, relation **rules** and **constraints** are tested
  where the component that enforces them is implemented, as a property when
  they quantify over values, as an example otherwise.
* The test name says the behaviour in plain words; a comment in the test
  cites the spec id (`# spec: tagging-twice-equals-tagging-once`) so that
  coverage can be checked with `grep`.
* An entry that cannot be tested as written (an unclear sentence, a generator
  that cannot be built) is raised with the user, not skipped silently.

If the project lacks the property-based testing library (`stream_data` in
`mix.exs`, `hypothesis` in the Python dependencies), adding it is a decision
for the user.
