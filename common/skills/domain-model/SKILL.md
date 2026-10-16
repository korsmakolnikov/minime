---
name: domain-model
description: The domain spec, version 2 (.sources/spec.yaml), written by hughes before any architecture, and the components map (.sources/components.yaml), written by ford, that ties every spec id to the component that realizes it - the format of both, the spec-check stages, and how the ADL, the interfaces and the spec become the map of the tests. Load it before writing, reading or testing against a spec in the Claude Code workflow (the Copilot workflow still uses domain-spec, version 1).
---

# domain-model

Two files, one system of ids:

* **`.sources/spec.yaml`** says what the domain is and must guarantee. hughes
  writes it with the user from the shopping list, in one pass, before any
  architecture: it names no component and reads no code.
* **`.sources/components.yaml`** says which component realizes each of those
  guarantees. ford writes it with the ADL and the interfaces.

The ids join them, and the tests cite them (`spec: <id>`): `spec-check`
checks that every guarantee is realized by a component and tested. Like the
rest of `.sources/`, neither file is ever committed.

## The spec (hughes)

```yaml
spec: 2
system: crash                     # the system's physical name, lowercase

entities:
  - name: Communication           # PascalCase, unique across entities and events
    kind: entity                  # entity (has an identity) | value_object (only a value)
    description: A message received from a client, to be tagged and archived.
    fields:
      - {name: id, type: integer, required: true}   # type in plain words
      - {name: status, type: one of open, archived}
    invariants:
      - id: archived-communication-has-a-tag
        rule: An archived communication carries at least one tag.
  - name: TagName
    kind: value_object
    description: The name of a tag, unique within its client.
    fields:
      - {name: value, type: string of 1 to 40 characters}

events:                           # the signals the domain exchanges
  - name: CommunicationTagged
    description: A communication received one or more tags.
    fields:
      - {name: communication_id, type: integer}

relations:
  - from: Communication
    to: Tag
    kind: many_to_many            # one_to_one | one_to_many | many_to_one | many_to_many
    description: A communication is tagged with any number of tags.
    rules:
      - id: tag-belongs-to-the-same-client
        rule: A communication is tagged only with tags of its client.

constraints:                      # rules spanning several entities or the system
  - id: tagging-is-atomic
    rule: Either every tag of a request is applied or none is.

operations:                       # what the domain does, in its own words
  - id: tag-communication
    description: A client tags one of its communications.
    pre:
      - The communication exists.
    post:
      - The communication carries exactly the requested tags.
    errors:
      - id: tag-missing-communication
        when: The communication does not exist.
        outcome: Nothing changes and the client learns the communication is missing.
    emits: [CommunicationTagged]

properties:
  - id: tagging-twice-equals-tagging-once
    operation: tag-communication  # optional: the operation it is about
    kind: idempotence             # see the kinds below
    forall:
      - {name: communication, generator: an existing communication}
      - {name: tags, generator: a non-empty list of valid tags of its client}
    holds: Tagging twice with the same tags leaves the same state as tagging once.
```

* `id`s are kebab-case and unique across the file; tests, the components map
  and reviews cite them.
* Every rule, `pre`, `post`, `when`, `outcome`, `holds` and `generator` is one
  C2-level English sentence a test can check. No "should", no "for now", no
  TODO, no code: an error's `outcome` says what the domain does, not what a
  function returns (ford decides that).
* A property's `forall` lists every input it quantifies over; the generator
  describes the domain of values, not a library call.

### Property kinds

| `kind` | It states | Typical test |
|---|---|---|
| `invariant` | Something always true of the result or the state. | Generate inputs, run, assert the invariant. |
| `roundtrip` | Doing then undoing gives the input back. | `decode(encode(x)) == x` |
| `idempotence` | Applying twice equals applying once. | `f(f(x)) == f(x)` |
| `metamorphic` | How the output changes when the input changes in a known way. | Compare `f(x)` with `f(transform(x))`. |
| `model` | The component behaves like a simpler reference model. | Run the same commands on both, compare. |
| `oracle` | The result equals that of a trusted implementation. | `f(x) == trusted(x)` |

## The components map (ford)

```yaml
version: 1
components:
  - path: crash.mcp.communication_tagger      # ADL physical path: a COMPONENT or LIBRARY
    module: CrashWeb.MCP.CommunicationTagger  # the module or class at its boundary
    boundary: interface                       # interface | concrete
    realizes:                                 # every spec id this component enforces
      - tag-communication
      - tagging-twice-equals-tagging-once
      - tag-belongs-to-the-same-client
```

* **`boundary: interface`**: callers depend on an abstraction (an Elixir
  behaviour, a Python `Protocol` or abstract class): a test of a caller may
  replace it with a double, and a contract test runs the same suite on the
  double and on the real implementation. **`concrete`**: no abstraction;
  callers are tested with the real module.
* Every id of the spec but an operation's error ids is realized by at least
  one component: an operation by the component that offers it, an invariant,
  a rule or a constraint by the one that enforces it.

## Validation

From the project root; each must print `ok`:

```sh
spec-check --stage domain        # hughes, after every write of the spec
spec-check --stage realization   # ford, after every write of the map or the ADL
spec-check --stage coverage      # at the close of a unit and in review
```

`coverage` also prints, as notes, the production files that cite an id:
allowed while the branch is open, removed before the pull request.

## From the map to the tests

The ADL and the components map give the **structure** of the tests; the spec
gives their **content**.

* **Order**: component by component, from the particular to the general.
  The unit tests of a component first; then its integration towards the
  outermost interface; last, the test of the whole flow.
* **Doubles** replace only a component whose `boundary` is `interface`. A
  `concrete` collaborator is used for real.
* **Integration tests** check what crosses an interface (inputs, outputs,
  errors, emitted events) against the contract, not again the behaviour the
  unit tests proved. A contract test is shared by the double and the real
  implementation (the language's handbook says how).
* **Each spec entry is at least one red test**, in the smallest layer of the
  onion where it can run: an operation's `post` and each of its errors as
  examples; a property as a property-based test; an invariant, a rule or a
  constraint where the component that realizes it is tested, as a property
  when it quantifies over values. A constraint that spans components lands in
  the integration or flow test only when no smaller layer can hold it.
* The test name states the behaviour in plain words; a comment cites the id
  (`spec: tagging-twice-equals-tagging-once`).
* An entry that cannot be tested as written (an unclear sentence, a generator
  that cannot be built) goes back to hughes, through kent; it is never
  skipped silently.
* The libraries (example-based, property-based, doubles, contract tests) are
  the language's: see its handbook. Adding a missing one is the user's
  decision.
